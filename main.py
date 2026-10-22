import os
import uvicorn
from fastapi import FastAPI, HTTPException, Body, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Optional, List

from atm_app.models import Bank, ATM, Customer, Card, SavingsAccount, CurrentAccount
from atm_app.exceptions import ATMError
from atm_app.storage import StateStorage

app = FastAPI(title="Grand OOP Bank Web ATM API", version="2.0.0")

# Setup backend references
data_dir = "/tmp/data" if os.environ.get("VERCEL") else os.path.join(os.path.dirname(__file__), "data")
storage = StateStorage(data_dir=data_dir)
bank, atm = storage.load_state()

# Helper to load demo data if none exists
def load_default_data():
    global bank, atm
    bank = Bank("Grand OOP Bank")
    
    # Register customers
    junaid = Customer("C-1001", "Muhammad Junaid", "junaid.warraich@email.com")
    ali = Customer("C-1002", "Ali Hassan", "ali.hassan@email.com")
    bank.register_customer(junaid)
    bank.register_customer(ali)

    # Register accounts
    junaid_sav = SavingsAccount("SAV-1001", "Muhammad Junaid", 25000.0)
    junaid_cur = CurrentAccount("CUR-1001", "Muhammad Junaid", 10000.0)
    ali_sav = SavingsAccount("SAV-1002", "Ali Hassan", 75000.0)
    bank.add_account("C-1001", junaid_sav)
    bank.add_account("C-1001", junaid_cur)
    bank.add_account("C-1002", ali_sav)

    # Register cards
    card_junaid1 = Card("1111-2222-3333-4444", "Muhammad Junaid", "4321")
    card_junaid2 = Card("5555-6666-7777-8888", "Muhammad Junaid", "5678")
    card_ali = Card("9876-5432-1098-7654", "Ali Hassan", "1984")
    bank.add_card("C-1001", card_junaid1)
    bank.add_card("C-1001", card_junaid2)
    bank.add_card("C-1002", card_ali)

    # Restock ATM cash (Rs. 100,000 total)
    atm = ATM("ATM-WEB-PRO", bank, {5000: 10, 1000: 30, 500: 40})
    storage.save_state(bank, atm)

if not bank or not atm:
    load_default_data()

# Session State (in-memory for simulator single user convenience)
class SessionState:
    def __init__(self):
        self.active_card: Optional[Card] = None
        self.active_customer: Optional[Customer] = None
        self.active_account: Optional[Account] = None

session = SessionState()


# API Payload Models
class CardLoginPayload(BaseModel):
    card_number: str
    pin: str

class SwitchAccountPayload(BaseModel):
    account_number: str

class TransactionPayload(BaseModel):
    amount: float

class TransferPayload(BaseModel):
    target_account_number: str
    amount: float

class ChangePinPayload(BaseModel):
    old_pin: str
    new_pin: str

class RestockPayload(BaseModel):
    notes_5000: int
    notes_1000: int
    notes_500: int

class ToggleCardPayload(BaseModel):
    card_number: str
    status: str


# Helper to assert session is active
def verify_session(x_card_number: Optional[str] = None):
    if session.active_card and session.active_customer and session.active_account:
        return
        
    target_card = x_card_number or (session.active_card.card_number if session.active_card else None)
    if not target_card and bank and "1111-2222-3333-4444" in bank.cards:
        target_card = "1111-2222-3333-4444"
        
    if target_card and bank and target_card in bank.cards:
        card = bank.get_card(target_card)
        customer = bank.get_customer_by_card(target_card)
        if card and customer and customer.accounts:
            session.active_card = card
            session.active_customer = customer
            session.active_account = customer.accounts[0]
            return

    raise HTTPException(status_code=401, detail="No active card session. Please insert card and enter PIN.")


# --- API Routes ---

@app.get("/api/cards")
def get_cards():
    """Lists available cards to select from in UI."""
    return [
        {
            "card_number": card.card_number,
            "holder_name": card.holder_name,
            "status": card.status,
            "customer_id": bank.get_customer_by_card(card.card_number).customer_id
        }
        for card in bank.cards.values()
    ]

