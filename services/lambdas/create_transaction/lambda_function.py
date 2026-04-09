import json
import uuid
import boto3
from decimal import Decimal

lambda_client = boto3.client("lambda")

FRAUD_LAMBDA_NAME = "fraud-scoring-service"

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("transactions")


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
    enriched_transaction["transactionId"] = str(uuid.uuid4())
    enriched_transaction["user_id"] = user_id

    return enriched_transaction


def invoke_fraud_lambda(transaction):
    fraud_input = {
        key: value
        for key, value in transaction.items()
        if key not in {"transactionId", "user_id"}
    }

    fraud_input = decimal_to_native(fraud_input)

    response = lambda_client.invoke(
        FunctionName=FRAUD_LAMBDA_NAME,
        InvocationType="RequestResponse",
        Payload=json.dumps({
            "transaction": fraud_input
        }).encode("utf-8")
    )

    payload = json.loads(response["Payload"].read())

    if payload.get("statusCode") != 200:
        raise Exception(f"Fraud Lambda failed: {payload}")

    body = payload.get("body", "{}")
    if isinstance(body, str):
        body = json.loads(body)

    return body


def lambda_handler(event, context):
    try:
        user_id = event.get("pathParameters", {}).get("userId")
        body = json.loads(event.get("body", "{}"), parse_float=Decimal)

        transaction = get_transaction_payload(user_id, body)

        # Use this if fraud Lambda is ready for raw transaction input
        #fraud_result = invoke_fraud_lambda(transaction)

        # Temporary fallback if fraud Lambda still expects engineered features:
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

        table.put_item(Item=transaction)

        response_body = decimal_to_native(transaction)

        return {
            "statusCode": 201,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(response_body)
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }