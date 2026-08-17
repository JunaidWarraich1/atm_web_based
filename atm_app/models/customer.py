from typing import List, Optional
from atm_app.models.card import Card
from atm_app.models.account import Account

class Customer:
    """
    Represents a bank customer.
    Demonstrates Association and Composition (Customer has multiple Cards and Accounts).
    """
    def __init__(self, customer_id: str, name: str, phone_email: str):
        self.customer_id = customer_id
        self.name = name
        self.phone_email = phone_email
        self.cards: List[Card] = []
        self.accounts: List[Account] = []

    def add_card(self, card: Card) -> None:
        """Adds a debit card associated with this customer."""
        self.cards.append(card)

    def add_account(self, account: Account) -> None:
        """Adds a bank account associated with this customer."""
        self.accounts.append(account)

    def get_account(self, account_number: str) -> Optional[Account]:
        """Finds an account by its account number."""
        for account in self.accounts:
            if account.account_number == account_number:
                return account
        return None

    def get_card(self, card_number: str) -> Optional[Card]:
        """Finds a card by its card number."""
        for card in self.cards:
            if card.card_number == card_number:
                return card
        return None
