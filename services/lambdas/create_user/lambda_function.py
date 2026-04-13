import json
from datetime import datetime, timezone
import re
import boto3
import os
from decimal import Decimal
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["USERS_TABLE"])


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body)
    }


def decimal_to_native(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: decimal_to_native(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [decimal_to_native(v) for v in obj]
    return obj


def is_valid_threshold(threshold):
    try:
        threshold = float(threshold)
    except (ValueError, TypeError):
        return False
    return 0 <= threshold <= 1


def is_valid_card_number(card_number):
    try:
        int(card_number)
        return True
    except (ValueError, TypeError):
        return False


def is_valid_phone_number(phone_number):
    return re.fullmatch(r"^\+[1-9]\d{7,14}$", phone_number) is not None


def is_valid_email(email):
    return re.fullmatch(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email) is not None


def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return response(400, {"error": "Invalid JSON in request body"})

    phone_number = body.get("phone_number")
    email = body.get("email")
    threshold = body.get("threshold", 0.5)
    card_number = body.get("card_number")
    created_at = datetime.now(timezone.utc).isoformat()

    if not phone_number or not email or not card_number:
        return response(400, {
            "error": "Missing required fields: phone_number, card_number, and email"
        })

    if not is_valid_threshold(threshold):
        return response(400, {
            "error": "threshold must be a number between 0 and 1"
        })

    if not is_valid_phone_number(phone_number):
        return response(400, {
            "error": "Invalid phone number, expected E.164"
        })

    if not is_valid_email(email):
        return response(400, {
            "error": "Invalid email format"
        })

    if not is_valid_card_number(card_number):
        return response(400, {
            "error": "Invalid card number format"
        })

    user_item = {
        "cardNumber": str(card_number),
        "phoneNumber": phone_number,
        "email": email,
        "threshold": Decimal(str(threshold)),
        "createdAt": created_at,
    }

    try:
        table.put_item(
            Item=user_item,
            ConditionExpression="attribute_not_exists(cardNumber)"
        )
    except ClientError as e:
        error_code = e.response["Error"]["Code"]

        if error_code == "ConditionalCheckFailedException":
            return response(409, {"error": "User already exists"})

        return response(500, {
            "error": "Failed to create user",
            "details": str(e)
        })

    return response(201, decimal_to_native(user_item))