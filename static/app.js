// --- STATE VARIABLES ---
let activeSession = null;
let currentScreen = "insert-card";

// Keypad buffers for different screen states
let pinInput = "";
let amountInput = ""; // Used for custom withdraw and deposit
let transferRecipient = "";
let transferAmount = "";
let transferActiveField = "recipient"; // 'recipient' or 'amount'

let pinChangeOld = "";
let pinChangeNew = "";
let pinChangeActiveField = "old"; // 'old' or 'new'

// List of HTML Screen Elements
const screens = {
    "insert-card": document.getElementById("screen-insert-card"),
    "enter-pin": document.getElementById("screen-enter-pin"),
    "main-menu": document.getElementById("screen-main-menu"),
    "balance": document.getElementById("screen-balance"),
    "deposit": document.getElementById("screen-deposit"),
    "withdraw": document.getElementById("screen-withdraw"),
    "transfer": document.getElementById("screen-transfer"),
    "change-pin": document.getElementById("screen-change-pin"),
    "statement": document.getElementById("screen-statement"),
    "switch-account": document.getElementById("screen-switch-account"),
    "processing": document.getElementById("screen-processing"),
    "success": document.getElementById("screen-success")
};

// --- INITIALIZATION ---
document.addEventListener("DOMContentLoaded", () => {
    initApp();
    setupKeypad();
    setupAdminPanel();
});

async function initApp() {
    await fetchCards();
    await checkSession();
    await updateAdminView();

    // Event listener: Card Insertion
    document.getElementById("btn-insert-selected-card").addEventListener("click", handleInsertCard);
    
    // Back to main menu buttons (class-based)
    document.querySelectorAll(".btn-menu-back").forEach(btn => {
        btn.addEventListener("click", () => showScreen("main-menu"));
    });

    // Preset withdrawals
    document.querySelectorAll(".preset-btn").forEach(btn => {
        if (btn.id !== "btn-custom-withdraw") {
            btn.addEventListener("click", (e) => {
                const amt = parseFloat(e.target.dataset.amount);
                submitWithdraw(amt);
            });
        }
    });

    // Custom withdrawal toggle
    document.getElementById("btn-custom-withdraw").addEventListener("click", () => {
        document.getElementById("custom-withdraw-area").classList.remove("hidden");
        document.getElementById("btn-confirm-withdraw").classList.remove("hidden");
        amountInput = "";
        updateAmountDisplay("withdraw-amount-display", amountInput);
    });

    // Submits via buttons (if not using enter key on physical keyboard)
    document.getElementById("btn-confirm-deposit").addEventListener("click", handleDepositConfirm);
    document.getElementById("btn-cancel-deposit").addEventListener("click", () => showScreen("main-menu"));
    
    document.getElementById("btn-confirm-withdraw").addEventListener("click", () => {
        if (amountInput) {
            submitWithdraw(parseFloat(amountInput));
        }
    });
    document.getElementById("btn-cancel-withdraw").addEventListener("click", () => showScreen("main-menu"));

    document.getElementById("btn-confirm-transfer").addEventListener("click", handleTransferConfirm);
    document.getElementById("btn-cancel-transfer").addEventListener("click", () => showScreen("main-menu"));

    document.getElementById("btn-confirm-change-pin").addEventListener("click", handlePinChangeConfirm);
    document.getElementById("btn-cancel-change-pin").addEventListener("click", () => showScreen("main-menu"));

    // Menu Screen Navigation (labels mock clicks)
    document.querySelectorAll(".menu-btn").forEach(btn => {
        btn.addEventListener("click", (e) => {
            const action = e.target.dataset.action;
            handleMenuNavigation(action);
        });
    });

    // Eject Card slot click (collect card)
    document.getElementById("card-slot-inlet").addEventListener("click", () => {
        if (activeSession) {
            handleEjectCard();
        }
    });

    // Cash Slot click (collect cash)
    document.getElementById("cash-slot-inlet").addEventListener("click", handleCollectCash);
    document.getElementById("btn-modal-collect-cash").addEventListener("click", handleCollectCash);

    // Click inputs in forms to switch active fields
    document.getElementById("transfer-field-recipient").addEventListener("click", () => {
        transferActiveField = "recipient";
        highlightTransferFields();
    });
    document.getElementById("transfer-field-amount").addEventListener("click", () => {
        transferActiveField = "amount";
        highlightTransferFields();
    });

    document.getElementById("pin-field-old").addEventListener("click", () => {
        pinChangeActiveField = "old";
        highlightPinFields();
    });
    document.getElementById("pin-field-new").addEventListener("click", () => {
        pinChangeActiveField = "new";
        highlightPinFields();
    });
}

