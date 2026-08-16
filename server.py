import base64
import hashlib
import hmac
import os
import secrets
import time
from datetime import date, datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv
from fastmcp import FastMCP


load_dotenv()

CONSUMER_KEY = os.environ["FATSECRET_CONSUMER_KEY"]
CONSUMER_SECRET = os.environ["FATSECRET_CONSUMER_SECRET"]
ACCESS_TOKEN = os.environ["FATSECRET_ACCESS_TOKEN"]
ACCESS_TOKEN_SECRET = os.environ["FATSECRET_ACCESS_TOKEN_SECRET"]

FOOD_ENTRIES_URL = (
    "https://platform.fatsecret.com/rest/food-entries/v2"
)

mcp = FastMCP(
    "FatSecret Diary"
)


def encode(value: str) -> str:
    return quote(str(value), safe="~-._")


def make_signature(
    method: str,
    url: str,
    params: dict,
    consumer_secret: str,
    token_secret: str,
) -> str:
    encoded_params = [
        (encode(key), encode(value))
        for key, value in params.items()
    ]

    encoded_params.sort()

    normalized = "&".join(
        f"{key}={value}"
        for key, value in encoded_params
    )

    base_string = "&".join(
        [
            method.upper(),
            encode(url),
            encode(normalized),
        ]
    )

    signing_key = (
        f"{encode(consumer_secret)}&"
        f"{encode(token_secret)}"
    )

    digest = hmac.new(
        signing_key.encode(),
        base_string.encode(),
        hashlib.sha1,
    ).digest()

    return base64.b64encode(digest).decode()


def resolve_date(date_iso: str | None) -> date:
    if date_iso:
        return date.fromisoformat(date_iso)

    return datetime.now(
        ZoneInfo("Asia/Almaty")
    ).date()


def fatsecret_date(value: date) -> int:
    epoch = date(1970, 1, 1)
    return (value - epoch).days


def number(entry: dict, key: str) -> float:
    try:
        return float(entry.get(key, 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def fetch_diary(
    date_iso: str | None = None,
) -> tuple[date, list[dict]]:
    requested_date = resolve_date(date_iso)

    params = {
        "date": str(
            fatsecret_date(requested_date)
        ),
        "format": "json",
        "oauth_consumer_key": CONSUMER_KEY,
        "oauth_token": ACCESS_TOKEN,
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_version": "1.0",
    }

    params["oauth_signature"] = make_signature(
        method="GET",
        url=FOOD_ENTRIES_URL,
        params=params,
        consumer_secret=CONSUMER_SECRET,
        token_secret=ACCESS_TOKEN_SECRET,
    )

    response = requests.get(
        FOOD_ENTRIES_URL,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    entries = (
        data
        .get("food_entries", {})
        .get("food_entry", [])
    )

    if isinstance(entries, dict):
        entries = [entries]

    return requested_date, entries


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
def get_diary(
    date_iso: str | None = None,
) -> dict:
    """
    Read FatSecret food diary entries.

    Args:
        date_iso:
            Date in YYYY-MM-DD format.
            If omitted, returns today's diary.
    """
    requested_date, entries = fetch_diary(
        date_iso
    )

    foods = []

    for entry in entries:
        foods.append(
            {
                "meal": entry.get("meal"),
                "name": entry.get(
                    "food_entry_name"
                ),
                "description": entry.get(
                    "food_entry_description"
                ),
                "calories": number(
                    entry,
                    "calories",
                ),
                "protein_g": number(
                    entry,
                    "protein",
                ),
                "fat_g": number(
                    entry,
                    "fat",
                ),
                "carbohydrate_g": number(
                    entry,
                    "carbohydrate",
                ),
                "fiber_g": number(
                    entry,
                    "fiber",
                ),
                "sugar_g": number(
                    entry,
                    "sugar",
                ),
            }
        )

    return {
        "date": requested_date.isoformat(),
        "entry_count": len(foods),
        "entries": foods,
    }


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
def get_daily_macros(
    date_iso: str | None = None,
) -> dict:
    """
    Calculate calories and macros from the
    FatSecret food diary.

    Args:
        date_iso:
            Date in YYYY-MM-DD format.
            If omitted, returns today's totals.
    """
    requested_date, entries = fetch_diary(
        date_iso
    )

    totals = {
        "calories": 0.0,
        "protein_g": 0.0,
        "fat_g": 0.0,
        "carbohydrate_g": 0.0,
        "fiber_g": 0.0,
        "sugar_g": 0.0,
    }

    for entry in entries:
        totals["calories"] += number(
            entry,
            "calories",
        )
        totals["protein_g"] += number(
            entry,
            "protein",
        )
        totals["fat_g"] += number(
            entry,
            "fat",
        )
        totals["carbohydrate_g"] += number(
            entry,
            "carbohydrate",
        )
        totals["fiber_g"] += number(
            entry,
            "fiber",
        )
        totals["sugar_g"] += number(
            entry,
            "sugar",
        )

    totals = {
        key: round(value, 1)
        for key, value in totals.items()
    }

    return {
        "date": requested_date.isoformat(),
        "entry_count": len(entries),
        **totals,
    }


if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="127.0.0.1",
        port=8000,
    )