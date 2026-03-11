import json

import requests
from requests.auth import HTTPBasicAuth

URL = "http://localhost:8830"
API_KEY = "f406b826-4c16-455d-9b95-61f9d93f4d0c-474308870-143662325"

def login():
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        # "API-Key": API_KEY
        "Authentication": f"Basic User11 welcome"
    }
    url = URL + "/rest/api2/login"
    result = requests.post(url, headers=headers, auth=HTTPBasicAuth("User11", "welcome"), verify=False)
    print("Status Code:", result.status_code)
    print("Response Body:", result.text)
    url = result.json().get("results")[0].get("url")
    jwt = result.json().get("results")[0].get("JWT")
    return url, jwt


def create_users(url, jwt, count=10):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        # "API-Key": API_KEY
        "JWT": jwt
    }
    start = 0
    for i in range(start, start + count + 1):
        user_data = {
            "language": "en",
            "loginName": f"apiuser{i}@yopmail.com",
            "firstName": "API",
            "lastName": f"Test User {i}",
            "role": "Administrator",
            "email": f"apiuser{i}@yopmail.com",
            "@p1": "welcome",
            "password": "welcome"
        }
        create_url = url.strip("/") + "/data/users/"
        print(create_url)
        response = requests.post(create_url, headers=headers, data=json.dumps(user_data), verify=False)
        print(f"Create User {i} - Status Code:", response.status_code)
        print(f"Create User {i} - Response Body:", response.text)

if __name__ == "__main__":
    url, jwt = login()
    create_users(url, jwt, 8)