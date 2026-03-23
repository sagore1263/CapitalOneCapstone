from lambda_function import lambda_handler

event = {
    "pathParameters": {
        "userId": "123e4567-e89b-12d3-a456-426614174000"
    }
}

result = lambda_handler(event, None)
print(result)
