import json


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body)
    }


def build_placeholder_user(user_id):
    return {
        "userId": user_id,
        "phoneNumber": "+15555550111",
        "email": "placeholder@example.com",
        "threshold": 0.5,
        "createdAt": "2026-03-23T00:00:00+00:00"
    }


def get_user_by_id(user_id):
    """
    Placeholder retrieval layer.

    In the future, replace this with a real data lookup such as DynamoDB:
    - query by userId
    - return None if the user does not exist
    - map the stored record into the API response shape
    """
    return build_placeholder_user(user_id)


def lambda_handler(event, context):
    user_id = (event.get("pathParameters") or {}).get("userId")

    if not user_id:
        return response(400, {"error": "Missing required path parameter: userId"})

    user_item = get_user_by_id(user_id)
    if user_item is None:
        return response(404, {"error": "User not found"})

    return response(200, user_item)
