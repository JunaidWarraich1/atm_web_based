# Grand OOP Bank Web ATM System (atmproject2)

A premium, full-featured web application simulating a physical bank ATM. Built with a robust **Python FastAPI backend** running strict Object-Oriented Programming (OOP) models and a modern, responsive **Single-Page Application (HTML/CSS/JS) frontend** that represents an interactive ATM terminal.

---

## 🏛️ OOP Architecture & Domain Logic

This project inherits the strict OOP design patterns from the core bank models:
1. **Abstraction**: Base classes `Account` and `Transaction` define contract actions for concrete accounts and statements.
2. **Encapsulation**: Private state variables (e.g. balance, PIN hash, card block status, banknote counts) are protected and only mutated through verified method calls.
3. **Inheritance**: Subclasses `SavingsAccount` (minimum balance constraint) and `CurrentAccount` (overdraft limit constraint) inherit from `Account`. Subclasses `DepositTransaction`, `WithdrawalTransaction`, and `TransferTransaction` inherit from `Transaction`.
4. **Polymorphism**: Account subclasses implement custom transactional fees and withdraw limit calculators dynamically evaluated at runtime.

---

## 🔒 Advanced Web Features

1. **Interactive Keypad & Screens**: Use the physical metallic keys on the mock ATM body to type your PIN, deposit amount, custom withdrawal sum, or transfer receiver.
2. **Backtracking Cash Dispenser**: Withdrawal requests run a backtracking note dispenser algorithm on the ATM vault to determine if the exact amount can be composed using available **Rs. 5,000**, **Rs. 1,000**, and **Rs. 500** notes.
3. **Physical Slot Animations**:
   * Inserting/Ejecting cards updates the physical card reader.
   * Successful withdrawals slide banknotes out of the Cash Dispenser slot (click notes to "collect" and open the receipt popup).
4. **Bank Database Admin Monitor (Right Side)**:
   * View all bank customers, card block status, fail counters, and account limit usage in real-time.
   * Restock ATM notes (manually load 500, 1000, or 5000 rupee notes).
   * Simulate a new day limits reset.
   * Perform database factory resets.
5. **JSON Data Persistence**: The bank database state is saved to `data/bank_state.json` and updates live as you interact with the ATM.

---

## 🚀 How to Run the Web Application

### 1. Install Dependencies
Ensure you have the required Python web packages installed:

```bash
pip install fastapi uvicorn httpx
```

### 2. Start the Server
Navigate to the project folder and launch the FastAPI server:

```bash
cd "C:\Users\hp\Documents\antigravity\atmproject2"
python main.py
```

### 3. Open the UI
Open your browser and navigate to:
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 💳 Demo Logins & Credentials

Select a card from the simulator dropdown and log in with these credentials:

| Card Number | Account Number | Holder | Account Type | Default PIN | Initial Balance | Special Rules |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`1111-2222-3333-4444`** | `SAV-1001` | John Doe | **Savings** | `4321` | Rs. 25,000 | Min Balance: Rs. 5,000 |
| **`1111-2222-3333-4444`** | `CUR-1001` | John Doe | **Current** | `4321` | Rs. 10,000 | Overdraft: up to Rs. 50,000 |
| **`5555-6666-7777-8888`** | - | John Doe | Secondary Card | `5678` | - | Multiple cards testing |
| **`9876-5432-1098-7654`** | `SAV-1002` | Jane Smith | **Savings** | `1984` | Rs. 75,000 | Min Balance: Rs. 5,000 |

* **ATM Vault Reserves**: Starts with Rs. 100,000 (10 x 5000 notes, 30 x 1000 notes, 40 x 500 notes).

---

## 🧪 Running tests

We provide two unit test suites to verify backend model constraints and API route behaviors:

```bash
# Test backend OOP models
python -m unittest tests/test_atm.py

# Test API route endpoints
python -m unittest tests/test_api.py
```
