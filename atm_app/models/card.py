from atm_app.utils import hash_pin
from atm_app.exceptions import CardBlockedError, InvalidPINError

class Card:
    """
    Represents an ATM debit card containing credentials and security state.
    Demonstrates Encapsulation by protecting the PIN hash and handling state changes internally.
    """
    def __init__(self, card_number: str, holder_name: str, pin: str):
        self.card_number = card_number
        self.holder_name = holder_name
        self._pin_hash = hash_pin(pin)
        self._status = "ACTIVE"  # ACTIVE, BLOCKED
        self._pin_attempts = 0

    @property
    def status(self) -> str:
        """Encapsulated getter for card status."""
        return self._status

    @status.setter
    def status(self, new_status: str):
        """Allows status updating, e.g., manual administrative blocks."""
        if new_status in ["ACTIVE", "BLOCKED"]:
            self._status = new_status

    @property
    def pin_attempts(self) -> int:
        return self._pin_attempts

    def is_blocked(self) -> bool:
        return self._status == "BLOCKED"

    def verify_pin(self, pin: str) -> bool:
        """
        Validates the PIN. Tracks incorrect attempts.
        Blocks the card if limit of 3 failed attempts is reached.
        """
        if self.is_blocked():
            raise CardBlockedError("This card is blocked due to excessive incorrect PIN attempts.")

        hashed_input = hash_pin(pin)
        if hashed_input == self._pin_hash:
            self._pin_attempts = 0  # Reset on successful validation
            return True
        else:
            self._pin_attempts += 1
            if self._pin_attempts >= 3:
                self._status = "BLOCKED"
                raise CardBlockedError("Incorrect PIN. Max attempts reached. Your card has been BLOCKED.")
            raise InvalidPINError(f"Incorrect PIN. Attempts remaining: {3 - self._pin_attempts}")

    def change_pin(self, old_pin: str, new_pin: str) -> None:
        """Updates the PIN hash after verifying the old PIN."""
        if self.is_blocked():
            raise CardBlockedError()
        
        # Verify the old PIN
        self.verify_pin(old_pin)
        
        # Update the PIN hash
        self._pin_hash = hash_pin(new_pin)
        self._pin_attempts = 0
