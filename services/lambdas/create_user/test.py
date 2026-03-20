from lambda_function import lambda_handler

event = {
    "body": """
    {
        "phone_number": "+9253603306",
        "email": "kyle@example.com",
        "threshold": "0.7"
    }
    """
}

result = lambda_handler(event, None)
print(result)