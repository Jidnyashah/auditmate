"""
generate_trades.py
------------------
Generates ~500 rows of realistic synthetic trade data with ~10% injected anomalies using Indian Rupees (₹) and Indian instruments.
Run once: python data/generate_trades.py
"""

import pandas as pd
import numpy as np
from faker import Faker
from pathlib import Path
import random

fake = Faker()
np.random.seed(42)
random.seed(42)

# ── Config ────────────────────────────────────────────────────
N_NORMAL = 450
N_ANOMALY = 50
OUTPUT_PATH = Path(__file__).parent / "synthetic_trades.csv"

DESKS = ["FX", "Equities", "Rates", "Credit", "Commodities"]
INSTRUMENTS = {
    "FX":          ["USD/INR", "EUR/INR", "GBP/INR", "JPY/INR"],
    "Equities":    ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"],
    "Rates":       ["IN10Y", "IN2Y", "IN91D", "MIBOR"],
    "Credit":      ["SBI_BOND", "HDFC_BOND", "RELIANCE_BOND"],
    "Commodities": ["MCX_GOLD", "MCX_SILVER", "MCX_CRUDE", "MCX_COPPER"],
}
COUNTERPARTIES = [f"CP_{i:03d}" for i in range(1, 21)]
VENUES = ["NSE", "BSE", "MCX", "NDS-OM", "OTC", "MSEI"]
STATUSES = ["Settled", "Settled", "Settled", "Pending", "Cancelled"]
TRADERS = [f"T{i:03d}" for i in range(1, 31)]

# Price ranges in INR
PRICE_RANGES = {
    "USD/INR": (82.5, 84.5), "EUR/INR": (89.0, 92.5), "GBP/INR": (104.0, 108.5),
    "JPY/INR": (0.52, 0.58), "RELIANCE": (2300, 3100), "TCS": (3400, 4200),
    "INFY": (1400, 1700), "HDFCBANK": (1400, 1700), "ICICIBANK": (950, 1150),
    "IN10Y": (98.5, 102.5), "IN2Y": (99.0, 101.5), "IN91D": (99.2, 100.2),
    "MIBOR": (6.5, 7.8), "SBI_BOND": (995, 1015), "HDFC_BOND": (990, 1020),
    "RELIANCE_BOND": (995, 1025), "MCX_GOLD": (62000, 75000), "MCX_SILVER": (71000, 85000),
    "MCX_CRUDE": (5500, 7200), "MCX_COPPER": (680, 820),
}


def make_trade_id():
    return f"TRD-{fake.bothify('????-########').upper()}"


def normal_trade(idx: int) -> dict:
    desk = random.choice(DESKS)
    instrument = random.choice(INSTRUMENTS[desk])
    lo, hi = PRICE_RANGES.get(instrument, (100, 200))
    price = round(np.random.uniform(lo, hi), 4)
    quantity = int(np.random.lognormal(mean=6.5, sigma=0.8))   # ~800 avg lot
    notional = round(price * quantity, 2)
    
    # Normal hours are 09:00 - 17:00 IST
    ts = fake.date_time_between(
        start_date="-90d", end_date="now"
    ).replace(
        hour=random.randint(9, 16),
        minute=random.randint(0, 59),
        second=random.randint(0, 59),
    )
    return {
        "trade_id":     make_trade_id(),
        "timestamp":    ts,
        "trader_id":    random.choice(TRADERS),
        "desk":         desk,
        "instrument":   instrument,
        "quantity":     quantity,
        "price":        price,
        "notional":     notional,
        "counterparty": random.choice(COUNTERPARTIES),
        "venue":        random.choice(VENUES),
        "status":       random.choices(STATUSES, weights=[6,6,6,1,1])[0],
        "anomaly_type": None,
        "is_flagged":   False,
    }


def inject_anomalies(trades: list[dict]) -> list[dict]:
    anomaly_pool = []

    # 1. Volume spike (10 trades, 8–12x normal quantity)
    for _ in range(10):
        t = normal_trade(-1)
        t["quantity"] = int(t["quantity"] * random.uniform(8, 12))
        t["notional"] = round(t["price"] * t["quantity"], 2)
        t["anomaly_type"] = "volume_spike"
        t["is_flagged"] = True
        anomaly_pool.append(t)

    # 2. Off-hours trades (10 trades, between 23:00–04:00 IST)
    for _ in range(10):
        t = normal_trade(-1)
        t["timestamp"] = t["timestamp"].replace(hour=random.choice([23, 0, 1, 2, 3, 4]))
        t["anomaly_type"] = "off_hours"
        t["is_flagged"] = True
        anomaly_pool.append(t)

    # 3. Price outliers (10 trades, 5-8x normal price)
    for _ in range(10):
        t = normal_trade(-1)
        t["price"] = round(t["price"] * random.uniform(5, 8), 4)
        t["notional"] = round(t["price"] * t["quantity"], 2)
        t["anomaly_type"] = "price_outlier"
        t["is_flagged"] = True
        anomaly_pool.append(t)

    # 4. Duplicate IDs (5 pairs = 10 trades)
    for _ in range(5):
        t1 = normal_trade(-1)
        t2 = t1.copy()
        t2["timestamp"] = t1["timestamp"] + pandas_time_offset()
        # Ensure duplicate ID but different properties
        t2["quantity"] = int(t1["quantity"] * 1.1)
        t2["notional"] = round(t2["price"] * t2["quantity"], 2)
        t1["anomaly_type"] = "duplicate_id"
        t1["is_flagged"] = True
        t2["anomaly_type"] = "duplicate_id"
        t2["is_flagged"] = True
        anomaly_pool.append(t1)
        anomaly_pool.append(t2)

    # 5. Missing fields (10 trades)
    for _ in range(10):
        t = normal_trade(-1)
        missing = random.choice(["trader_id", "venue", "counterparty"])
        t[missing] = np.nan
        t["anomaly_type"] = "missing_field"
        t["is_flagged"] = True
        anomaly_pool.append(t)

    # 6. Minor deviation (Low severity) - 10 trades
    for _ in range(10):
        t = normal_trade(-1)
        t["anomaly_type"] = "minor_deviation"
        t["is_flagged"] = True
        anomaly_pool.append(t)

    return anomaly_pool


def pandas_time_offset():
    return timedelta(seconds=random.randint(10, 300))


from datetime import timedelta
import pandas as pd

if __name__ == "__main__":
    trades = [normal_trade(i) for i in range(N_NORMAL)]
    anomalies = inject_anomalies(trades)
    
    all_trades = trades + anomalies
    df = pd.DataFrame(all_trades)
    df = df.sort_values(by="timestamp").reset_index(drop=True)
    
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    
    print(f"[OK] Generated {len(df)} trades at: {OUTPUT_PATH}")
    print(f"[OK] Flagged anomalies: {len(df[df['is_flagged']])}")
