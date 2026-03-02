#!/usr/bin/env python3
"""
Reusable DynamoDB boilerplate service.

Provides:
- Session initialization from environment variables
- Get table
- Put item
- Get item
- Update item
- Delete item
- Query
- Scan
"""

import os
from typing import Any, Dict, List, Optional

import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError


class DynamoDBService:
    def __init__(self):
        self._validate_env()

        self.session = boto3.Session(
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
            region_name=os.getenv("AWS_REGION"),
        )

        self.client = self.session.client("dynamodb")
        self.resource = self.session.resource("dynamodb")

    # -------------------------
    # Internal helpers
    # -------------------------

    def _validate_env(self):
        required = [
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_REGION",
        ]
        for var in required:
            if not os.getenv(var):
                raise RuntimeError(f"Missing required environment variable: {var}")

    # -------------------------
    # Core Table Methods
    # -------------------------

    def get_table(self, table_name: str):
        """Return a DynamoDB Table resource."""
        return self.resource.Table(table_name)

    # -------------------------
    # CRUD Operations
    # -------------------------

    def put_item(self, table_name: str, item: Dict[str, Any]) -> None:
        """Create or overwrite an item."""
        table = self.get_table(table_name)
        table.put_item(Item=item)

    def get_item(self, table_name: str, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Fetch a single item by primary key."""
        table = self.get_table(table_name)
        response = table.get_item(Key=key)
        return response.get("Item")

    def delete_item(self, table_name: str, key: Dict[str, Any]) -> None:
        """Delete item by primary key."""
        table = self.get_table(table_name)
        table.delete_item(Key=key)

    def update_item(
        self,
        table_name: str,
        key: Dict[str, Any],
        update_expression: str,
        expression_values: Dict[str, Any],
        expression_names: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Update an item using DynamoDB update expressions.
        Example update_expression:
            "SET #name = :name"
        """
        table = self.get_table(table_name)

        response = table.update_item(
            Key=key,
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ExpressionAttributeNames=expression_names,
            ReturnValues="ALL_NEW",
        )

        return response.get("Attributes", {})

    # -------------------------
    # Query & Scan
    # -------------------------

    def query(
        self,
        table_name: str,
        key_condition_expression,
        filter_expression=None,
        index_name: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query by partition key (and optional sort key).
        Requires KeyConditionExpression.
        """
        table = self.get_table(table_name)

        kwargs = {
            "KeyConditionExpression": key_condition_expression,
        }

        if filter_expression:
            kwargs["FilterExpression"] = filter_expression
        if index_name:
            kwargs["IndexName"] = index_name
        if limit:
            kwargs["Limit"] = limit

        items = []
        response = table.query(**kwargs)
        items.extend(response.get("Items", []))

        while "LastEvaluatedKey" in response:
            response = table.query(
                ExclusiveStartKey=response["LastEvaluatedKey"],
                **kwargs,
            )
            items.extend(response.get("Items", []))

        return items

    def scan(
        self,
        table_name: str,
        filter_expression=None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Full table scan (use carefully).
        """
        table = self.get_table(table_name)

        kwargs = {}
        if filter_expression:
            kwargs["FilterExpression"] = filter_expression
        if limit:
            kwargs["Limit"] = limit

        items = []
        response = table.scan(**kwargs)
        items.extend(response.get("Items", []))

        while "LastEvaluatedKey" in response:
            response = table.scan(
                ExclusiveStartKey=response["LastEvaluatedKey"],
                **kwargs,
            )
            items.extend(response.get("Items", []))

        return items

    # -------------------------
    # Utility Methods
    # -------------------------

    def list_tables(self) -> List[str]:
        """List all DynamoDB tables."""
        response = self.client.list_tables()
        return response.get("TableNames", [])

    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        try:
            self.client.describe_table(TableName=table_name)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                return False
            raise