import os
import csv
from decimal import Decimal
from pathlib import Path
import boto3

# -------- Config --------
TABLE = os.environ["DDB_TABLE"]                 # e.g. user_transactions
REGION = os.environ.get("AWS_REGION", "us-east-1")
OUT_DIR = Path("ml/data")
OUT_FILE = OUT_DIR / "transactions.csv"


def convert_value(val):
    """Convert DynamoDB types to CSV-friendly values"""
    if isinstance(val, Decimal):
        return float(val)
    return val


def main():
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(TABLE)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    items = []
    last_key = None

    print("Fetching data from DynamoDB...")

    while True:
        kwargs = {}
        if last_key:
            kwargs["ExclusiveStartKey"] = last_key

        resp = table.scan(**kwargs)
        batch = resp.get("Items", [])
        items.extend(batch)

        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            break

    if not items:
        print("No items found.")
        return

    # Determine CSV columns
    columns = set()
    for item in items:
        columns.update(item.keys())

    columns = sorted(columns)

    print(f"Writing {len(items)} rows to CSV...")

    with open(OUT_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()

        for item in items:
            row = {k: convert_value(v) for k, v in item.items()}
            writer.writerow(row)

    print(f"CSV written to {OUT_FILE}")


if __name__ == "__main__":
    main()