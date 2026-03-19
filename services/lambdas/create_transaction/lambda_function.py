import json
import uuid
import boto3

lambda_client = boto3.client("lambda")

FRAUD_LAMBDA_NAME = "fraud-scoring-service"


def get_transaction_payload(user_id, body):
  
    transaction = body.get("transaction", body)

    if not isinstance(transaction, dict):
        raise ValueError("Request body must contain a transaction object")

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
        body = json.loads(event.get("body", "{}"))

        transaction = get_transaction_payload(user_id, body)
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