class ATMError(Exception):
    """Base class for all ATM and banking system exceptions."""
    def __init__(self, message="An ATM error occurred."):
        self.message = message
        super().__init__(self.message)


class InvalidPINError(ATMError):
    """Raised when an invalid PIN is entered."""
    def __init__(self, message="Invalid PIN entered."):
        super().__init__(message)


class CardBlockedError(ATMError):
    """Raised when a card is blocked after too many incorrect attempts or by admin action."""
    def __init__(self, message="This card is blocked and cannot be used."):
        super().__init__(message)


class InsufficientBalanceError(ATMError):
    """Raised when the account balance is insufficient for a withdrawal or transfer."""
    def __init__(self, message="Insufficient balance in account."):
        super().__init__(message)


class InsufficientATMFundsError(ATMError):
    """Raised when the physical ATM doesn't have enough cash or matching denominations."""
    def __init__(self, message="ATM has insufficient cash."):
        super().__init__(message)


class InvalidAmountError(ATMError):
    """Raised when the transaction amount is negative, zero, or not a multiple of allowed note denominations."""
    def __init__(self, message="Invalid transaction amount."):
        super().__init__(message)


class AccountInactiveError(ATMError):
    """Raised when trying to perform transactions on a blocked, closed, or inactive account."""
    def __init__(self, message="Account is currently inactive."):
        super().__init__(message)


class DailyLimitExceededError(ATMError):
    """Raised when a withdrawal or transfer exceeds the customer's daily limit."""
    def __init__(self, message="Daily transaction limit exceeded."):
        super().__init__(message)


class InvalidAccountError(ATMError):
    """Raised when the requested account does not exist in the bank registry."""
    def __init__(self, message="Target account number is invalid or does not exist."):
        super().__init__(message)
