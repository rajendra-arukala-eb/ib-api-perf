import base64

import requests
import uuid
import random
import string

from customers.config import URL_CREATE_CUSTOMER, LOGIN_URL, CUSTOMER_DB
from customers.login import get_jwt


def random_string(length=6):
    return ''.join(random.choices(string.ascii_lowercase, k=length))

def create_customer_payload(index):
    unique = uuid.uuid4().hex[:8]

    return {
        "companyName": f"Company-{unique}",
        "loginName": f"user_{unique}",
        "email": f"user_{unique}@example.com",
        "firstName": f"First{index}",
        "lastName": f"Last{index}",
        "dbName": CUSTOMER_DB,
        "mobileDevEnabled": True,
        "password": "welcome",
        "password": "welcome",
        "timeZone": "Asia/Calcutta",
        "maxApplications": 100,
        "country": "US",
        "language": "en",
        "maxStorageMB": 250,
        "maxFieldDefs": 40000,
        "serviceLevel": 2,
        "maxUsers": 5,
        "securityLevel": 1,
        "maxObjectDefs": 2000,
        "process": "Customer Default"
    }


if __name__ == "__main__":
    jwt, api_url = get_jwt("admin2", "welcome", LOGIN_URL)
    headers = {
        "Content-Type": "application/json",
        "JWT": jwt
    }
    print("Headers for requests:", headers)

    success = 0
    failure = 0

    for i in range(1, 2):
        payload = create_customer_payload(i)
        response = requests.post(URL_CREATE_CUSTOMER, json=payload, headers=headers)

        if response.status_code in (200, 201):
            success += 1
            print(f"✅ Created customer {i}: {payload['loginName']}")
        else:
            failure += 1
            print(f"❌ Failed customer {i}: {response.status_code} - {response.text}")

        print("\n===== SUMMARY =====")
        print(f"Success: {success}")
        print(f"Failure: {failure}")
