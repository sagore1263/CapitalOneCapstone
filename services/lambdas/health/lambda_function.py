import json

def lambda_handler(event, context):
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "applications/json"
        },
        "body": json.dumps({
            "status": "ok",
            "body": "Testing deploy",
            "service": "fraud-detection-api"
        })
    }