// --- SESSION MANAGEMENT ---

async function checkSession() {
    try {
        const res = await fetch("/api/session");
        const data = await res.json();
        if (data.authenticated) {
            activeSession = data;
            showScreen("main-menu");
            updateMenuDisplay();
            // Show card inserted in physical slot
            document.getElementById("card-in-slot").classList.add("active");
        } else {
            activeSession = null;
            showScreen("insert-card");
            document.getElementById("card-in-slot").classList.remove("active");
        }
    } catch (e) {
        console.error("Session check failed", e);
    }
}

async function fetchCards() {
    try {
        const res = await fetch("/api/cards");
        const cards = await res.json();
        const select = document.getElementById("simulation-card-select");
        
        // Save current selection index if exists
        const prevVal = select.value;
        select.innerHTML = '<option value="" disabled selected>-- Select Card --</option>';
        
        cards.forEach(card => {
            const opt = document.createElement("option");
            opt.value = card.card_number;
            opt.textContent = `${card.holder_name} (${card.card_number.substring(0, 4)}...) - ${card.status}`;
            if (card.status === "BLOCKED") {
                opt.disabled = true;
                opt.textContent += " [BLOCKED]";
            }
            select.appendChild(opt);
        });

        if (prevVal) {
            select.value = prevVal;
        }
    } catch (e) {
        console.error("Error fetching cards", e);
    }
}

async function handleInsertCard() {
    const cardNum = document.getElementById("simulation-card-select").value;
    if (!cardNum) {
        alert("Please select a simulation card first.");
        return;
    }
    
    // Simulate inserting card visual
    document.getElementById("card-in-slot").classList.add("active");
    pinInput = "";
    updatePinDots();
    document.getElementById("pin-error-message").textContent = "";
    document.getElementById("pin-attempts-warning").textContent = "";
    
    setTimeout(() => {
        showScreen("enter-pin");
    }, 400);
}

async function handleEjectCard() {
    showLoading("Ejecting Card...");
    try {
        const res = await fetch("/api/eject-card", { method: "POST" });
        await res.json();
        activeSession = null;
        document.getElementById("card-in-slot").classList.remove("active");
        showScreen("insert-card");
        await fetchCards();
        await updateAdminView();
    } catch (e) {
        console.error(e);
    }
}

// --- SCREEN SWITCHER ---
function showScreen(screenId) {
    currentScreen = screenId;
    
    // Reset buffers
    pinInput = "";
    amountInput = "";
    transferRecipient = "";
    transferAmount = "";
    transferActiveField = "recipient";
    pinChangeOld = "";
    pinChangeNew = "";
    pinChangeActiveField = "old";

    for (const key in screens) {
        if (key === screenId) {
            screens[key].classList.add("active");
        } else {
            screens[key].classList.remove("active");
        }
    }

    // Custom screen triggers
    if (screenId === "main-menu") {
        updateMenuDisplay();
    } else if (screenId === "balance") {
        loadBalanceScreen();
    } else if (screenId === "statement") {
        loadStatementScreen();
    } else if (screenId === "switch-account") {
        loadSwitchAccountScreen();
    } else if (screenId === "deposit") {
        document.getElementById("deposit-error-message").textContent = "";
        updateAmountDisplay("deposit-amount-display", amountInput);
    } else if (screenId === "withdraw") {
        document.getElementById("withdraw-error-message").textContent = "";
        document.getElementById("custom-withdraw-area").classList.add("hidden");
        document.getElementById("btn-confirm-withdraw").classList.add("hidden");
        updateAmountDisplay("withdraw-amount-display", amountInput);
    } else if (screenId === "transfer") {
        document.getElementById("transfer-error-message").textContent = "";
        highlightTransferFields();
        updateTransferFieldDisplays();
    } else if (screenId === "change-pin") {
        document.getElementById("pin-change-error-message").textContent = "";
        highlightPinFields();
        updatePinChangeFieldDisplays();
    }
}