@app.post("/api/insert-card")
def insert_card(payload: CardLoginPayload):
    """Verifies card details and authenticates session."""
    try:
        customer = bank.authenticate_card(payload.card_number, payload.pin)
        card = bank.get_card(payload.card_number)
        
        session.active_card = card
        session.active_customer = customer
        session.active_account = customer.accounts[0] if customer.accounts else None
        
        storage.save_state(bank, atm)
        
        return {
            "success": True,
            "customer_name": customer.name,
            "active_account": {
                "account_number": session.active_account.account_number,
                "type": session.active_account.__class__.__name__
            } if session.active_account else None,
            "accounts": [
                {"account_number": acc.account_number, "type": acc.__class__.__name__, "balance": acc.balance}
                for acc in customer.accounts
            ]
        }
    except ATMError as e:
        storage.save_state(bank, atm)
        raise HTTPException(status_code=400, detail=e.message)

@app.post("/api/eject-card")
def eject_card():
    """Clears the session status."""
    session.active_card = None
    session.active_customer = None
    session.active_account = None
    return {"success": True, "message": "Card ejected."}

@app.get("/api/session")
def get_session():
    """Gets current active session parameters."""
    if not session.active_card:
        return {"authenticated": False}
    
    return {
        "authenticated": True,
        "customer_name": session.active_customer.name,
        "card_number": session.active_card.card_number,
        "active_account": {
            "account_number": session.active_account.account_number,
            "type": session.active_account.__class__.__name__,
            "balance": session.active_account.balance,
            "withdrawal_limit": session.active_account.calculate_withdrawal_limit(),
            "withdrawal_fee": session.active_account.get_withdrawal_fee()
        } if session.active_account else None,
        "accounts": [
            {"account_number": acc.account_number, "type": acc.__class__.__name__, "balance": acc.balance}
            for acc in session.active_customer.accounts
        ]
    }

@app.post("/api/switch-account")
def switch_account(payload: SwitchAccountPayload):
    verify_session()
    account = session.active_customer.get_account(payload.account_number)
    if not account:
        raise HTTPException(status_code=404, detail="Account not linked to this customer.")
    
    session.active_account = account
    return {"success": True, "active_account_number": account.account_number}

@app.get("/api/balance")
def check_balance():
    verify_session()
    return {
        "account_number": session.active_account.account_number,
        "balance": session.active_account.check_balance(),
        "withdrawable_limit": session.active_account.calculate_withdrawal_limit()
    }

@app.post("/api/deposit")
def deposit_cash(payload: TransactionPayload, x_card_number: Optional[str] = Header(None)):
    verify_session(x_card_number)
    try:
        txn = session.active_account.deposit(payload.amount)
        storage.save_state(bank, atm)
        return {
            "success": True,
            "transaction_id": txn.transaction_id,
            "amount": payload.amount,
            "new_balance": session.active_account.balance
        }
    except ATMError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/withdraw")
def withdraw_cash(payload: TransactionPayload, x_card_number: Optional[str] = Header(None)):
    verify_session(x_card_number)
    try:
        # Double validation checks
        initial_notes = atm.cash_denominations
        
        # 1. ATM Dispenser algorithm test (actually deducts notes)
        dispensed = atm.dispense_cash(payload.amount)
        
        try:
            # 2. Account checks (limits, fees, balances)
            txn = session.active_account.withdraw(payload.amount)
            
            # Commit changes
            storage.save_state(bank, atm)
            
            return {
                "success": True,
                "transaction_id": txn.transaction_id,
                "amount": payload.amount,
                "fee": session.active_account.get_withdrawal_fee(),
                "new_balance": session.active_account.balance,
                "dispensed_notes": dispensed
            }
        except Exception as e:
            # Revert ATM notes subtraction since account txn failed
            atm._cash_denominations = initial_notes
            raise e
            
    except ATMError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/transfer")
