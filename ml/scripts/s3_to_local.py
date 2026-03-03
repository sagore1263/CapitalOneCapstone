import os
from pathlib import Path
import boto3

# -------- Config via env --------
BUCKET = os.environ["BUCKET"]                 #  fraud-transaction
PREFIX = os.environ.get("PREFIX", "incoming/")  #  incoming/
LOCAL_DIR = Path(os.environ.get("LOCAL_DIR", "ml/data/raw"))
CHECKPOINT_FILE = Path(os.environ.get("CHECKPOINT_FILE", "ml/state/s3_checkpoint.txt"))
MAX_KEYS_PER_RUN = int(os.environ.get("MAX_KEYS_PER_RUN", "500"))  # safety cap


s3 = boto3.client("s3")


def load_checkpoint() -> str:
    try:
        return CHECKPOINT_FILE.read_text().strip()
    except FileNotFoundError:
        return ""


def save_checkpoint(marker: str) -> None:
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_FILE.write_text(marker)


def download_new_objects() -> int:
    """
    Downloads only new S3 objects whose Key is > checkpoint marker.
    Assumes keys are roughly time-ordered (timestamp prefix is ideal).
    Does NOT delete from S3.
    """
    marker = load_checkpoint()

    LOCAL_DIR.mkdir(parents=True, exist_ok=True)

    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=BUCKET, Prefix=PREFIX)

    # Collect keys (small/medium volumes). If huge, we can stream-sort.
    keys = []
    for page in pages:
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith("/"):
                continue
            if key > marker:
                keys.append(key)

    if not keys:
        print("No new objects found.")
        return 0

    keys.sort()  # oldest -> newest if your keys are timestamp-first

    downloaded = 0
    new_marker = marker

    for key in keys[:MAX_KEYS_PER_RUN]:
        # Preserve key structure locally: incoming/abc.json -> ml/data/raw/incoming/abc.json
        local_path = LOCAL_DIR / key
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Skip if already downloaded (idempotent)
        if local_path.exists():
            new_marker = key
            continue

        s3.download_file(BUCKET, key, str(local_path))
        downloaded += 1
        new_marker = key
        print(f"Downloaded: s3://{BUCKET}/{key} -> {local_path}")

    save_checkpoint(new_marker)
    print(f"Done. Downloaded {downloaded} file(s). Checkpoint = {new_marker}")
    return downloaded


if __name__ == "__main__":
    download_new_objects()