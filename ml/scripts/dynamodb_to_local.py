import os
import json
from decimal import Decimal
from pathlib import Path
import boto3
from boto3.dynamodb.conditions import Attr

# -------- Config --------
TABLE = os.environ["DDB_TABLE"]                 #  user_transactions
REGION = os.environ.get("AWS_REGION", "us-east-1")

OUT_DIR = Path("ml/data/inbox")                 # per-transaction files
CHECKPOINT_FILE = Path("ml/data/.last_seen_created_at")

# Change these to match your schema
CREATED_AT_FIELD = "created_at"                 # e.g. "created_at"
ID_FIELD = "transaction_id"                     # e.g. "transaction_id" (fallback handled)

def convert_value(val):
    """Convert DynamoDB types to JSON-friendly values"""
    if isinstance(val, Decimal):
        # keep ints as int when possible, else float
        if val % 1 == 0:
            return int(val)
        return float(val)
    if isinstance(val, dict):
        return {k: convert_value(v) for k, v in val.items()}
    if isinstance(val, list):
        return [convert_value(v) for v in val]
    return val

def safe_name(s: str) -> str:
    # filename-safe
    return "".join(c for c in s if c.isalnum() or c in ("-", "_", ".", "="))[:200]

def load_checkpoint() -> str | None:
    if CHECKPOINT_FILE.exists():
        return CHECKPOINT_FILE.read_text().strip() or None
    return None

def save_checkpoint(value: str):
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_FILE.write_text(value)

def main():
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(TABLE)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    last_seen = load_checkpoint()
    print(f"Last checkpoint: {last_seen}")

    # If we have a checkpoint, filter to only fetch newer items.
    # NOTE: This still SCANS, but reduces what we process/write locally.
    filter_expr = None
    if last_seen is not None:
        filter_expr = Attr(CREATED_AT_FIELD).gt(last_seen)

    items = []
    last_key = None

    print("Fetching NEW data from DynamoDB (scan)...")

    while True:
        kwargs = {}
        if last_key:
            kwargs["ExclusiveStartKey"] = last_key
        if filter_expr is not None:
            kwargs["FilterExpression"] = filter_expr

        resp = table.scan(**kwargs)
        batch = resp.get("Items", [])
        items.extend(batch)

        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            break

    if not items:
        print("No new items found.")
        return

    # Sort by created_at so checkpoint updates correctly
    items.sort(key=lambda x: x.get(CREATED_AT_FIELD, ""))

    written = 0
    newest_created_at = last_seen

    for item in items:
        created_at = str(item.get(CREATED_AT_FIELD, "unknown"))
        txn_id = str(item.get(ID_FIELD, "")) or str(item.get("id", "")) or "no_id"

        # Convert Decimals, etc.
        out_item = {k: convert_value(v) for k, v in item.items()}

        filename = f"{safe_name(created_at)}__{safe_name(txn_id)}.json"
        out_path = OUT_DIR / filename

        # Don’t overwrite if it already exists (dedupe)
        if out_path.exists():
            continue

        with open(out_path, "w") as f:
            json.dump(out_item, f)

        written += 1
        newest_created_at = created_at  # because sorted

    if newest_created_at and newest_created_at != last_seen:
        save_checkpoint(newest_created_at)

    print(f"Wrote {written} new file(s) to {OUT_DIR}")
    print(f"Updated checkpoint to: {newest_created_at}")

if __name__ == "__main__":
    main()