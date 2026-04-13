import json
import uuid
import boto3
import os
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from botocore.exceptions import ClientError
lambda_client = boto3.client("lambda")
ALERT_LAMBDA_NAME = os.environ["ALERT_LAMBDA_NAME"]
lambda_client = boto3.client("lambda")
dynamodb = boto3.resource("dynamodb")

transactions_table = dynamodb.Table(os.environ["TRANSACTIONS_TABLE"])
users_table = dynamodb.Table(os.environ["USERS_TABLE"])

FRAUD_LAMBDA_NAME = os.environ.get("FRAUD_LAMBDA_NAME")


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body)
    }


def convert_floats_to_decimal(obj):
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_floats_to_decimal(v) for v in obj]
    return obj


def decimal_to_native(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: decimal_to_native(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [decimal_to_native(v) for v in obj]
    return obj


def parse_iso_timestamp(value):
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except Exception:
        raise ValueError("transactionTimestamp must be a valid ISO-8601 timestamp")


def format_iso_timestamp(dt):
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def get_transaction_payload(user_id, body):
    transaction = body.get("transaction", body)

    if not isinstance(transaction, dict):
        raise ValueError("Request body must contain a transaction object")

    required_keys = [
        "cardNumber",
        "transactionTimestamp",
        "amount",
        "category",
        "city",
        "cityPopulation",
        "customerLatitude",
        "customerLongitude",
        "dateOfBirth",
        "firstName",
        "gender",
        "isFraud",
        "job",
        "lastName",
        "merchant",
        "merchantLatitude",
        "merchantLongitude",
        "state",
        "street",
        "unixTime",
        "zipCode"
    ]

    missing = [key for key in required_keys if key not in transaction]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

    enriched_transaction = dict(transaction)
    enriched_transaction["cardNumber"] = str(enriched_transaction["cardNumber"])
    enriched_transaction["transactionTimestamp"] = str(enriched_transaction["transactionTimestamp"])
    enriched_transaction["transactionId"] = str(uuid.uuid4())

    if user_id:
        enriched_transaction["user_id"] = str(user_id)

    return enriched_transaction


def user_exists(card_number):
    result = users_table.get_item(Key={"cardNumber": str(card_number)})
    return "Item" in result


def invoke_fraud_lambda(transaction):
    if not FRAUD_LAMBDA_NAME:
        raise Exception("FRAUD_LAMBDA_NAME environment variable is not set")

    fraud_input = {
        key: value
        for key, value in transaction.items()
        if key not in {"transactionId", "user_id"}
    }

    fraud_input = decimal_to_native(fraud_input)

    lambda_response = lambda_client.invoke(
        FunctionName=FRAUD_LAMBDA_NAME,
        InvocationType="RequestResponse",
        Payload=json.dumps({
            "transaction": fraud_input
        }).encode("utf-8")
    )

    payload = json.loads(lambda_response["Payload"].read())

    if payload.get("statusCode") != 200:
        raise Exception(f"Fraud Lambda failed: {payload}")

    body = payload.get("body", "{}")
    if isinstance(body, str):
        body = json.loads(body)

    return body


def put_transaction_with_unique_timestamp(transaction, max_attempts=5):
    original_dt = parse_iso_timestamp(transaction["transactionTimestamp"])

    for offset_ms in range(max_attempts):
        candidate = dict(transaction)
        adjusted_dt = original_dt + timedelta(milliseconds=offset_ms)
        candidate["transactionTimestamp"] = format_iso_timestamp(adjusted_dt)

        try:
            transactions_table.put_item(
                Item=candidate,
                ConditionExpression="attribute_not_exists(cardNumber) AND attribute_not_exists(transactionTimestamp)"
            )
            return candidate
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "ConditionalCheckFailedException":
                continue
            raise

    raise ValueError(
        "Could not create a unique transactionTimestamp for this cardNumber after multiple attempts"
    )

def invoke_alert_lambda(transaction):
    payload = {
        "transactionId": transaction["transactionId"],
        "cardNumber": transaction["cardNumber"],
        "transactionTimestamp": transaction["transactionTimestamp"],
        "merchant": transaction["merchant"],
        "amount": float(transaction["amount"]),
        "fraudScore": float(transaction["fraud_score"]),
    }

    lambda_client.invoke(
        FunctionName=ALERT_LAMBDA_NAME,
        InvocationType="Event",
        Payload=json.dumps(payload).encode("utf-8")
    )

def lambda_handler(event, context):
    try:
        path_params = event.get("pathParameters") or {}
        user_id = path_params.get("userId")

        body = json.loads(event.get("body", "{}"), parse_float=Decimal)
        transaction = get_transaction_payload(user_id, body)

        if not user_exists(transaction["cardNumber"]):
            return response(404, {
                "error": "No user found for the provided cardNumber"
            })

        try:
            fraud_result = invoke_fraud_lambda(transaction)
        except Exception:
            fraud_result = {
                "prediction_probability": 0.0841,
                "fraud_score": 0.88
            }

        transaction["prediction_probability"] = Decimal(
            str(fraud_result.get("prediction_probability", 0))
        )
        transaction["fraud_score"] = Decimal(
            str(fraud_result.get("fraud_score", 0))
        )

        transaction = convert_floats_to_decimal(transaction)
        saved_transaction = put_transaction_with_unique_timestamp(transaction)
        print("About to invoke alert lambda")
        invoke_alert_lambda(decimal_to_native(saved_transaction))
        print("Alert lambda invoked")

        return response(201, decimal_to_native(saved_transaction))

    except ValueError as e:
        return response(400, {"error": str(e)})

    except ClientError as e:
        return response(500, {
            "error": "Failed to create transaction",
            "details": str(e)
        })

    except Exception as e:
        return response(500, {"error": str(e)})