import unittest
from fastapi.testclient import TestClient
from main import app, session, load_default_data, bank, atm

class TestWebATMAPI(unittest.TestCase):
    """
    Unit tests for the Web ATM FastAPI endpoints.
    Verifies routing, session state, transaction success, and error payloads.
    """
    def setUp(self):
        self.client = TestClient(app)
        # Clear session
        session.active_card = None
        session.active_customer = None
        session.active_account = None
        
        # Reload demo database
        load_default_data()

    def test_get_cards(self):
        """Test listing available cards."""
        res = self.client.get("/api/cards")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreater(len(data), 0)
        # Check John's card is present
        card_nums = [c["card_number"] for c in data]
        self.assertIn("1111-2222-3333-4444", card_nums)

    def test_insert_card_success(self):
        """Test card insertion with correct PIN."""
        res = self.client.post("/api/insert-card", json={
            "card_number": "1111-2222-3333-4444",
            "pin": "4321"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["customer_name"], "John Doe")
        self.assertEqual(data["active_account"]["account_number"], "SAV-1001")

    def test_insert_card_failed_pin(self):
        """Test authentication error for invalid credentials."""
        # Correct card, wrong PIN
        res = self.client.post("/api/insert-card", json={
            "card_number": "1111-2222-3333-4444",
            "pin": "9999"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("Incorrect PIN", res.json()["detail"])

    def test_session_state(self):
        """Test checking session status before and after login."""
        # Pre-login
        res_pre = self.client.get("/api/session")
        self.assertEqual(res_pre.status_code, 200)
        self.assertFalse(res_pre.json()["authenticated"])

        # Login
        self.client.post("/api/insert-card", json={
            "card_number": "1111-2222-3333-4444",
            "pin": "4321"
        })

        # Post-login
        res_post = self.client.get("/api/session")
        self.assertEqual(res_post.status_code, 200)
        data = res_post.json()
        self.assertTrue(data["authenticated"])
        self.assertEqual(data["customer_name"], "John Doe")
        self.assertEqual(data["active_account"]["account_number"], "SAV-1001")

    def test_switch_account(self):
        """Test switching active account for the customer."""
        # Login John
        self.client.post("/api/insert-card", json={
            "card_number": "1111-2222-3333-4444",
            "pin": "4321"
        })

        # Switch to current account
        res = self.client.post("/api/switch-account", json={"account_number": "CUR-1001"})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["success"])

        # Check session reflects switch
        res_session = self.client.get("/api/session")
        self.assertEqual(res_session.json()["active_account"]["account_number"], "CUR-1001")

    def test_deposit(self):
        """Test depositing money."""
        # Login
        self.client.post("/api/insert-card", json={
            "card_number": "1111-2222-3333-4444",
            "pin": "4321"
        })

        # John Savings initial: Rs. 25,000. Deposit 5,000.
        res = self.client.post("/api/deposit", json={"amount": 5000.0})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["new_balance"], 30000.0)

    def test_withdrawal_and_denominations(self):
        """Test withdrawal triggers notes dispensing breakdown."""
        # Login John
        self.client.post("/api/insert-card", json={
            "card_number": "1111-2222-3333-4444",
            "pin": "4321"
        })

        # John Savings initial balance: Rs. 25,000.
        # Withdraw Rs. 7,500. (Savings fee is Rs. 50, so total deduction = 7550, leaving 17,450.
        # Remaining balance (17450) is greater than Rs. 5,000 min balance.
        # 7,500 should dispense: 1 x 5000, 2 x 1000, 1 x 500 notes.
        res = self.client.post("/api/withdraw", json={"amount": 7500.0})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["new_balance"], 17450.0)
        self.assertEqual(data["fee"], 50.0)
        self.assertEqual(data["dispensed_notes"], {"5000": 1, "1000": 2, "500": 1})

    def test_withdrawal_insufficient_atm_funds(self):
        """Test withdrawal failure when ATM doesn't have sufficient notes."""
        # Login
        self.client.post("/api/insert-card", json={
            "card_number": "1111-2222-3333-4444",
            "pin": "4321"
        })

        # Try to withdraw more than ATM cash (ATM starts with 100,000)
        res = self.client.post("/api/withdraw", json={"amount": 105000.0})
        self.assertEqual(res.status_code, 400)
        self.assertIn("enough cash", res.json()["detail"].lower())

    def test_transfer_funds(self):
        """Test peer-to-peer transfer between accounts."""
        # Login John (SAV-1001: 25,000)
        self.client.post("/api/insert-card", json={
            "card_number": "1111-2222-3333-4444",
            "pin": "4321"
        })

        # Transfer 10,000 to Jane Savings (SAV-1002)
        # Fee is Rs. 100. John balance: 25,000 - 10,100 = 14,900.
        res = self.client.post("/api/transfer", json={
            "target_account_number": "SAV-1002",
            "amount": 10000.0
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["new_balance"], 14900.0)

    def test_admin_restock(self):
        """Test restocking ATM vault notes."""
        # Restock 2 x 5000, 5 x 1000, 10 x 500 = 10000 + 5000 + 5000 = Rs. 20,000.
        # ATM total starts at 100,000. New total = 120,000.
        res = self.client.post("/api/admin/restock", json={
            "notes_5000": 2,
            "notes_1000": 5,
            "notes_500": 10
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["new_vault_total"], 120000.0)

if __name__ == "__main__":
    unittest.main()
