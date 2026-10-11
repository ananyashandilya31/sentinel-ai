"""
Seed Threat Intelligence Database CLI Script.
Usage:
    python data/seed_threat_intel.py [--overwrite]
"""
import sys
import argparse
from pathlib import Path

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root_dir))

from backend.database import SessionLocal, engine, Base
from backend.models.threat_intel import IPReputation
from backend.services.threat_intel_service import seed_threat_intel_database


def main():
    parser = argparse.ArgumentParser(description="Seed threat intelligence database with known IPs")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing threat intelligence records")
    args = parser.parse_args()

    print("[*] Ensuring database tables exist...")
    Base.metadata.create_all(bind=engine)

    print(f"[*] Seeding IP reputation data (overwrite={args.overwrite})...")
    session = SessionLocal()
    try:
        count = seed_threat_intel_database(session, overwrite=args.overwrite)
        total = session.query(IPReputation).count()
        print(f"[+] Successfully seeded/updated {count} records. Total IP reputations in DB: {total}")
    except Exception as exc:
        print(f"[-] Error seeding database: {exc}")
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