function showLoading(text) {
    document.getElementById("processing-loading-text").textContent = text;
    showScreen("processing");
}

// --- KEYPAD LOGIC ---
function setupKeypad() {
    document.querySelectorAll(".key-num").forEach(btn => {
        btn.addEventListener("click", () => {
            const val = btn.dataset.val;
            handleKeypadNumber(val);
        });
    });

    document.getElementById("keypad-clear").addEventListener("click", handleKeypadClear);
    document.getElementById("keypad-cancel").addEventListener("click", handleKeypadCancel);
    document.getElementById("keypad-enter").addEventListener("click", handleKeypadEnter);
}

function handleKeypadNumber(val) {
    if (currentScreen === "enter-pin") {
        if (pinInput.length < 4) {
            pinInput += val;
            updatePinDots();
        }
    } 
    else if (currentScreen === "deposit") {
        if (amountInput.length < 9) { // Max digits check
            amountInput += val;
            updateAmountDisplay("deposit-amount-display", amountInput);
        }
    } 
    else if (currentScreen === "withdraw") {
        // Only if custom amount input is visible
        const customArea = document.getElementById("custom-withdraw-area");
        if (!customArea.classList.contains("hidden")) {
            if (amountInput.length < 9) {
                amountInput += val;
                updateAmountDisplay("withdraw-amount-display", amountInput);
            }
        }
    } 
    else if (currentScreen === "transfer") {
        if (transferActiveField === "recipient") {
            if (transferRecipient.length < 12) {
                transferRecipient += val;
                updateTransferFieldDisplays();
            }
        } else {
            if (transferAmount.length < 9) {
                transferAmount += val;
                updateTransferFieldDisplays();
            }
        }
    } 
    else if (currentScreen === "change-pin") {
        if (pinChangeActiveField === "old") {
            if (pinChangeOld.length < 4) {
                pinChangeOld += val;
                updatePinChangeFieldDisplays();
            }
        } else {
            if (pinChangeNew.length < 4) {
                pinChangeNew += val;
                updatePinChangeFieldDisplays();
            }
        }
    }
}

function handleKeypadClear() {
    if (currentScreen === "enter-pin") {
        pinInput = "";
        updatePinDots();
    } 
    else if (currentScreen === "deposit") {
        amountInput = "";
        updateAmountDisplay("deposit-amount-display", amountInput);
    } 
    else if (currentScreen === "withdraw") {
        amountInput = "";
        updateAmountDisplay("withdraw-amount-display", amountInput);
    } 
    else if (currentScreen === "transfer") {
        if (transferActiveField === "recipient") {
            transferRecipient = "";
        } else {
            transferAmount = "";
        }
        updateTransferFieldDisplays();
    } 
    else if (currentScreen === "change-pin") {
        if (pinChangeActiveField === "old") {
            pinChangeOld = "";
        } else {
            pinChangeNew = "";
        }
        updatePinChangeFieldDisplays();
    }
}

function handleKeypadCancel() {
    if (currentScreen === "enter-pin" || currentScreen === "insert-card") {
        handleEjectCard();
    } else {
        // Go back to menu from sub-screens
        showScreen("main-menu");
    }
}

function handleKeypadEnter() {
    if (currentScreen === "enter-pin") {
        if (pinInput.length === 4) {
            submitPINLogin();
        }
    } 
    else if (currentScreen === "deposit") {
        handleDepositConfirm();
    } 
    else if (currentScreen === "withdraw") {
        if (amountInput) {
            submitWithdraw(parseFloat(amountInput));
        }
    } 
    else if (currentScreen === "transfer") {
        handleTransferConfirm();
    } 
    else if (currentScreen === "change-pin") {
        handlePinChangeConfirm();
    }
}

// --- UPDATE UI DISPLAYS FOR BUFFERS ---
function updatePinDots() {
    const dots = document.querySelectorAll("#pin-dots .dot");
    dots.forEach((dot, idx) => {
        if (idx < pinInput.length) {
            dot.classList.add("filled");
        } else {
            dot.classList.remove("filled");
        }
    });
}

function updateAmountDisplay(elementId, val) {
    const display = document.getElementById(elementId);
    if (!val) {
        display.textContent = "Rs. 0";
    } else {
        display.textContent = `Rs. ${parseFloat(val).toLocaleString()}`;
    }
}

