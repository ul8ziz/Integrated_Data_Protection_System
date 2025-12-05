# 🎭 Demo & Testing Scripts

This folder contains scripts to simulate user behavior and test the DLP system capabilities.

## 🚀 Quick Demo Scenarios

### 1. Full System Health Check
Run this first to ensure everything is working.
```bash
python test_full_scan.py
```

### 2. The "Insider Threat" Story (Interactive Demo)
Follow these steps to demonstrate a data leak prevention scenario:

*   **Step 1: Initial Detection**
    *   `python scenario_step1.py`
    *   *Action:* User analyzes text with a phone number.
    *   *Result:* Detected but ALLOWED (Alert only).

*   **Step 2: Policy Enforcement**
    *   `python scenario_step2.py`
    *   *Action:* Admin creates a "Strict Block" policy for phone numbers.
    *   *Result:* Policy created successfully.

*   **Step 3: Prevention**
    *   `python scenario_step3.py`
    *   *Action:* User tries the same text again.
    *   *Result:* **BLOCKED** immediately.

*   **Step 4: Audit Trail**
    *   `python scenario_step4_fixed.py`
    *   *Action:* Admin checks logs.
    *   *Result:* Shows the blocked incident in detail.

### 3. Email Interception
Simulate an email server asking the DLP system for permission.
```bash
python scenario_email.py
```

### 4. Real Email Test (Advanced)
Connects to real Gmail SMTP to send emails (requires config).
```bash
python real_email_sender.py
```

