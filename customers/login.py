import requests
import base64


def basic_token(username: str, password: str, separator=":") -> str:
    raw = f"{username}{separator}{password}".encode("utf-8")
    return base64.b64encode(raw).decode("ascii")

def get_jwt(username, password, login_url):
    # Use colon by default
    token = basic_token(username, password, separator=":")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {token}",
    }

    print("Headers for login request:", headers)
    r = requests.post(login_url, headers=headers, timeout=30)

    if r.status_code != 200:
        raise Exception(f"Login failed: {r.status_code} - {r.text}")

    data = r.json()
    jwt = data["results"][0]["JWT"]
    api_url = data["results"][0]["url"]
    print("✅ JWT received")
    print("JWT:", jwt)
    print("API URL:", api_url)
    return jwt, api_url

if __name__ == "__main__":
    LOGIN_URL = "http://localhost:8830/rest/api2/login"
    USERNAME = "admin"
    PASSWORD = "welcome"
    get_jwt(USERNAME, PASSWORD, LOGIN_URL)