function updateTransferFieldDisplays() {
    const recDisplay = document.getElementById("transfer-field-recipient");
    const amtDisplay = document.getElementById("transfer-field-amount");

    recDisplay.textContent = transferRecipient ? transferRecipient : "Enter Number";
    amtDisplay.textContent = transferAmount ? `Rs. ${parseFloat(transferAmount).toLocaleString()}` : "Rs. 0";
}

function highlightTransferFields() {
    const recDisplay = document.getElementById("transfer-field-recipient");
    const amtDisplay = document.getElementById("transfer-field-amount");

    if (transferActiveField === "recipient") {
        recDisplay.classList.add("active-field");
        amtDisplay.classList.remove("active-field");
    } else {
        recDisplay.classList.remove("active-field");
        amtDisplay.classList.add("active-field");
    }
}

function updatePinChangeFieldDisplays() {
    const oldDisplay = document.getElementById("pin-field-old");
    const newDisplay = document.getElementById("pin-field-new");

    oldDisplay.textContent = "•".repeat(pinChangeOld.length) + "-".repeat(4 - pinChangeOld.length);
    newDisplay.textContent = "•".repeat(pinChangeNew.length) + "-".repeat(4 - pinChangeNew.length);
}

function highlightPinFields() {
    const oldDisplay = document.getElementById("pin-field-old");
    const newDisplay = document.getElementById("pin-field-new");

    if (pinChangeActiveField === "old") {
        oldDisplay.classList.add("active-field");
        newDisplay.classList.remove("active-field");
    } else {
        oldDisplay.classList.remove("active-field");
        newDisplay.classList.add("active-field");
    }
}

// --- SUBMISSION ACTIONS ---

async function submitPINLogin() {
    const cardNum = document.getElementById("simulation-card-select").value;
    const pinVal = pinInput; // Capture input before loading screen clears buffer
    showLoading("Authenticating PIN...");
    
    try {
        const res = await fetch("/api/insert-card", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ card_number: cardNum, pin: pinVal })
        });
        const data = await res.json();
        
        if (res.ok) {
            await checkSession();
            await updateAdminView();
        } else {
            showScreen("enter-pin");
            document.getElementById("pin-error-message").textContent = data.detail;
            
            // Check if card was blocked
            if (data.detail.toLowerCase().includes("blocked")) {
                document.getElementById("pin-attempts-warning").textContent = "Your card is now BLOCKED.";
            }
            await fetchCards();
            await updateAdminView();
        }
    } catch (e) {
        showScreen("enter-pin");
        document.getElementById("pin-error-message").textContent = "Connection error. Try again.";
    }
}

function updateMenuDisplay() {
    if (!activeSession) return;
    document.getElementById("menu-holder-name").textContent = activeSession.customer_name;
    if (activeSession.active_account) {
        document.getElementById("menu-active-account").textContent = `${activeSession.active_account.account_number} (${activeSession.active_account.type})`;
    } else {
        document.getElementById("menu-active-account").textContent = "No Account";
    }
}

function handleMenuNavigation(action) {
    if (action === "eject") {
        handleEjectCard();
    } else if (action === "balance") {
        showScreen("balance");
    } else if (action === "deposit") {
        showScreen("deposit");
    } else if (action === "withdraw") {
        showScreen("withdraw");
    } else if (action === "transfer") {
        showScreen("transfer");
    } else if (action === "pin") {
        showScreen("change-pin");
    } else if (action === "statement") {
        showScreen("statement");
    } else if (action === "switch") {
        showScreen("switch-account");
    }
}

