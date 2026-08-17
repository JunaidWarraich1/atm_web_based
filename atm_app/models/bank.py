from typing import Dict, Optional, Tuple
from atm_app.models.customer import Customer
from atm_app.models.account import Account
from atm_app.models.card import Card
from atm_app.models.transaction import TransferTransaction
from atm_app.exceptions import InvalidAccountError, CardBlockedError, AccountInactiveError, InvalidPINError

class Bank:
    """
    Acts as the central banking coordinator.
    Demonstrates encapsulation of customer, card, and account catalogs and handles inter-account transactions.
    """
    def __init__(self, name: str = "Grand OOP Bank"):
        self.name = name
        self.customers: Dict[str, Customer] = {}
        self.accounts: Dict[str, Account] = {}
        self.cards: Dict[str, Card] = {}
        
        # Link mapping card_number -> customer_id
        self._card_to_customer_map: Dict[str, str] = {}

    def register_customer(self, customer: Customer) -> None:
        """Registers a new customer in the bank catalog."""
        self.customers[customer.customer_id] = customer

    def add_account(self, customer_id: str, account: Account) -> None:
        """Registers a new account and associates it with the customer."""
        if customer_id not in self.customers:
            raise KeyError("Customer not registered.")
        self.accounts[account.account_number] = account
        self.customers[customer_id].add_account(account)

    def add_card(self, customer_id: str, card: Card) -> None:
        """Registers a new card and associates it with the customer."""
        if customer_id not in self.customers:
            raise KeyError("Customer not registered.")
        self.cards[card.card_number] = card
        self._card_to_customer_map[card.card_number] = customer_id
        self.customers[customer_id].add_card(card)

    def get_account(self, account_number: str) -> Optional[Account]:
        """Finds an account by its account number."""
        return self.accounts.get(account_number)

    def get_card(self, card_number: str) -> Optional[Card]:
        """Finds a card by card number."""
        return self.cards.get(card_number)

    def get_customer_by_card(self, card_number: str) -> Optional[Customer]:
        """Looks up the customer associated with the given card number."""
        cust_id = self._card_to_customer_map.get(card_number)
        if cust_id:
            return self.customers.get(cust_id)
        return None

    def authenticate_card(self, card_number: str, pin: str) -> Customer:
        """
        Validates card existence, status, and verifies PIN.
        Returns the associated Customer on success.
        """
        card = self.get_card(card_number)
        if not card:
            raise InvalidAccountError("Card not found in our database.")

        if card.is_blocked():
            raise CardBlockedError("Card is blocked. Please contact customer support.")

        # This will verify and raise appropriate InvalidPINError / CardBlockedError
        card.verify_pin(pin)

        customer = self.get_customer_by_card(card_number)
        if not customer:
            raise InvalidAccountError("No customer associated with this card.")

        return customer

    def transfer_funds(self, sender_acc_num: str, receiver_acc_num: str, amount: float) -> Tuple[TransferTransaction, TransferTransaction]:
        """
        Coordinates the transfer of funds between two accounts.
        Updates balances and registers credit/debit transaction logs.
        """
        sender_acc = self.get_account(sender_acc_num)
        receiver_acc = self.get_account(receiver_acc_num)

        if not sender_acc:
            raise InvalidAccountError(f"Sender account {sender_acc_num} does not exist.")
        if not receiver_acc:
            raise InvalidAccountError(f"Receiver account {receiver_acc_num} does not exist.")

        # Delegate transfer logic to the sender account, which encapsulates limits and balances
        return sender_acc.transfer(amount, receiver_acc)

    def reset_all_daily_limits(self) -> None:
        """Resets the daily limits of all accounts in the bank."""
        for account in self.accounts.values():
            account.reset_daily_limits_if_needed()
            # Explicitly force-update reset date if testing simulator rollover
            account._daily_withdrawal_total = 0.0
            account._daily_transfer_total = 0.0
