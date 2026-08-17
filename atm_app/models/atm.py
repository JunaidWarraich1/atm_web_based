from typing import Dict
from atm_app.exceptions import InsufficientATMFundsError, InvalidAmountError
from atm_app.models.bank import Bank

class ATM:
    """
    Represents the physical ATM hardware and cash dispenser.
    Demonstrates Encapsulation by protecting cash note reserves and implementing the note dispensing algorithm.
    """
    def __init__(self, atm_id: str, bank: Bank, initial_cash: Dict[int, int] = None):
        """
        initial_cash: Dict mapping note values to their counts.
                      e.g., {5000: 10, 1000: 20, 500: 10}
        """
        self.atm_id = atm_id
        self.bank = bank
        
        # Encapsulated note denominations
        self._cash_denominations = {5000: 0, 1000: 0, 500: 0}
        if initial_cash:
            self.load_cash(initial_cash)

    @property
    def cash_denominations(self) -> Dict[int, int]:
        """Read-only copy of cash denominations to prevent direct modification."""
        return self._cash_denominations.copy()

    def get_total_cash(self) -> float:
        """Returns the total monetary value of cash currently in the ATM."""
        return sum(denom * count for denom, count in self._cash_denominations.items())

    def load_cash(self, notes_dict: Dict[int, int]) -> None:
        """Restocks note counts in the ATM."""
        for denom, count in notes_dict.items():
            if denom not in [5000, 1000, 500]:
                raise InvalidAmountError(f"Unsupported denomination: {denom}")
            if count < 0:
                raise InvalidAmountError("Note count cannot be negative.")
            self._cash_denominations[denom] += count

    def check_cash_availability(self, amount: float) -> bool:
        """Simple check if total ATM balance is sufficient."""
        return self.get_total_cash() >= amount

    def dispense_cash(self, amount: float) -> Dict[int, int]:
        """
        Note Dispensing Algorithm (Change-making backtracking implementation).
        Ensures amount is a multiple of 500, within total ATM cash, and can be composed using available notes.
        Deducts notes from inventory on success.
        """
        if amount <= 0:
            raise InvalidAmountError("Withdrawal amount must be positive.")
        if amount % 500 != 0:
            raise InvalidAmountError("ATM can only dispense amounts in multiples of Rs. 500.")

        total_cash = self.get_total_cash()
        if amount > total_cash:
            raise InsufficientATMFundsError("ATM does not have enough cash to fulfill this transaction.")

        target = int(amount)
        denoms = [5000, 1000, 500]
        
        # Backtracking lookup to find valid note combination (preferring larger notes)
        def find_combination(idx: int, remaining: int, current_sol: Dict[int, int]) -> Optional[Dict[int, int]]:
            if remaining == 0:
                return current_sol
            if idx >= len(denoms):
                return None
                
            denom = denoms[idx]
            max_notes = min(remaining // denom, self._cash_denominations[denom])
            
            for count in range(max_notes, -1, -1):
                new_sol = current_sol.copy()
                new_sol[denom] = count
                res = find_combination(idx + 1, remaining - (count * denom), new_sol)
                if res is not None:
                    return res
            return None

        # Helper import to satisfy typing
        from typing import Optional

        solution = find_combination(0, target, {})
        if solution is None:
            raise InsufficientATMFundsError("ATM cannot dispense the exact amount using available note denominations (500, 1000, 5000).")

        # Strip out 0 counts
        dispensed = {denom: count for denom, count in solution.items() if count > 0}

        # Deduct notes from ATM reserves
        for denom, count in dispensed.items():
            self._cash_denominations[denom] -= count

        return dispensed
