from abc import ABC, abstractmethod
from datetime import datetime
import uuid

class Transaction(ABC):
    """
    Abstract Base Class for transactions.
    Demonstrates Abstraction and Inheritance.
    """
    def __init__(self, amount: float, account_number: str, status: str = "SUCCESS", txn_id: str = None):
        self.transaction_id = txn_id or f"TXN-{uuid.uuid4().hex[:8].upper()}"
        self.amount = amount
        self.timestamp = datetime.now()
        self.account_number = account_number
        self.status = status

    @abstractmethod
    def get_type_name(self) -> str:
        """Returns the transaction type as a string."""
        pass

    @abstractmethod
    def get_statement_line(self) -> str:
        """Returns a formatted statement line showing the date, type, and signed amount."""
        pass


class DepositTransaction(Transaction):
    """Concrete transaction for cash deposits."""
    def get_type_name(self) -> str:
        return "Deposit"

    def get_statement_line(self) -> str:
        date_str = self.timestamp.strftime("%d-%b")
        return f"{date_str:<10} Deposit    +{self.amount:,.2f}"


class WithdrawalTransaction(Transaction):
    """Concrete transaction for cash withdrawals."""
    def get_type_name(self) -> str:
        return "Withdrawal"

    def get_statement_line(self) -> str:
        date_str = self.timestamp.strftime("%d-%b")
        return f"{date_str:<10} Withdrawal -{self.amount:,.2f}"


class TransferTransaction(Transaction):
    """
    Concrete transaction for peer-to-peer transfers.
    Handles credit and debit labels dynamically depending on the role.
    """
    def __init__(self, amount: float, account_number: str, other_account_number: str, role: str, status: str = "SUCCESS", txn_id: str = None):
        """
        role: 'DEBIT' (sender) or 'CREDIT' (receiver)
        """
        super().__init__(amount, account_number, status, txn_id)
        self.other_account_number = other_account_number
        self.role = role  # DEBIT or CREDIT

    def get_type_name(self) -> str:
        return f"Transfer ({'To' if self.role == 'DEBIT' else 'From'} {self.other_account_number})"

    def get_statement_line(self) -> str:
        date_str = self.timestamp.strftime("%d-%b")
        sign = "-" if self.role == "DEBIT" else "+"
        label = f"Trsf to {self.other_account_number}" if self.role == "DEBIT" else f"Trsf fr {self.other_account_number}"
        # Truncate label to keep it neat
        return f"{date_str:<10} {label:<14} {sign}{self.amount:,.2f}"
