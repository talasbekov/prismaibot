import re

with open("backend/app/billing/apipay_client.py", "r") as f:
    content = f.read()

# Fix ApiPaySubscriptionResponse
content = re.sub(
    r"class ApiPaySubscriptionResponse\(BaseModel\):\n    id: int\n    status: str\n    amount: float\n    period: str",
    "class ApiPaySubscriptionResponse(BaseModel):\n    id: int\n    status: str\n    amount: float\n    billing_period: str",
    content
)

# Fix create_invoice payload
content = re.sub(
    r'"phone_number": phone_number,\n            "is_sandbox": self\.is_sandbox,\n        }',
    '"phone_number": phone_number,\n        }',
    content
)

# Fix create_subscription payload
content = re.sub(
    r'"phone_number": phone_number,\n            "period": period,\n            "is_sandbox": self\.is_sandbox,\n        }',
    '"phone_number": phone_number,\n            "billing_period": period,\n        }',
    content
)

# Fix create_subscription response parsing
content = re.sub(
    r'data = response\.json\(\)\n            return ApiPaySubscriptionResponse\(\*\*data\)',
    'data = response.json()\n            sub_data = data.get("subscription", data)\n            return ApiPaySubscriptionResponse(**sub_data)',
    content
)

# Fix cancel_subscription HTTP method and path
content = re.sub(
    r'response = await client\.delete\(\n                f"\{self\.base_url\}/subscriptions/\{subscription_id\}",',
    'response = await client.post(\n                f"{self.base_url}/subscriptions/{subscription_id}/cancel",',
    content
)

with open("backend/app/billing/apipay_client.py", "w") as f:
    f.write(content)
