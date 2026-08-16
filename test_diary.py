import base64
import hashlib
import hmac
import os
import secrets
import time
from datetime import date
from urllib.parse import quote

import requests
from dotenv import load_dotenv

load_dotenv()

CONSUMER_KEY = os.environ["FATSECRET_CONSUMER_KEY"]
CONSUMER_SECRET = os.environ["FATSECRET_CONSUMER_SECRET"]
ACCESS_TOKEN = os.environ["FATSECRET_ACCESS_TOKEN"]
ACCESS_TOKEN_SECRET = os.environ["FATSECRET_ACCESS_TOKEN_SECRET"]

URL = "https://platform.fatsecret.com/rest/food-entries/v2"


def encode(value):
    return quote(str(value), safe="~-._")


def make_signature(method, url, params, consumer_secret, token_secret):
    encoded_params = [
        (encode(k), encode(v))
        for k, v in params.items()
    ]
    encoded_params.sort()

    normalized = "&".join(
        f"{k}={v}" for k, v in encoded_params
    )

    base_string = "&".join([
        method.upper(),
        encode(url),
        encode(normalized),
    ])

    signing_key = (
        f"{encode(consumer_secret)}&{encode(token_secret)}"
    )

    digest = hmac.new(
        signing_key.encode(),
        base_string.encode(),
        hashlib.sha1,
    ).digest()

    return base64.b64encode(digest).decode()


# FatSecret date = number of days since 1970-01-01
today = date.today()
date_int = (today - date(1970, 1, 1)).days

params = {
    "date": str(date_int),
    "format": "json",

    "oauth_consumer_key": CONSUMER_KEY,
    "oauth_token": ACCESS_TOKEN,
    "oauth_nonce": secrets.token_hex(16),
    "oauth_signature_method": "HMAC-SHA1",
    "oauth_timestamp": str(int(time.time())),
    "oauth_version": "1.0",
}

params["oauth_signature"] = make_signature(
    "GET",
    URL,
    params,
    CONSUMER_SECRET,
    ACCESS_TOKEN_SECRET,
)

response = requests.get(
    URL,
    params=params,
    timeout=30,
)

print("HTTP:", response.status_code)
print("Date:", today)

if not response.ok:
    print(response.text)
    raise SystemExit(1)

data = response.json()

food_entries = data.get("food_entries", {})
entries = food_entries.get("food_entry", [])

if isinstance(entries, dict):
    entries = [entries]

if not entries:
    print("\nДневник за сегодня пуст.")
    raise SystemExit(0)

print("\n=== FATSECRET DIARY ===\n")

total_calories = 0
total_protein = 0
total_fat = 0
total_carbs = 0

for entry in entries:
    name = entry.get("food_entry_name", "Unknown")
    description = entry.get("food_entry_description", "")
    meal = entry.get("meal", "")

    calories = float(entry.get("calories", 0))
    protein = float(entry.get("protein", 0))
    fat = float(entry.get("fat", 0))
    carbs = float(entry.get("carbohydrate", 0))

    total_calories += calories
    total_protein += protein
    total_fat += fat
    total_carbs += carbs

    print(f"{meal}: {name}")
    print(f"  {description}")
    print(
        f"  {calories:.0f} kcal | "
        f"P {protein:.1f} | "
        f"F {fat:.1f} | "
        f"C {carbs:.1f}"
    )
    print()

print("======================")
print(f"Calories: {total_calories:.0f} kcal")
print(f"Protein:  {total_protein:.1f} g")
print(f"Fat:      {total_fat:.1f} g")
print(f"Carbs:    {total_carbs:.1f} g")
