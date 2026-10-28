"""
generate_data.py
Generates realistic e-commerce A/B experiment data tailored to beauty & personal care (Nykaa context).
Author: jay-sanajay (https://github.com/jay-sanajay)
Repository: https://github.com/jay-sanajay/ecommerce-ab-testing-engine

Feature tested: "Complete Your Routine" Bundles vs Control Carousel on Product Display Page (PDP).
Outputs SQLite database (data/nykaa_experiment.db) and CSV exports.
"""

import os
import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def generate_experiment_data(num_users=100000, random_seed=42):
    np.random.seed(random_seed)
    print(f"Generating synthetic experiment dataset for {num_users:,} unique users...")

    # 1. Users table
    user_ids = [f"U_{100000 + i}" for i in range(num_users)]
    
    devices = np.random.choice(["Mobile App", "Mobile Web", "Desktop"], size=num_users, p=[0.68, 0.22, 0.10])
    city_tiers = np.random.choice(["Tier 1", "Tier 2", "Tier 3"], size=num_users, p=[0.45, 0.35, 0.20])
    user_types = np.random.choice(["Returning", "New"], size=num_users, p=[0.58, 0.42])
    primary_categories = np.random.choice(["Skincare", "Makeup", "Haircare", "Fragrance"], size=num_users, p=[0.40, 0.30, 0.18, 0.12])
    
    # 2. Experiment Assignment (50/50 Control vs Treatment)
    # Slight natural binomial variance (e.g. 50.1% vs 49.9%)
    variant_probs = [0.50, 0.50]
    variants = np.random.choice(["Control", "Treatment"], size=num_users, p=variant_probs)
    
    start_date = datetime(2026, 10, 1, 0, 0, 0)
    assigned_times = [start_date + timedelta(seconds=int(np.random.uniform(0, 14 * 86400))) for _ in range(num_users)]
    
    users_df = pd.DataFrame({
        "user_id": user_ids,
        "variant": variants,
        "assigned_timestamp": assigned_times,
        "device": devices,
        "city_tier": city_tiers,
        "user_type": user_types,
        "primary_category": primary_categories
    })

    # 3. Funnel Events & Orders Simulation
    funnel_records = []
    order_records = []
    order_counter = 1

    for idx, row in users_df.iterrows():
        uid = row["user_id"]
        variant = row["variant"]
        t0 = row["assigned_timestamp"]
        cat = row["primary_category"]
        device = row["device"]
        is_returning = (row["user_type"] == "Returning")

        # Step 0: PDP View (All assigned users viewed PDP)
        funnel_records.append({
            "event_id": f"E_{len(funnel_records)+1}",
            "user_id": uid,
            "event_type": "pdp_view",
            "timestamp": t0
        })

        # Base conversion rates
        # Control: Cart = ~13%, Checkout = ~55% of cart, Purchase = ~46% of checkout => ~3.3%
        # Treatment: Cart = ~15.2%, Checkout = ~57% of cart, Purchase = ~48% of checkout => ~4.15%
        p_cart_base = 0.128 if variant == "Control" else 0.151
        p_checkout_base = 0.540 if variant == "Control" else 0.570
        p_purchase_base = 0.465 if variant == "Control" else 0.485

        # Category/Device adjustments
        if device == "Mobile App":
            p_cart_base *= 1.15
        elif device == "Mobile Web":
            p_cart_base *= 0.85

        if is_returning:
            p_cart_base *= 1.10

        # Simulate Cart
        did_cart = np.random.rand() < p_cart_base
        if did_cart:
            t1 = t0 + timedelta(seconds=int(np.random.exponential(120)))
            funnel_records.append({
                "event_id": f"E_{len(funnel_records)+1}",
                "user_id": uid,
                "event_type": "add_to_cart",
                "timestamp": t1
            })

            # Simulate Checkout
            did_checkout = np.random.rand() < p_checkout_base
            if did_checkout:
                t2 = t1 + timedelta(seconds=int(np.random.exponential(180)))
                funnel_records.append({
                    "event_id": f"E_{len(funnel_records)+1}",
                    "user_id": uid,
                    "event_type": "checkout_started",
                    "timestamp": t2
                })

                # Simulate Purchase
                did_purchase = np.random.rand() < p_purchase_base
                if did_purchase:
                    t3 = t2 + timedelta(seconds=int(np.random.exponential(90)))
                    funnel_records.append({
                        "event_id": f"E_{len(funnel_records)+1}",
                        "user_id": uid,
                        "event_type": "purchase",
                        "timestamp": t3
                    })

                    # Order Value calculation:
                    # Treatment bundled feature increases basket size (AOV)
                    # Base lognormal distribution
                    if variant == "Control":
                        mu = 7.15  # exp(7.15) ~ ₹1274
                        sigma = 0.50
                    else:
                        mu = 7.32  # exp(7.32) ~ ₹1510 (+18% basket value due to routine bundles)
                        sigma = 0.52

                    base_value = float(np.random.lognormal(mean=mu, sigma=sigma))

                    # 0.4% chance of extreme bulk order outlier to test winsorization
                    if np.random.rand() < 0.004:
                        base_value = float(np.random.uniform(18000, 45000))

                    discount_pct = float(np.random.choice([0.0, 0.10, 0.15, 0.20], p=[0.40, 0.30, 0.20, 0.10]))
                    final_value = round(base_value * (1 - discount_pct), 2)

                    order_records.append({
                        "order_id": f"ORD_{order_counter:06d}",
                        "user_id": uid,
                        "variant": variant,
                        "order_timestamp": t3,
                        "order_value": final_value,
                        "category": cat,
                        "discount_pct": discount_pct
                    })
                    order_counter += 1

    funnel_df = pd.DataFrame(funnel_records)
    orders_df = pd.DataFrame(order_records)

    print(f"Data Generation Complete:")
    print(f" - Users: {len(users_df):,}")
    print(f" - Funnel Events: {len(funnel_df):,}")
    print(f" - Orders: {len(orders_df):,}")

    # Save to SQLite and CSV
    os.makedirs("data", exist_ok=True)
    db_path = os.path.join("data", "nykaa_experiment.db")
    conn = sqlite3.connect(db_path)
    
    users_df.to_sql("users", conn, if_exists="replace", index=False)
    funnel_df.to_sql("funnel_events", conn, if_exists="replace", index=False)
    orders_df.to_sql("orders", conn, if_exists="replace", index=False)
    conn.close()

    users_df.to_csv("data/users.csv", index=False)
    funnel_df.to_csv("data/funnel_events.csv", index=False)
    orders_df.to_csv("data/orders.csv", index=False)

    print(f"Database saved to {db_path} and CSVs generated in data/ folder.")
    return users_df, funnel_df, orders_df

if __name__ == "__main__":
    generate_experiment_data()