async function loadBalanceScreen() {
    showLoading("Checking account parameters...");
    try {
        const res = await fetch("/api/session");
        const data = await res.json();
        if (res.ok && data.active_account) {
            activeSession = data;
            document.getElementById("balance-account-number").textContent = `${data.active_account.account_number} (${data.active_account.type})`;
            document.getElementById("balance-amount").textContent = `Rs. ${data.active_account.balance.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
            document.getElementById("balance-withdrawable").textContent = `Rs. ${data.active_account.withdrawal_limit.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
            showScreen("balance");
        } else {
            showScreen("main-menu");
        }
    } catch (e) {
        showScreen("main-menu");
    }
}

async function handleDepositConfirm() {
    if (!amountInput) {
        document.getElementById("deposit-error-message").textContent = "Please enter an amount.";
        return;
    }
    const amt = parseFloat(amountInput);
    showLoading("Depositing Cash...");
    try {
        const res = await fetch("/api/deposit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ amount: amt })
        });
        const data = await res.json();
        if (res.ok) {
            showSuccess(
                `Cash Deposit Successful!<br>
                 Amount: Rs. ${amt.toLocaleString()}<br>
                 Transaction ID: ${data.transaction_id}<br>
                 New Balance: Rs. ${data.new_balance.toLocaleString('en-US', {minimumFractionDigits: 2})}`
            );
            await updateAdminView();
        } else {
            showScreen("deposit");
            document.getElementById("deposit-error-message").textContent = data.detail;
        }
    } catch (e) {
        showScreen("deposit");
        document.getElementById("deposit-error-message").textContent = "Failed to deposit. Check network connection.";
    }
}

async function submitWithdraw(amount) {
    showLoading("Validating cash dispenser reserves...");
    try {
        const res = await fetch("/api/withdraw", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ amount: amount })
        });
        const data = await res.json();
        
        if (res.ok) {
            // Trigger Cash Dispensed Visual!
            document.getElementById("cash-slot-inlet").classList.add("active");
            document.getElementById("cash-notes-dispensed").classList.add("active");

            // Open popup modal for cash collection
            const breakdownContent = document.getElementById("modal-dispensed-notes-content");
            breakdownContent.innerHTML = "<h4>Dispensed Breakdown:</h4><ul>";
            for (const note in data.dispensed_notes) {
                breakdownContent.innerHTML += `<li><span>Rs. ${note} notes:</span> <strong>${data.dispensed_notes[note]}</strong></li>`;
            }
            breakdownContent.innerHTML += "</ul>";
            
            document.getElementById("cash-collection-modal").classList.remove("hidden");

            // Show success details on screen
            showSuccess(
                `Withdrawal Successful!<br>
                 Amount Collected: Rs. ${amount.toLocaleString()}<br>
                 Transaction ID: ${data.transaction_id}<br>
                 Fee Deducted: Rs. ${data.fee}<br>
                 New Account Balance: Rs. ${data.new_balance.toLocaleString('en-US', {minimumFractionDigits: 2})}`
            );
            await updateAdminView();
        } else {
            showScreen("withdraw");
            document.getElementById("withdraw-error-message").textContent = data.detail;
        }
    } catch (e) {
        showScreen("withdraw");
        document.getElementById("withdraw-error-message").textContent = "Withdrawal failed. Check network connection.";
    }
}

function handleCollectCash() {
    // Hide visual cash dispensed
    document.getElementById("cash-slot-inlet").classList.remove("active");
    document.getElementById("cash-notes-dispensed").classList.remove("active");
    document.getElementById("cash-collection-modal").classList.add("hidden");
}

async function handleTransferConfirm() {
    if (!transferRecipient) {
        document.getElementById("transfer-error-message").textContent = "Please enter target account number.";
        return;
    }
    if (!transferAmount) {
        document.getElementById("transfer-error-message").textContent = "Please enter transfer amount.";
        return;
    }
    
    const targetAcc = transferRecipient; // Capture before loading clears buffer
    const amt = parseFloat(transferAmount);
    showLoading("Executing double-ledger transfer...");
    try {
        const res = await fetch("/api/transfer", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ target_account_number: targetAcc, amount: amt })
        });
        const data = await res.json();
        
        if (res.ok) {
            showSuccess(
                `Money Transfer Completed!<br>
                 Recipient Account: ${transferRecipient}<br>
                 Amount Sent: Rs. ${amt.toLocaleString()}<br>
                 Transaction Fee: Rs. ${data.fee}<br>
                 Transaction ID: ${data.transaction_id}<br>
                 New Balance: Rs. ${data.new_balance.toLocaleString('en-US', {minimumFractionDigits: 2})}`
            );
            await updateAdminView();
        } else {
            showScreen("transfer");
            document.getElementById("transfer-error-message").textContent = data.detail;
        }
    } catch (e) {
        showScreen("transfer");
        document.getElementById("transfer-error-message").textContent = "Transfer failed. Check network connection.";
    }
}

