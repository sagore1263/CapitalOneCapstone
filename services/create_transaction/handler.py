import json
import uuid

def lambda_handler(event, context):
    user_id = event.get("pathParameters", {}).get("userId")
    body = json.loads(event.get("body", "{}"))

    return {
        'statusCode': 201,
        'body': json.dumps({
            "transactionId": str(uuid.uuid4()),
            "user_id": user_id,
            "amount": body.get("amount", 0.0)
        })
    }
