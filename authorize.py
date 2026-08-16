import base64
import hashlib
import hmac
import os
import secrets
import time
import webbrowser
from urllib.parse import quote, parse_qs

import requests
from dotenv import load_dotenv, set_key


load_dotenv()

CONSUMER_KEY = os.environ["FATSECRET_CONSUMER_KEY"]
CONSUMER_SECRET = os.environ["FATSECRET_CONSUMER_SECRET"]

REQUEST_TOKEN_URL = "https://authentication.fatsecret.com/oauth/request_token"
AUTHORIZE_URL = "https://authentication.fatsecret.com/oauth/authorize"
ACCESS_TOKEN_URL = "https://authentication.fatsecret.com/oauth/access_token"


def encode(value: str) -> str:
    """RFC 3986 percent encoding required by OAuth 1.0."""
    return quote(str(value), safe="~-._")


def make_signature(
    method: str,
    url: str,
    params: dict,
    consumer_secret: str,
    token_secret: str = "",
) -> str:
    # OAuth normalization
    encoded_params = [
        (encode(key), encode(value))
        for key, value in params.items()
    ]

    encoded_params.sort()

    normalized = "&".join(
        f"{key}={value}"
        for key, value in encoded_params
    )

    # OAuth Signature Base String
    base_string = "&".join(
        [
            method.upper(),
            encode(url),
            encode(normalized),
        ]
    )

    # Signing key = Consumer Secret & Token Secret
    signing_key = (
        f"{encode(consumer_secret)}&{encode(token_secret)}"
    )

    digest = hmac.new(
        signing_key.encode(),
        base_string.encode(),
        hashlib.sha1,
    ).digest()

    # IMPORTANT:
    # Return raw Base64.
    # requests will URL-encode it exactly once.
    return base64.b64encode(digest).decode()


def oauth_params():
    return {
        "oauth_consumer_key": CONSUMER_KEY,
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_version": "1.0",
    }


# ---------------------------------------------------------
# STEP 1: Request Token
# ---------------------------------------------------------

params = oauth_params()
params["oauth_callback"] = "oob"

params["oauth_signature"] = make_signature(
    method="POST",
    url=REQUEST_TOKEN_URL,
    params=params,
    consumer_secret=CONSUMER_SECRET,
)

response = requests.post(
    REQUEST_TOKEN_URL,
    data=params,
    headers={
        "Content-Type": "application/x-www-form-urlencoded",
    },
    timeout=30,
)

print("Request token HTTP:", response.status_code)

if not response.ok:
    print(response.text)
    raise SystemExit(1)

request_data = {
    key: values[0]
    for key, values in parse_qs(response.text).items()
}

request_token = request_data["oauth_token"]
request_token_secret = request_data["oauth_token_secret"]

print("✅ Request token получен")


# ---------------------------------------------------------
# STEP 2: User Authorization
# ---------------------------------------------------------

authorization_url = (
    f"{AUTHORIZE_URL}?oauth_token={encode(request_token)}"
)

print("\nОткрой FatSecret:")
print(authorization_url)

webbrowser.open(authorization_url)

verifier = input(
    "\nВставь verification code из FatSecret: "
).strip()


# ---------------------------------------------------------
# STEP 3: Access Token
# ---------------------------------------------------------

params = oauth_params()

params.update(
    {
        "oauth_token": request_token,
        "oauth_verifier": verifier,
    }
)

params["oauth_signature"] = make_signature(
    method="GET",
    url=ACCESS_TOKEN_URL,
    params=params,
    consumer_secret=CONSUMER_SECRET,
    token_secret=request_token_secret,
)

response = requests.get(
    ACCESS_TOKEN_URL,
    params=params,
    timeout=30,
)

print("Access token HTTP:", response.status_code)

if not response.ok:
    print(response.text)
    raise SystemExit(1)

access_data = {
    key: values[0]
    for key, values in parse_qs(response.text).items()
}

access_token = access_data["oauth_token"]
access_token_secret = access_data["oauth_token_secret"]


# ---------------------------------------------------------
# SAVE
# ---------------------------------------------------------

set_key(
    ".env",
    "FATSECRET_ACCESS_TOKEN",
    access_token,
)

set_key(
    ".env",
    "FATSECRET_ACCESS_TOKEN_SECRET",
    access_token_secret,
)

print("\n✅ FatSecret успешно подключён")
print("OAuth access token сохранён в .env")