async function handlePinChangeConfirm() {
    if (pinChangeOld.length < 4 || pinChangeNew.length < 4) {
        document.getElementById("pin-change-error-message").textContent = "PINs must be exactly 4 digits.";
        return;
    }
    
    const oldPinVal = pinChangeOld; // Capture before loading clears buffer
    const newPinVal = pinChangeNew;
    showLoading("Validating card security constraints...");
    try {
        const res = await fetch("/api/change-pin", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ old_pin: oldPinVal, new_pin: newPinVal })
        });
        const data = await res.json();
        
        if (res.ok) {
            showSuccess("Card PIN changed successfully!<br>Please remember your new PIN for future transactions.");
            await updateAdminView();
        } else {
            showScreen("change-pin");
            document.getElementById("pin-change-error-message").textContent = data.detail;
        }
    } catch (e) {
        showScreen("change-pin");
        document.getElementById("pin-change-error-message").textContent = "Failed to update PIN. Connection error.";
    }
}

async function loadStatementScreen() {
    try {
        const res = await fetch("/api/statement");
        const rows = await res.json();
        
        const container = document.getElementById("statement-rows");
        container.innerHTML = "";
        
        rows.forEach(r => {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${r.date}</td>
                <td>${r.description}</td>
                <td class="${r.amount.startsWith('-') ? 'text-red' : 'text-green'}">${r.amount}</td>
                <td>${r.status}</td>
            `;
            container.appendChild(row);
        });

        // Fetch balance details to display
        const resSession = await fetch("/api/session");
        const sessionData = await resSession.json();
        document.getElementById("statement-final-balance").textContent = `Rs. ${sessionData.active_account.balance.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        
    } catch (e) {
        console.error(e);
    }
}

async function loadSwitchAccountScreen() {
    try {
        const res = await fetch("/api/session");
        const data = await res.json();
        
        const container = document.getElementById("account-list-container");
        container.innerHTML = "";
        
        data.accounts.forEach(acc => {
            const btn = document.createElement("div");
            btn.className = `account-row-btn ${acc.account_number === data.active_account.account_number ? 'active' : ''}`;
            btn.innerHTML = `
                <span>${acc.account_number} (${acc.type})</span>
                <strong>Rs. ${acc.balance.toLocaleString()}</strong>
            `;
            btn.addEventListener("click", () => switchAccount(acc.account_number));
            container.appendChild(btn);
        });
    } catch (e) {
        console.error(e);
    }
}

async function switchAccount(accNum) {
    showLoading("Connecting to account server...");
    try {
        const res = await fetch("/api/switch-account", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ account_number: accNum })
        });
        if (res.ok) {
            await checkSession();
            showScreen("main-menu");
        } else {
            showScreen("main-menu");
        }
    } catch (e) {
        showScreen("main-menu");
    }
}

function showSuccess(detailsHtml) {
    document.getElementById("success-details-content").innerHTML = detailsHtml;
    showScreen("success");
}

// --- ADMIN PANEL CONTROLLER ---
function setupAdminPanel() {
    // Restock Button click
    document.getElementById("btn-admin-restock").addEventListener("click", async () => {
        const n5000 = parseInt(document.getElementById("input-restock-5000").value || "0");
        const n1000 = parseInt(document.getElementById("input-restock-1000").value || "0");
        const n500 = parseInt(document.getElementById("input-restock-500").value || "0");

        try {
            const res = await fetch("/api/admin/restock", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ notes_5000: n5000, notes_1000: n1000, notes_500: n500 })
            });
            const data = await res.json();
            if (res.ok) {
                alert("ATM Vault successfully restocked!");
                // Clear inputs
                document.getElementById("input-restock-5000").value = "";
                document.getElementById("input-restock-1000").value = "";
                document.getElementById("input-restock-500").value = "";
                await updateAdminView();
            } else {
                alert(`Error: ${data.detail}`);
            }
        } catch (e) {
            alert("Restock command failed.");
        }
    });

    // Reset Limits click
    document.getElementById("btn-admin-reset-limits").addEventListener("click", async () => {
        try {
            const res = await fetch("/api/admin/reset-limits", { method: "POST" });
            const data = await res.json();
            if (res.ok) {
                alert(data.message);
                await updateAdminView();
            }
        } catch (e) {
            alert("Limit reset command failed.");
        }
    });

    // Reset DB click
    document.getElementById("btn-admin-reset-db").addEventListener("click", async () => {
        if (confirm("This will erase all custom transactions, limits, and reset to default demo accounts. Are you sure?")) {
            try {
                const res = await fetch("/api/admin/reset", { method: "POST" });
                const data = await res.json();
                if (res.ok) {
                    alert(data.message);
                    await checkSession();
                    await fetchCards();
                    await updateAdminView();
                }
            } catch (e) {
                alert("Database wipe failed.");
            }
        }
    });
}

