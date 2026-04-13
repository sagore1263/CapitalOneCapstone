import json
import boto3
import os
from decimal import Decimal

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["USERS_TABLE"])


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
    user_id = (event.get("pathParameters") or {}).get("userId")

    if not user_id:
        return response(400, {"error": "Missing required path parameter: userId"})

    # Current users table is keyed by cardNumber, so userId is treated as cardNumber.
    result = table.get_item(Key={"cardNumber": str(user_id)})
    item = result.get("Item")

    if not item:
        return response(404, {"error": "User not found"})

    return response(200, decimal_to_native(item))