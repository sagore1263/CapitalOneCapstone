import json

def lambda_handler(event, context):

    users = [
        {"id": "u1", "name": "Alice"},
        {"id": "u2", "name": "Bob"},
        {"id": "u3", "name": "Charlie"}
    ]

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "applications/json"
        },
        "body": json.dumps(users)
    }