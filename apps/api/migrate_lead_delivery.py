"""
Run this ONCE to create the lead_deliveries table and add new columns to plumbers.
Save as: apps/api/migrate_lead_delivery.py
Run with: python migrate_lead_delivery.py
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine, Base
from sqlalchemy import text

def run_migration():
    print("Running lead delivery migration...")

    with engine.connect() as conn:
        # Add new columns to plumbers table if they don't exist
        columns = [
            "ALTER TABLE plumbers ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(255)",
            "ALTER TABLE plumbers ADD COLUMN IF NOT EXISTS subscription_plan VARCHAR(50)",
            "ALTER TABLE plumbers ADD COLUMN IF NOT EXISTS subscription_active INTEGER DEFAULT 0",
            "ALTER TABLE plumbers ADD COLUMN IF NOT EXISTS subscription_started_at TIMESTAMP",
            "ALTER TABLE plumbers ADD COLUMN IF NOT EXISTS leads_delivered_count INTEGER DEFAULT 0",
        ]

        for col in columns:
            try:
                conn.execute(text(col))
                print(f"OK: {col[:60]}...")
            except Exception as e:
                print(f"Skip (already exists): {e}")

        # Create lead_deliveries table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS lead_deliveries (
                id SERIAL PRIMARY KEY,
                plumber_id INTEGER NOT NULL REFERENCES plumbers(id) ON DELETE CASCADE,
                prospect_id INTEGER NOT NULL REFERENCES demand_prospects(id) ON DELETE CASCADE,
                plan VARCHAR(50),
                delivered_at TIMESTAMP DEFAULT NOW(),
                status VARCHAR(50) DEFAULT 'delivered',
                opened INTEGER DEFAULT 0,
                contacted INTEGER DEFAULT 0,
                converted INTEGER DEFAULT 0
            )
        """))
        print("OK: lead_deliveries table created")

        conn.commit()

    print("Migration complete!")

if __name__ == "__main__":
    run_migration()
