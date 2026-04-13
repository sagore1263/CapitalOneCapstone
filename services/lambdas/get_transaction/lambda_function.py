import json
import boto3
import os
from decimal import Decimal
from boto3.dynamodb.conditions import Attr

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TRANSACTIONS_TABLE"])


def decimal_to_native(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: decimal_to_native(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [decimal_to_native(v) for v in obj]
    return obj


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body)
    }


def lambda_handler(event, context):
    transaction_id = (event.get("pathParameters") or {}).get("transactionId")

    if not transaction_id:
        return response(400, {"error": "Missing required path parameter: transactionId"})

    result = table.scan(
        FilterExpression=Attr("transactionId").eq(str(transaction_id))
    )

    items = result.get("Items", [])

    if not items:
        return response(404, {"error": "Transaction not found"})

    return response(200, decimal_to_native(items[0]))