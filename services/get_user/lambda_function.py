import json

def lambda_handler(event, context):
    user_id = (event.get("pathParameters", {})).get("userId")
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "userId": user_id,
            "name": "Dummy User"
        })
    }