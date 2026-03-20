import json
import uuid
from datetime import datetime, timezone
import re

def response(status_code, body):

    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body)
    }

def is_valid_threshold(threshold):
    try:
        threshold = float(threshold)
    except (ValueError, TypeError):
        return False

    if not (0 <= threshold <= 1):
        return False
    
    return True

def is_valid_phone_number(phone_number):
    return re.fullmatch(r"^\+[1-9]\d{7,14}$", phone_number)

def is_valid_email(email):
    return re.fullmatch(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email)

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return response(400, {"error": "Invalid JSON in request body"})
    phone_number = body.get("phone_number")
    email = body.get("email")
    threshold = body.get("threshold", "0.5")
    created_at = datetime.now(timezone.utc).isoformat()

    if not phone_number or not email:
        return response(400, {
            "error": "Missing required fields: phone_number, and email"
        })

    if not is_valid_threshold(threshold):
        return response(400, {
            "error": "threshold must be a number between 0 and 1"
        })
    
    if not is_valid_phone_number(phone_number):
        return response(400, {
            "error": "Invalid phoneNumber, expected E.164"
        })

    if not is_valid_email(email):
        return response(400, {
            "error": "Invalid email format"
        })

    user_item = {
        "userId": str(uuid.uuid4()),
        "phoneNumber": phone_number,
        "email": email,
        "threshold": threshold,
        "createdAt": created_at
    }

    return response(201, user_item)
