import pandas as pd
import boto3
from decimal import Decimal

TABLE_NAME = "transactions"
REGION = "us-east-2"
CSV_FILE = "fraudTrain.csv"

dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE_NAME)

def to_iso(dt_str):
    return pd.to_datetime(dt_str).strftime("%Y-%m-%dT%H:%M:%SZ")

def row_to_item(row):
    return {
        "userId": str(row["cc_num"]),
        "transactionDate": f"{to_iso(row['trans_date_trans_time'])}#{row['trans_num']}",
        "recordIndex": int(row["Unnamed: 0"]) if "Unnamed: 0" in row else int(row["index"]),
        "transactionId": str(row["trans_num"]),
        "merchant": str(row["merchant"]),
        "category": str(row["category"]),
        "amount": Decimal(str(row["amt"])),
        "firstName": str(row["first"]),
        "lastName": str(row["last"]),
        "gender": str(row["gender"]),
        "street": str(row["street"]),
        "city": str(row["city"]),
        "state": str(row["state"]),
        "zipCode": int(row["zip"]),
        "customerLatitude": Decimal(str(row["lat"])),
        "customerLongitude": Decimal(str(row["long"])),
        "cityPopulation": int(row["city_pop"]),
        "job": str(row["job"]),
        "dateOfBirth": str(row["dob"]),
        "unixTime": int(row["unix_time"]),
        "merchantLatitude": Decimal(str(row["merch_lat"])),
        "merchantLongitude": Decimal(str(row["merch_long"])),
        "isFraud": int(row["is_fraud"])
    }

def load_csv():
    total = 0

    for chunk in pd.read_csv(CSV_FILE, chunksize=500):
        with table.batch_writer() as batch:
            for _, row in chunk.iterrows():
                batch.put_item(Item=row_to_item(row))
                total += 1

                if total % 1000 == 0:
                    print(f"Loaded {total} items...")

    print(f"Done. Loaded {total} items into {TABLE_NAME}.")

if __name__ == "__main__":
    load_csv()