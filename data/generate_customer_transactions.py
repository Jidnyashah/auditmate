import pandas as pd
import numpy as np
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# Set random seed for reproducibility
np.random.seed(42)
random.seed(42)

# High-risk TF (Terrorist Financing) countries based on FATF lists
HIGH_RISK_TF_COUNTRIES = ["Iran", "North Korea", "Syria", "Yemen", "Myanmar", "Somalia", "Sudan", "South Sudan"]
NORMAL_COUNTRIES = ["India", "United States", "United Kingdom", "Singapore", "UAE", "Germany", "Japan", "Switzerland", "Australia", "Canada"]

# Indian customer list & risk profiles
CUSTOMERS = [
    {"cust_id": f"CUST{i:03d}", "name": name, "risk_profile": risk}
    for i, (name, risk) in enumerate([
        ("Rohan Sharma", "Low"), ("Priya Patel", "Low"), ("Vikram Malhotra", "High"),
        ("Aarav Mehta", "Low"), ("Deepa Krishnan", "Medium"), ("Amit Verma", "Low"),
        ("Sanjay Singhania", "High"), ("Jaspreet Singh", "Medium"), ("Karan Johar", "Low"),
        ("Anjali Gupta", "Low"), ("Amrita Sen", "High"), ("Ravi Shastri", "Low")
    ])
]

# Generate multiple accounts per customer
ACCOUNTS = []
account_types = ["Checking", "Savings", "Business"]
for cust in CUSTOMERS:
    num_accounts = random.randint(1, 3)
    for j in range(num_accounts):
        ACCOUNTS.append({
            "account_id": f"ACC{1000 + len(ACCOUNTS):d}",
            "customer_id": cust["cust_id"],
            "customer_name": cust["name"],
            "customer_risk_profile": cust["risk_profile"],
            "account_type": random.choice(account_types)
        })

# Generate transactions over past 3 months (90 days) in INR (Rupees)
start_date = datetime.now() - timedelta(days=90)
end_date = datetime.now()

transactions = []
num_transactions = 1200

for _ in range(num_transactions):
    acc = random.choice(ACCOUNTS)
    
    random_days = random.randint(0, 90)
    random_seconds = random.randint(0, 86400)
    ts = start_date + timedelta(days=random_days, seconds=random_seconds)
    
    tx_type = random.choice(["Deposit", "Withdrawal", "Transfer", "Wire"])
    
    is_tf_country = False
    if acc["customer_risk_profile"] == "High":
        is_tf_country = random.random() < 0.15
    elif acc["customer_risk_profile"] == "Medium":
        is_tf_country = random.random() < 0.05
    else:
        is_tf_country = random.random() < 0.005
        
    country = random.choice(HIGH_RISK_TF_COUNTRIES) if is_tf_country else random.choice(NORMAL_COUNTRIES)
    
    # Amount generation in INR (Scale roughly 80x larger than USD defaults)
    if tx_type == "Wire":
        amount = round(np.random.exponential(scale=1200000) + 10000, 2)  # ~12 Lakhs avg
    elif acc["account_type"] == "Business":
        amount = round(np.random.exponential(scale=640000) + 5000, 2)    # ~6.4 Lakhs avg
    else:
        amount = round(np.random.exponential(scale=96000) + 500, 2)      # ~96k avg
        
    # Cap maximum amount to keep it realistic but inject a few large outliers
    if random.random() < 0.01:
        amount = round(random.uniform(4000000, 20000000), 2)  # ₹40 Lakhs to ₹2 Crore
        
    # Counterparty details
    if tx_type in ["Transfer", "Wire"]:
        cp_name = random.choice([
            "Global Trading Ltd", "Nexus Logistics", "Vertex Clearing", "Direct Express",
            "S.A. Trade Corp", "Capital Horizons", "M. K. Holdings", "Hassan & Co Financials",
            "Pyongyang Export", "Damascus Trading", "Sana Wires", "Tehran General Commerce"
        ])
    else:
        cp_name = "Self"
        country = "India"  # local transaction
        
    status = "Settled"
    if random.random() < 0.02:
        status = "Declined"
    elif random.random() < 0.03:
        status = "Pending"
        
    channel = "Online Banking"
    if tx_type == "Wire":
        channel = "Wire Transfer"
    elif tx_type == "Withdrawal" and amount < 40000:
        channel = random.choice(["ATM", "Branch"])
    else:
        channel = random.choice(["Online Banking", "Mobile App"])

    transactions.append({
        "transaction_id": f"TXN{uuid.uuid4().hex[:8].upper()}",
        "customer_id": acc["customer_id"],
        "customer_name": acc["customer_name"],
        "customer_risk_profile": acc["customer_risk_profile"],
        "account_id": acc["account_id"],
        "account_type": acc["account_type"],
        "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "amount_usd": amount,  # mapped to notional in memory
        "quantity": 1,
        "transaction_type": tx_type,
        "counterparty_name": cp_name,
        "counterparty_country": country,
        "status": status,
        "channel": channel
    })

# Injected targeted TF / PMLA anomalies for verification
# Scenario A: Structuring (repeated small transfers to TF country under AML alert threshold of ₹1,000,000 / 10 Lakhs)
structuring_customer = next(acc for acc in ACCOUNTS if acc["customer_name"] == "Sanjay Singhania")
structuring_start_time = start_date + timedelta(days=45)
for i in range(5):
    transactions.append({
        "transaction_id": f"TXNSTR{i:03d}",
        "customer_id": structuring_customer["customer_id"],
        "customer_name": structuring_customer["customer_name"],
        "customer_risk_profile": structuring_customer["customer_risk_profile"],
        "account_id": structuring_customer["account_id"],
        "account_type": structuring_customer["account_type"],
        "timestamp": (structuring_start_time + timedelta(hours=i*2)).strftime("%Y-%m-%d %H:%M:%S"),
        "amount_usd": round(random.uniform(900000, 980000), 2),  # Structuring just below ₹10 Lakhs threshold
        "quantity": 1,
        "transaction_type": "Wire",
        "counterparty_name": "Tehran General Commerce",
        "counterparty_country": "Iran",
        "status": "Settled",
        "channel": "Wire Transfer"
    })

