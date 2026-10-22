import json
import os
from datetime import datetime, date
from typing import Tuple, Optional
from atm_app.models import Bank, ATM, Customer, Card, SavingsAccount, CurrentAccount
from atm_app.models.transaction import DepositTransaction, WithdrawalTransaction, TransferTransaction

class StateStorage:
    """
    Manages JSON-based persistence for the Bank and ATM state.
    Serializes and deserializes the entire object graph, preserving class types and encapsulation.
    """
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.filepath = os.path.join(data_dir, "bank_state.json")

    def _ensure_dir(self):
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def save_state(self, bank: Bank, atm: ATM) -> None:
        """Serializes and saves Bank and ATM state to JSON."""
        try:
            self._ensure_dir()
            
            # Serialize customers
            customers_data = []
            for cust in bank.customers.values():
                customers_data.append({
                    "customer_id": cust.customer_id,
                    "name": cust.name,
                    "phone_email": cust.phone_email,
                    "card_numbers": [card.card_number for card in cust.cards],
                    "account_numbers": [acc.account_number for acc in cust.accounts]
                })

            # Serialize cards
            cards_data = []
            for card in bank.cards.values():
                cards_data.append({
                    "card_number": card.card_number,
                    "holder_name": card.holder_name,
                    "pin_hash": card._pin_hash,
                    "status": card.status,
                    "pin_attempts": card.pin_attempts
                })

            # Serialize accounts and their transactions
            accounts_data = []
            for acc in bank.accounts.values():
                txns_data = []
                for txn in acc.transactions:
                    txn_dict = {
                        "type": txn.get_type_name(),
                        "txn_id": txn.transaction_id,
                        "amount": txn.amount,
                        "timestamp": txn.timestamp.isoformat(),
                        "account_number": txn.account_number,
                        "status": txn.status
                    }
                    if isinstance(txn, TransferTransaction):
                        txn_dict["other_account_number"] = txn.other_account_number
                        txn_dict["role"] = txn.role
                    txns_data.append(txn_dict)

                acc_type = "SavingsAccount" if isinstance(acc, SavingsAccount) else "CurrentAccount"
                accounts_data.append({
                    "type": acc_type,
                    "account_number": acc.account_number,
                    "holder_name": acc.holder_name,
                    "balance": acc._balance,
                    "status": acc.status,
                    "daily_withdrawal_total": acc._daily_withdrawal_total,
                    "daily_transfer_total": acc._daily_transfer_total,
                    "last_limit_reset": acc._last_limit_reset.isoformat(),
                    "transactions": txns_data
                })

            # Serialize ATM
            atm_data = {
                "atm_id": atm.atm_id,
                "cash_denominations": {str(k): v for k, v in atm.cash_denominations.items()}
            }

            state = {
                "bank_name": bank.name,
                "customers": customers_data,
                "cards": cards_data,
                "accounts": accounts_data,
                "card_to_customer_map": bank._card_to_customer_map,
                "atm": atm_data
            }

            with open(self.filepath, "w") as f:
                json.dump(state, f, indent=4)
        except Exception as e:
            print(f"[STORAGE ERROR] Could not save state to {self.filepath}: {e}")

    def load_state(self) -> Tuple[Optional[Bank], Optional[ATM]]:
        """Loads and reconstructs the Bank and ATM object graphs from JSON."""
        if not os.path.exists(self.filepath):
            return None, None

        try:
            with open(self.filepath, "r") as f:
                state = json.load(f)

            bank = Bank(state.get("bank_name", "Grand OOP Bank"))
            
            # Reconstruct Cards
            for c_data in state["cards"]:
                card = Card(c_data["card_number"], c_data["holder_name"], "0000")  # Dummy PIN, we overwrite hash below
                card._pin_hash = c_data["pin_hash"]
                card.status = c_data["status"]
                card._pin_attempts = c_data["pin_attempts"]
                bank.cards[card.card_number] = card

            # Reconstruct Accounts & transactions
            for a_data in state["accounts"]:
                acc_num = a_data["account_number"]
                holder = a_data["holder_name"]
                bal = a_data["balance"]
                
                if a_data["type"] == "SavingsAccount":
                    acc = SavingsAccount(acc_num, holder, bal)
                else:
                    acc = CurrentAccount(acc_num, holder, bal)
                
                acc.status = a_data["status"]
                acc._daily_withdrawal_total = a_data["daily_withdrawal_total"]
                acc._daily_transfer_total = a_data["daily_transfer_total"]
                acc._last_limit_reset = date.fromisoformat(a_data["last_limit_reset"])

                # Reconstruct transactions
                for t_data in a_data["transactions"]:
                    t_type = t_data["type"]
                    t_id = t_data["txn_id"]
                    t_amt = t_data["amount"]
                    t_time = datetime.fromisoformat(t_data["timestamp"])
                    t_status = t_data["status"]

                    if t_type == "Deposit":
                        txn = DepositTransaction(t_amt, acc_num, t_status, t_id)
                    elif t_type == "Withdrawal":
                        txn = WithdrawalTransaction(t_amt, acc_num, t_status, t_id)
                    else:  # Transfer
                        txn = TransferTransaction(
                            t_amt, acc_num, t_data["other_account_number"], 
                            t_data["role"], t_status, t_id
                        )
                    txn.timestamp = t_time
                    acc.transactions.append(txn)
                
                bank.accounts[acc_num] = acc

            # Reconstruct Customers
            for cust_data in state["customers"]:
                cust = Customer(cust_data["customer_id"], cust_data["name"], cust_data["phone_email"])
                
                # Link cards
                for c_num in cust_data["card_numbers"]:
                    card = bank.cards.get(c_num)
                    if card:
                        cust.add_card(card)
                        
                # Link accounts
                for a_num in cust_data["account_numbers"]:
                    acc = bank.accounts.get(a_num)
                    if acc:
                        cust.add_account(acc)
                        
                bank.customers[cust.customer_id] = cust

            # Re-map card_to_customer
            bank._card_to_customer_map = state["card_to_customer_map"]

            # Reconstruct ATM
            atm_data = state["atm"]
            cash = {int(k): v for k, v in atm_data["cash_denominations"].items()}
            atm = ATM(atm_data["atm_id"], bank, cash)

            return bank, atm

        except Exception as e:
            # If load fails (e.g. invalid format or modification), start fresh
            print(f"Error loading saved state: {e}. Starting with a fresh database.")
            return None, None

    def clear_state(self) -> None:
        """Deletes the persistence file."""
        if os.path.exists(self.filepath):
            os.remove(self.filepath)