async function updateAdminView() {
    try {
        const res = await fetch("/api/admin/status");
        if (!res.ok) return;
        const data = await res.json();

        // Update ATM Vault numbers
        document.getElementById("admin-vault-total").textContent = `Rs. ${data.vault_total.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
        document.getElementById("admin-count-5000").textContent = `${data.denominations['5000']} notes`;
        document.getElementById("admin-count-1000").textContent = `${data.denominations['1000']} notes`;
        document.getElementById("admin-count-500").textContent = `${data.denominations['500']} notes`;

        // Update Customers list
        const listContainer = document.getElementById("admin-db-users-list");
        listContainer.innerHTML = "";

        data.customers.forEach(cust => {
            const card = document.createElement("div");
            card.className = "admin-customer-card";
            
            // Build header
            let content = `
                <div class="admin-customer-info">
                    <span class="name">${cust.name}</span>
                    <span class="id">ID: ${cust.customer_id}</span>
                </div>
            `;

            // Cards section
            content += `<div class="admin-cards-list"><strong>Cards:</strong>`;
            cust.cards.forEach(c => {
                const isBlocked = c.status === "BLOCKED";
                content += `
                    <div class="admin-card-row">
                        <span>💳 ${c.card_number} (failed: ${c.attempts}/3)</span>
                        <button class="status-toggle ${isBlocked ? 'text-red' : 'text-green'}" 
                                onclick="adminToggleCard('${c.card_number}', '${isBlocked ? 'ACTIVE' : 'BLOCKED'}')">
                            ${c.status}
                        </button>
                    </div>
                `;
            });
            content += `</div>`;

            // Accounts section
            content += `<div class="admin-accounts-list"><strong>Accounts:</strong>`;
            cust.accounts.forEach(acc => {
                content += `
                    <div class="admin-account-row">
                        <span>🏦 ${acc.account_number} (${acc.type}) [${acc.status}]</span>
                        <strong class="text-green">Rs. ${acc.balance.toLocaleString('en-US', {minimumFractionDigits: 2})}</strong>
                    </div>
                    <div class="admin-account-row text-blue limits-detail">
                        <span>Limit totals: W:${acc.daily_withdrawal_total.toLocaleString()}/100k | T:${acc.daily_transfer_total.toLocaleString()}/150k</span>
                    </div>
                `;
            });
            content += `</div>`;

            card.innerHTML = content;
            listContainer.appendChild(card);
        });

    } catch (e) {
        console.error("Admin view update failed", e);
    }
}

// Exposed globally for admin list button clicks
async function adminToggleCard(cardNum, targetStatus) {
    try {
        const res = await fetch("/api/admin/toggle-card", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ card_number: cardNum, status: targetStatus })
        });
        if (res.ok) {
            await fetchCards();
            await checkSession();
            await updateAdminView();
        }
    } catch (e) {
        console.error(e);
    }
}
window.adminToggleCard = adminToggleCard;

// Add physical keyboard listener
document.addEventListener("keydown", (e) => {
    // If user is typing in administrative input fields, don't hijack keyboard inputs
    if (e.target.tagName === "INPUT") {
        return;
    }
    
    const key = e.key;

    // Alphanumeric + dash entry for recipient account number
    if (currentScreen === "transfer" && transferActiveField === "recipient") {
        if (key.length === 1 && /[a-zA-Z0-9\-]/.test(key)) {
            if (transferRecipient.length < 12) {
                // If it is initial text, clear it first
                if (transferRecipient === "Enter Number") {
                    transferRecipient = "";
                }
                transferRecipient += key.toUpperCase();
                updateTransferFieldDisplays();
            }
            return;
        }
    }
    
    if (key >= "0" && key <= "9") {
        handleKeypadNumber(key);
    } else if (key === "Enter") {
        handleKeypadEnter();
    } else if (key === "Escape") {
        handleKeypadCancel();
    } else if (key === "Backspace" || key === "Delete") {
        handleKeypadClear();
    }
});