# Scenario B: Single Massive Wire to high-risk TF Country
large_wire_customer = next(acc for acc in ACCOUNTS if acc["customer_name"] == "Amrita Sen")
transactions.append({
    "transaction_id": f"TXNLW999",
    "customer_id": large_wire_customer["customer_id"],
    "customer_name": large_wire_customer["customer_name"],
    "customer_risk_profile": large_wire_customer["customer_risk_profile"],
    "account_id": large_wire_customer["account_id"],
    "account_type": large_wire_customer["account_type"],
    "timestamp": (start_date + timedelta(days=60)).strftime("%Y-%m-%d %H:%M:%S"),
    "amount_usd": 12500000.00,  # ₹1.25 Crore
    "quantity": 1,
    "transaction_type": "Wire",
    "counterparty_name": "Syrian Trust Logistics",
    "counterparty_country": "Syria",
    "status": "Settled",
    "channel": "Wire Transfer"
})

# Scenario C: Volume Spikes (Quantity outliers)
volume_customer = next(acc for acc in ACCOUNTS if acc["customer_name"] == "Rohan Sharma")
for i in range(2):
    transactions.append({
        "transaction_id": f"TXNVOL{i:03d}",
        "customer_id": volume_customer["customer_id"],
        "customer_name": volume_customer["customer_name"],
        "customer_risk_profile": volume_customer["customer_risk_profile"],
        "account_id": volume_customer["account_id"],
        "account_type": volume_customer["account_type"],
        "timestamp": (start_date + timedelta(days=30 + i)).strftime("%Y-%m-%d %H:%M:%S"),
        "amount_usd": 100000.00,
        "quantity": 25,  # Trigger volume spike anomaly
        "transaction_type": "Transfer",
        "counterparty_name": "Global Trading Ltd",
        "counterparty_country": "India",
        "status": "Settled",
        "channel": "Online Banking"
    })

# Scenario D: Duplicate IDs (Critical Severity anomalies)
duplicate_customer = next(acc for acc in ACCOUNTS if acc["customer_name"] == "Priya Patel")
for i in range(2):
    dup_id = f"TXNDUP{i:03d}"
    t_base = start_date + timedelta(days=20 + i)
    # Record 1
    transactions.append({
        "transaction_id": dup_id,
        "customer_id": duplicate_customer["customer_id"],
        "customer_name": duplicate_customer["customer_name"],
        "customer_risk_profile": duplicate_customer["customer_risk_profile"],
        "account_id": duplicate_customer["account_id"],
        "account_type": duplicate_customer["account_type"],
        "timestamp": t_base.strftime("%Y-%m-%d %H:%M:%S"),
        "amount_usd": 50000.00,
        "quantity": 1,
        "transaction_type": "Transfer",
        "counterparty_name": "Nexus Logistics",
        "counterparty_country": "India",
        "status": "Settled",
        "channel": "Online Banking"
    })
    # Record 2 (Duplicate ID)
    transactions.append({
        "transaction_id": dup_id,
        "customer_id": duplicate_customer["customer_id"],
        "customer_name": duplicate_customer["customer_name"],
        "customer_risk_profile": duplicate_customer["customer_risk_profile"],
        "account_id": duplicate_customer["account_id"],
        "account_type": duplicate_customer["account_type"],
        "timestamp": (t_base + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S"),
        "amount_usd": 55000.00,  # slightly different amount
        "quantity": 1,
        "transaction_type": "Transfer",
        "counterparty_name": "Nexus Logistics",
        "counterparty_country": "India",
        "status": "Settled",
        "channel": "Online Banking"
    })

# Scenario E: Missing Fields (High Severity anomalies)
missing_customer = next(acc for acc in ACCOUNTS if acc["customer_name"] == "Vikram Malhotra")
for i in range(2):
    transactions.append({
        "transaction_id": f"TXNMIS{i:03d}",
        "customer_id": np.nan if i == 0 else missing_customer["customer_id"],
        "customer_name": missing_customer["customer_name"],
        "customer_risk_profile": missing_customer["customer_risk_profile"],
        "account_id": missing_customer["account_id"],
        "account_type": missing_customer["account_type"],
        "timestamp": (start_date + timedelta(days=10 + i)).strftime("%Y-%m-%d %H:%M:%S"),
        "amount_usd": 80000.00,
        "quantity": 1,
        "transaction_type": "Transfer",
        "counterparty_name": np.nan if i == 1 else "Vertex Clearing",
        "counterparty_country": "India",
        "status": "Settled",
        "channel": "Online Banking"
    })

# Save to CSV
df_tx = pd.DataFrame(transactions)
df_tx = df_tx.sort_values(by="timestamp").reset_index(drop=True)

out_dir = Path(__file__).parent.parent / "data"
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / "customer_transactions.csv"
df_tx.to_csv(out_path, index=False)

print(f"[OK] Generated {len(df_tx)} transactions at: {out_path}")
print(f"[OK] High-risk TF transactions: {len(df_tx[df_tx['counterparty_country'].isin(HIGH_RISK_TF_COUNTRIES)])}")
