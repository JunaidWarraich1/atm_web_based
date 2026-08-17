from abc import ABC, abstractmethod
from datetime import datetime, date
from atm_app.exceptions import (
    InsufficientBalanceError, InvalidAmountError,
    AccountInactiveError, DailyLimitExceededError,
    InvalidAccountError
)
from atm_app.models.transaction import DepositTransaction, WithdrawalTransaction, TransferTransaction

class Account(ABC):
    """
    Abstract Base Class for bank accounts.
    Demonstrates Abstraction, Inheritance, and Encapsulation.
    """
    DAILY_WITHDRAWAL_LIMIT = 100000.0  # Rs. 100,000 daily withdrawal limit
    DAILY_TRANSFER_LIMIT = 150000.0    # Rs. 150,000 daily transfer limit

    def __init__(self, account_number: str, holder_name: str, initial_balance: float = 0.0):
        self.account_number = account_number
        self.holder_name = holder_name
        self._balance = initial_balance
        self._status = "ACTIVE"  # ACTIVE, INACTIVE
        self.transactions = []
        
        # Limit tracking
        self._daily_withdrawal_total = 0.0
        self._daily_transfer_total = 0.0
        self._last_limit_reset = date.today()

    @property
    def balance(self) -> float:
        """Encapsulated balance property getter. Avoids direct modification."""
        return self._balance

    @property
    def status(self) -> str:
        return self._status

    @status.setter
    def status(self, new_status: str):
        if new_status in ["ACTIVE", "INACTIVE"]:
            self._status = new_status

    def is_active(self) -> bool:
        return self._status == "ACTIVE"

    def check_balance(self) -> float:
        """Returns the current balance securely."""
        self.reset_daily_limits_if_needed()
        return self._balance

    def reset_daily_limits_if_needed(self) -> None:
        """Resets the daily transaction limits if a new day has started."""
        current_date = date.today()
        if current_date > self._last_limit_reset:
            self._daily_withdrawal_total = 0.0
            self._daily_transfer_total = 0.0
            self._last_limit_reset = current_date

    @property
    def daily_withdrawal_total(self) -> float:
        self.reset_daily_limits_if_needed()
        return self._daily_withdrawal_total

    @property
    def daily_transfer_total(self) -> float:
        self.reset_daily_limits_if_needed()
        return self._daily_transfer_total

    @abstractmethod
    def calculate_withdrawal_limit(self) -> float:
        """
        Polymorphic calculation of maximum withdrawable amount at this instant.
        Considers balance, min balance/overdraft, and daily limits.
        """
        pass

    @abstractmethod
    def get_withdrawal_fee(self) -> float:
        """Polymorphic fee for cash withdrawals."""
        pass

    @abstractmethod
    def get_transfer_fee(self) -> float:
        """Polymorphic fee for account transfers."""
        pass

    @abstractmethod
    def validate_withdrawal_rules(self, amount: float) -> None:
        """Validates specific rules for this account type (e.g. minimum balance, max txn limit)."""
        pass

    def deposit(self, amount: float) -> DepositTransaction:
        """
        Deposits positive amount into account.
        Creates and stores transaction record.
        """
        if not self.is_active():
            raise AccountInactiveError("Cannot deposit: Account is inactive.")
        
        if amount <= 0:
            raise InvalidAmountError("Deposit amount must be positive.")

        self._balance += amount
        txn = DepositTransaction(amount, self.account_number)
        self.transactions.append(txn)
        return txn

    def withdraw(self, amount: float) -> WithdrawalTransaction:
        """
        Withdraws amount from account (excluding ATM-specific cash/denomination validations).
        Applies fees and tracks daily limits.
        """
        self.reset_daily_limits_if_needed()

        if not self.is_active():
            raise AccountInactiveError("Cannot withdraw: Account is inactive.")

        if amount <= 0:
            raise InvalidAmountError("Withdrawal amount must be positive.")

        fee = self.get_withdrawal_fee()
        total_deduction = amount + fee

        # Check account type limits
        self.validate_withdrawal_rules(amount)

        # Check daily limit
        if self._daily_withdrawal_total + amount > self.DAILY_WITHDRAWAL_LIMIT:
            raise DailyLimitExceededError(
                f"Withdrawal exceeds daily limit of Rs. {self.DAILY_WITHDRAWAL_LIMIT:,.2f}. "
                f"Withdrawn today: Rs. {self._daily_withdrawal_total:,.2f}."
            )

        # Perform the balance check
        # This will be verified differently for Savings (min balance 5000) and Current (overdraft 50000)
        # We delegate this verification to check if the total_deduction would violate core balances.
        self._verify_funds(total_deduction)

        # Update balance and limits
        self._balance -= total_deduction
        self._daily_withdrawal_total += amount

        txn = WithdrawalTransaction(amount, self.account_number)
        self.transactions.append(txn)
        return txn

    def transfer(self, amount: float, target_account: 'Account') -> tuple[TransferTransaction, TransferTransaction]:
        """
        Transfers money to another account.
        Creates debit record for sender and credit record for receiver.
        """
        self.reset_daily_limits_if_needed()

        if not self.is_active():
            raise AccountInactiveError("Sender account is inactive.")
        if target_account is None:
            raise InvalidAccountError("Target account does not exist.")
        if not target_account.is_active():
            raise AccountInactiveError("Target account is inactive.")
        if self.account_number == target_account.account_number:
            raise InvalidAmountError("Sender and receiver accounts cannot be the same.")
        if amount <= 0:
            raise InvalidAmountError("Transfer amount must be positive.")

        fee = self.get_transfer_fee()
        total_deduction = amount + fee

        # Check daily limits
        if self._daily_transfer_total + amount > self.DAILY_TRANSFER_LIMIT:
            raise DailyLimitExceededError(
                f"Transfer exceeds daily limit of Rs. {self.DAILY_TRANSFER_LIMIT:,.2f}. "
                f"Transferred today: Rs. {self._daily_transfer_total:,.2f}."
            )

        # Verify sender has sufficient funds
        self._verify_funds(total_deduction)

        # Perform transfer
        self._balance -= total_deduction
        target_account._balance += amount
        self._daily_transfer_total += amount

        # Create transactions
        debit_txn = TransferTransaction(amount, self.account_number, target_account.account_number, "DEBIT")
        credit_txn = TransferTransaction(amount, target_account.account_number, self.account_number, "CREDIT")

        self.transactions.append(debit_txn)
        target_account.transactions.append(credit_txn)

        return debit_txn, credit_txn

    @abstractmethod
    def _verify_funds(self, total_deduction: float) -> None:
        """Internal helper to verify if the account can support a deduction of total_deduction."""
        pass


