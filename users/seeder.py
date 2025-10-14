import json

import requests

URL = "https://bcictemp-int.eng.infiniteblue.com"
API_KEY = "f406b826-4c16-455d-9b95-61f9d93f4d0c-474308870-143662325"

def login():
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "API-Key": API_KEY
    }
    url = URL + "/rest/api2/login"
    result = requests.post(url, headers=headers, verify=False)
    print("Status Code:", result.status_code)
    print("Response Body:", result.text)
    url = result.json().get("results")[0].get("url")
    return url


def create_users(url, count=10):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "API-Key": API_KEY
    }
    start = 8
    for i in range(start, start + count + 1):
        user_data = {
            "language": "en",
            "loginName": f"apiuser{i}@yopmail.com",
            "firstName": "API",
            "lastName": f"Test User {i}",
            "role": "Administrator API",
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
    url = login()
    create_users(url, 12)