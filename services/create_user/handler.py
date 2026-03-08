import json
import uuid

def lambda_handler(event, context):
    body = json.loads(event.get("body", "{}"))

    return {
        'statusCode': 201,
        'body': json.dumps({
            "id": str(uuid.uuid4()),
            "name": body.get('name', "Dummy User")
        })
    }