class SavingsAccount(Account):
    """
    Savings Account.
    Rules: Minimum balance of Rs. 5,000, Max Rs. 50,000 per withdrawal txn.
    """
    MIN_BALANCE = 5000.0
    MAX_WITHDRAWAL_PER_TXN = 50000.0

    def calculate_withdrawal_limit(self) -> float:
        self.reset_daily_limits_if_needed()
        
        # Max withdrawable based on balance and min balance requirement
        withdrawable_balance = max(0.0, self._balance - self.MIN_BALANCE)
        
        # Remaining daily limit
        remaining_daily = max(0.0, self.DAILY_WITHDRAWAL_LIMIT - self._daily_withdrawal_total)
        
        # Limit per transaction
        limit = min(withdrawable_balance, remaining_daily, self.MAX_WITHDRAWAL_PER_TXN)
        return limit

    def get_withdrawal_fee(self) -> float:
        return 50.0

    def get_transfer_fee(self) -> float:
        return 100.0

    def validate_withdrawal_rules(self, amount: float) -> None:
        if amount > self.MAX_WITHDRAWAL_PER_TXN:
            raise InvalidAmountError(f"Savings Account maximum withdrawal per transaction is Rs. {self.MAX_WITHDRAWAL_PER_TXN:,.2f}.")

    def _verify_funds(self, total_deduction: float) -> None:
        if self._balance - total_deduction < self.MIN_BALANCE:
            raise InsufficientBalanceError(
                f"Savings account must maintain a minimum balance of Rs. {self.MIN_BALANCE:,.2f}. "
                f"Current: Rs. {self._balance:,.2f}, required deduction: Rs. {total_deduction:,.2f}."
            )


class CurrentAccount(Account):
    """
    Current Account.
    Rules: Overdraft limit of Rs. 50,000. No transaction limit other than daily/overdraft.
    """
    OVERDRAFT_LIMIT = 50000.0

    def calculate_withdrawal_limit(self) -> float:
        self.reset_daily_limits_if_needed()
        
        # Max withdrawable based on balance and overdraft
        withdrawable_balance = max(0.0, self._balance + self.OVERDRAFT_LIMIT)
        
        # Remaining daily limit
        remaining_daily = max(0.0, self.DAILY_WITHDRAWAL_LIMIT - self._daily_withdrawal_total)
        
        return min(withdrawable_balance, remaining_daily)

    def get_withdrawal_fee(self) -> float:
        return 0.0  # Current accounts do not charge withdrawal fees in our system

    def get_transfer_fee(self) -> float:
        return 50.0  # Current accounts have a lower transfer fee

    def validate_withdrawal_rules(self, amount: float) -> None:
        pass  # Current account has no single transaction limit other than overdraft and daily

    def _verify_funds(self, total_deduction: float) -> None:
        if self._balance - total_deduction < -self.OVERDRAFT_LIMIT:
            raise InsufficientBalanceError(
                f"Transaction exceeds overdraft limit of Rs. {self.OVERDRAFT_LIMIT:,.2f}. "
                f"Current: Rs. {self._balance:,.2f}, required deduction: Rs. {total_deduction:,.2f}."
            )
        
        # Make sure balance doesn't go below overdraft limit
        if self._balance - total_deduction < -self.OVERDRAFT_LIMIT:
            raise InsufficientBalanceError("Insufficient balance: Exceeds overdraft limit.")
