import json
import uuid
import boto3
from datetime import datetime, timezone

lambda_client = boto3.client("lambda")

FRAUD_LAMBDA_NAME = "fraud-scoring-service"


def get_feature_payload(user_id, body):
    now_utc = datetime.now(timezone.utc)

    return {
        "transactionId": str(uuid.uuid4()),
        "user_id": user_id,
        "amount": float(body.get("amount", 0.0)),
        "hour": int(body.get("hour", now_utc.hour)),
        "is_international": int(body.get("is_international", 0)),
        "merchant_risk": float(body.get("merchant_risk", 0.0)),
        "txn_count_24h": float(body.get("txn_count_24h", 0.0)),
    }


def invoke_fraud_lambda(transaction):
    response = lambda_client.invoke(
        FunctionName=FRAUD_LAMBDA_NAME,
        InvocationType="RequestResponse",
        Payload=json.dumps({
            "transaction": {
                "amount": transaction["amount"],
                "hour": transaction["hour"],
                "is_international": transaction["is_international"],
                "merchant_risk": transaction["merchant_risk"],
                "txn_count_24h": transaction["txn_count_24h"],
            }
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
        body = json.loads(event.get("body", "{}"))

        transaction = get_feature_payload(user_id, body)
        fraud_result = invoke_fraud_lambda(transaction)

        transaction["prediction_probability"] = fraud_result.get("prediction_probability")
        transaction["fraud_score"] = fraud_result.get("fraud_score")

        return {
            "statusCode": 201,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(transaction)
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }