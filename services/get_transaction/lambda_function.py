import json
import uuid

def lambda_handler(event, context):

    transaction_id = event.get('pathParameters', {}).get('transactionId')

    return {
        'statusCode': 200,
        'body': json.dumps({
            'transactionId': transaction_id,
            'user_id': str(uuid.uuid4()),
            'amount': '100',
        })
    }
