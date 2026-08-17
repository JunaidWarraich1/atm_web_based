import unittest
from datetime import date, timedelta
from atm_app.models import Bank, ATM, Customer, Card, SavingsAccount, CurrentAccount
from atm_app.exceptions import (
    InvalidPINError, CardBlockedError, InsufficientBalanceError,
    InsufficientATMFundsError, InvalidAmountError,
    AccountInactiveError, DailyLimitExceededError, InvalidAccountError
)

class TestATMSystem(unittest.TestCase):
    """
    Unit tests for the OOP ATM System.
    Validates rules, calculations, encapsulation, and error states.
    """
    def setUp(self):
        # Create bank
        self.bank = Bank("Test Bank")
        
        # Create a Customer
        self.customer = Customer("C-101", "Alice", "alice@example.com")
        self.bank.register_customer(self.customer)

        # Create Cards
        self.card1 = Card("1111-2222-3333-4444", "Alice", "1234")
        self.bank.add_card("C-101", self.card1)
        
        # Create Accounts
        self.savings = SavingsAccount("SAV-101", "Alice", 10000.0)  # Rs. 10,000 initial balance
        self.current = CurrentAccount("CUR-101", "Alice", 20000.0)  # Rs. 20,000 initial balance
        
        self.bank.add_account("C-101", self.savings)
        self.bank.add_account("C-101", self.current)

        # Create ATM loaded with cash
        # Total Cash: 5000*2 + 1000*10 + 500*20 = 10,000 + 10,000 + 10,000 = 30,000
        self.atm = ATM("ATM-777", self.bank, {5000: 2, 1000: 10, 500: 20})

    def test_authentication_success(self):
        """Test card authentication with correct PIN."""
        cust = self.bank.authenticate_card("1111-2222-3333-4444", "1234")
        self.assertEqual(cust.customer_id, "C-101")
        self.assertEqual(self.card1.pin_attempts, 0)

    def test_authentication_failed_attempts_and_block(self):
        """Test that a card is blocked after 3 incorrect attempts."""
        # Attempt 1
        with self.assertRaises(InvalidPINError):
            self.bank.authenticate_card("1111-2222-3333-4444", "9999")
        self.assertEqual(self.card1.pin_attempts, 1)
        self.assertEqual(self.card1.status, "ACTIVE")

        # Attempt 2
        with self.assertRaises(InvalidPINError):
            self.bank.authenticate_card("1111-2222-3333-4444", "8888")
        self.assertEqual(self.card1.pin_attempts, 2)
        self.assertEqual(self.card1.status, "ACTIVE")

        # Attempt 3 - should block
        with self.assertRaises(CardBlockedError):
            self.bank.authenticate_card("1111-2222-3333-4444", "7777")
        self.assertEqual(self.card1.pin_attempts, 3)
        self.assertEqual(self.card1.status, "BLOCKED")

        # Try to authenticate a blocked card
        with self.assertRaises(CardBlockedError):
            self.bank.authenticate_card("1111-2222-3333-4444", "1234")

    def test_savings_account_min_balance(self):
        """Test that SavingsAccount enforces minimum balance rule (Rs. 5,000)."""
        # Initial balance is 10,000. 
        # Attempting to withdraw 6,000 (plus Rs. 50 withdrawal fee = 6,050)
        # 10,000 - 6,050 = 3,950, which violates the Rs. 5,000 min balance.
        with self.assertRaises(InsufficientBalanceError):
            self.savings.withdraw(6000.0)

        # Successful withdrawal within limit:
        # Withdraw 4,000 (plus Rs. 50 fee = 4,050). Remaining balance = 5,950 (>= 5,000)
        self.savings.withdraw(4000.0)
        self.assertEqual(self.savings.balance, 5950.0)

    def test_savings_account_transaction_limit(self):
        """Test that SavingsAccount enforces Rs. 50,000 limit per transaction."""
        # Setup high balance to clear min balance checks
        self.savings._balance = 100000.0
        with self.assertRaises(InvalidAmountError):
            self.savings.withdraw(50001.0)

    def test_current_account_overdraft(self):
        """Test that CurrentAccount allows overdrafts up to Rs. 50,000."""
        # Initial: 20,000. Fee is Rs. 0.
        # Withdraw 60,000 (leaves balance of -40,000, which is within the 50,000 overdraft limit)
        self.current.withdraw(60000.0)
        self.assertEqual(self.current.balance, -40000.0)

        # Try to withdraw another 20,000 -> -80,000 (violates Rs. 50,000 overdraft limit)
        with self.assertRaises(InsufficientBalanceError):
            self.current.withdraw(20000.0)

    def test_atm_cash_denominations_dispenser(self):
        """Test the ATM note dispensing backtracking logic."""
        # Total Cash: 5000*2 + 1000*10 + 500*20 = 30,000
        # Request Rs. 7,500
        # Should greedily dispense 1 x 5000, 2 x 1000, 1 x 500 = Rs. 7,500
        dispensed = self.atm.dispense_cash(7500.0)
        self.assertEqual(dispensed, {5000: 1, 1000: 2, 500: 1})
        self.assertEqual(self.atm.get_total_cash(), 22500.0)

        # Now ATM cash counts are: 5000: 1, 1000: 8, 500: 19
        # Request 11,500
        # Should dispense: 1 x 5000, 6 x 1000, 1 x 500 = 11,500
        dispensed2 = self.atm.dispense_cash(11500.0)
        self.assertEqual(dispensed2, {5000: 1, 1000: 6, 500: 1})
        self.assertEqual(self.atm.get_total_cash(), 11000.0)

    def test_atm_cash_dispense_insufficient_or_invalid(self):
        """Test ATM errors for invalid amount formats or cash shortage."""
        # Non-multiple of 500
        with self.assertRaises(InvalidAmountError):
            self.atm.dispense_cash(1234.0)

        # Request more than ATM has
        with self.assertRaises(InsufficientATMFundsError):
            self.atm.dispense_cash(40000.0)

        # Request amount that cannot be represented (e.g. we deplete 500 notes)
        self.atm._cash_denominations = {5000: 0, 1000: 5, 500: 0}  # Only 1000 notes left
        with self.assertRaises(InsufficientATMFundsError):
            self.atm.dispense_cash(1500.0)  # Cannot make 1500 with only 1000s

    def test_money_transfer(self):
        """Test peer-to-peer transfers with validations and double transactions."""
        # Setup receiver
        bob = Customer("C-102", "Bob", "bob@example.com")
        self.bank.register_customer(bob)
        bob_sav = SavingsAccount("SAV-102", "Bob", 10000.0)
        self.bank.add_account("C-102", bob_sav)

        # Alice transfers 3,000 to Bob from her Savings account (fee is 100)
        # Alice balance goes from 10,000 to 10,000 - 3,100 = 6,900
        # Bob balance goes from 10,000 to 13,000
        debit, credit = self.bank.transfer_funds("SAV-101", "SAV-102", 3000.0)

        self.assertEqual(self.savings.balance, 6900.0)
        self.assertEqual(bob_sav.balance, 13000.0)

        # Verify transaction roles
        self.assertEqual(debit.role, "DEBIT")
        self.assertEqual(debit.other_account_number, "SAV-102")
        self.assertEqual(credit.role, "CREDIT")
        self.assertEqual(credit.other_account_number, "SAV-101")

        # Verify statements
        self.assertIn("Trsf to SAV-102", debit.get_statement_line())
        self.assertIn("Trsf fr SAV-101", credit.get_statement_line())

    def test_transfer_validation(self):
        """Test transfer rules: self-transfer, inactive accounts, insufficient balance."""
        bob = Customer("C-102", "Bob", "bob@example.com")
        self.bank.register_customer(bob)
        bob_sav = SavingsAccount("SAV-102", "Bob", 10000.0)
        self.bank.add_account("C-102", bob_sav)

        # Inactive account
        bob_sav.status = "INACTIVE"
        with self.assertRaises(AccountInactiveError):
            self.bank.transfer_funds("SAV-101", "SAV-102", 1000.0)
        bob_sav.status = "ACTIVE"

        # Self transfer
        with self.assertRaises(InvalidAmountError):
            self.bank.transfer_funds("SAV-101", "SAV-101", 1000.0)

        # Insufficient balance (violates min balance of Rs. 5000)
        # Savings balance is 10,000. Fee is 100. Max transfer allowed is 4,900.
        with self.assertRaises(InsufficientBalanceError):
            self.bank.transfer_funds("SAV-101", "SAV-102", 5000.0)

    def test_daily_limits(self):
        """Test tracking and enforcement of daily limits."""
        # Savings account daily withdrawal limit: Rs. 100,000
        self.savings._balance = 200000.0
        
        # Withdraw 40,000 (ok)
        self.savings.withdraw(40000.0)
        # Withdraw 50,000 (ok) - note: Savings max single transaction is 50,000
        self.savings.withdraw(50000.0)
        
        # Total withdrawn today: 90,000. Next withdrawal of 15,000 should fail (exceeds 100,000 daily limit)
        with self.assertRaises(DailyLimitExceededError):
            self.savings.withdraw(15000.0)

    def test_daily_limit_rollover(self):
        """Test daily limits reset when a new day begins."""
        self.savings._balance = 200000.0
        self.savings.withdraw(40000.0)
        self.assertEqual(self.savings.daily_withdrawal_total, 40000.0)

        # Simulate date change by moving reset date to yesterday
        self.savings._last_limit_reset = date.today() - timedelta(days=1)
        
        # Checking balance or withdrawing should trigger reset
        self.savings.reset_daily_limits_if_needed()
        self.assertEqual(self.savings.daily_withdrawal_total, 0.0)

        # Now should be able to withdraw again
        self.savings.withdraw(40000.0)
        self.assertEqual(self.savings.daily_withdrawal_total, 40000.0)

if __name__ == "__main__":
    unittest.main()