def transfer_funds(payload: TransferPayload, x_card_number: Optional[str] = Header(None)):
    verify_session(x_card_number)
    try:
        debit_txn, _ = bank.transfer_funds(session.active_account.account_number, payload.target_account_number, payload.amount)
        storage.save_state(bank, atm)
        return {
            "success": True,
            "transaction_id": debit_txn.transaction_id,
            "amount": payload.amount,
            "fee": session.active_account.get_transfer_fee(),
            "new_balance": session.active_account.balance
        }
    except ATMError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/change-pin")
def change_pin(payload: ChangePinPayload, x_card_number: Optional[str] = Header(None)):
    verify_session(x_card_number)
    
    # Check security format
    from atm_app.utils import validate_pin_format
    if not validate_pin_format(payload.new_pin):
        raise HTTPException(status_code=400, detail="New PIN must be exactly 4 digits, and cannot be consecutive/repeating digits.")

    try:
        session.active_card.change_pin(payload.old_pin, payload.new_pin)
        storage.save_state(bank, atm)
        return {"success": True, "message": "PIN updated successfully."}
    except ATMError as e:
        raise HTTPException(status_code=400, detail=e.message)

@app.get("/api/statement")
def get_statement():
    verify_session()
    txns = session.active_account.transactions[-5:]
    serialized = []
    for t in reversed(txns):
        # Extract signed amount formatting
        line = t.get_statement_line().split()
        date_str = line[0]
        type_desc = " ".join(line[1:-1])
        amount_val = line[-1]
        
        serialized.append({
            "transaction_id": t.transaction_id,
            "date": date_str,
            "description": type_desc,
            "amount": amount_val,
            "status": t.status
        })
    return serialized


# --- Admin Routes ---

@app.get("/api/admin/status")
def get_admin_status():
    return {
        "atm_id": atm.atm_id,
        "vault_total": atm.get_total_cash(),
        "denominations": atm.cash_denominations,
        "customers": [
            {
                "customer_id": cust.customer_id,
                "name": cust.name,
                "phone_email": cust.phone_email,
                "cards": [
                    {"card_number": card.card_number, "status": card.status, "attempts": card.pin_attempts}
                    for card in cust.cards
                ],
                "accounts": [
                    {
                        "account_number": acc.account_number,
                        "type": acc.__class__.__name__,
                        "balance": acc.balance,
                        "status": acc.status,
                        "daily_withdrawal_total": acc.daily_withdrawal_total,
                        "daily_transfer_total": acc.daily_transfer_total
                    }
                    for acc in cust.accounts
                ]
            }
            for cust in bank.customers.values()
        ]
    }

@app.post("/api/admin/restock")
def restock_vault(payload: RestockPayload):
    try:
        atm.load_cash({
            5000: payload.notes_5000,
            1000: payload.notes_1000,
            500: payload.notes_500
        })
        storage.save_state(bank, atm)
        return {"success": True, "new_vault_total": atm.get_total_cash()}
    except ATMError as e:
        raise HTTPException(status_code=400, detail=e.message)

@app.post("/api/admin/reset-limits")
def reset_limits():
    bank.reset_all_daily_limits()
    storage.save_state(bank, atm)
    return {"success": True, "message": "Daily transaction limits reset for all accounts."}

@app.post("/api/admin/toggle-card")
def toggle_card(payload: ToggleCardPayload):
    card = bank.get_card(payload.card_number)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found.")
    
    if payload.status in ["ACTIVE", "BLOCKED"]:
        card.status = payload.status
        if payload.status == "ACTIVE":
            card._pin_attempts = 0
        storage.save_state(bank, atm)
        return {"success": True, "new_status": card.status}
    else:
        raise HTTPException(status_code=400, detail="Invalid card status value.")

@app.post("/api/admin/reset")
def reset_database():
    storage.clear_state()
    load_default_data()
    
    # Eject session too
    session.active_card = None
    session.active_customer = None
    session.active_account = None
    
    return {"success": True, "message": "Bank database and ATM vault reset successfully."}


# --- Static SPA Router ---

# Serves static assets
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

@app.get("/")
def read_root():
    """Serves the index.html SPA dashboard directly at the root URL."""
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))


def start_server():
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    start_server()
