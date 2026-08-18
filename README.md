# FatSecret MCP Server

FatSecret MCP Server is a private, read-only Model Context Protocol (MCP) service that makes personal FatSecret diary data available to MCP-compatible AI clients. It retrieves food entries, calculates daily nutrition totals, reports weight history, and combines nutrition and weight data into a progress summary.

The server uses FatSecret OAuth 1.0 credentials to access diary data and Google OAuth to authenticate MCP clients. Access is restricted to one email address through the `ALLOWED_EMAIL` setting.

## Features

- Read food diary entries for a specific date.
- Calculate calories, protein, fat, carbohydrates, fiber, and sugar for a day.
- Retrieve up to 24 calendar months of weight history.
- Summarize nutrition logging and weight changes over a period of 7 to 365 days.
- Authenticate MCP clients with Google OAuth.
- Restrict access to a single Google account.
- Run locally or in a Docker container over stateless HTTP.

All MCP tools are read-only and do not add, update, or delete FatSecret data.

## Requirements

- Python 3.12 or later
- [uv](https://docs.astral.sh/uv/) for dependency management
- A FatSecret Platform application with consumer credentials
- A FatSecret user access token and token secret
- A Google OAuth client for protecting the MCP server
- A public HTTPS URL when using the Google OAuth flow outside local development

## Configuration

Create a `.env` file in the project root:

```dotenv
FATSECRET_CONSUMER_KEY=your_consumer_key
FATSECRET_CONSUMER_SECRET=your_consumer_secret
FATSECRET_ACCESS_TOKEN=your_access_token
FATSECRET_ACCESS_TOKEN_SECRET=your_access_token_secret

GOOGLE_OAUTH_CLIENT_ID=your_google_client_id
GOOGLE_OAUTH_CLIENT_SECRET=your_google_client_secret
PUBLIC_BASE_URL=https://your-server.example.com
ALLOWED_EMAIL=owner@example.com

PORT=8080
```

`PORT` is optional and defaults to `8080`. The server reads all other variables during startup and exits if a required value is missing.

Keep `.env` private. It contains credentials that grant access to personal FatSecret data.

## Installation and authorization

Install the dependencies:

```bash
uv sync
```

If you do not yet have a FatSecret access token, first add `FATSECRET_CONSUMER_KEY` and `FATSECRET_CONSUMER_SECRET` to `.env`, then run:

```bash
uv run python authorize.py
```

The script opens FatSecret in a browser. Approve access, paste the displayed verification code into the terminal, and the script will save `FATSECRET_ACCESS_TOKEN` and `FATSECRET_ACCESS_TOKEN_SECRET` to `.env`.

## Running the server

Start the HTTP MCP server:

```bash
uv run python server.py
```

By default, the service listens on `0.0.0.0:8080`. The MCP endpoint is available at:

```text
http://localhost:8080/mcp
```

For remote use, configure an HTTPS reverse proxy or deploy the container to a platform that provides HTTPS. Set `PUBLIC_BASE_URL` to the externally reachable base URL used by Google OAuth.

## Docker

Build and run the container:

```bash
docker build -t fatsecret-mcp .
docker run --rm --env-file .env -p 8080:8080 fatsecret-mcp
```

## Methods

The MCP server exposes four methods. Each accepts and returns JSON-compatible values.

### `get_diary`

Returns individual food diary entries for one day.

Parameters:

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `date_iso` | `string` or `null` | No | Date in `YYYY-MM-DD` format. Defaults to the current date in the `Asia/Almaty` time zone. |

The response contains the requested date, the number of entries, and an `entries` array. Each entry includes the meal, food name, description, calories, protein, fat, carbohydrates, fiber, and sugar.

Example response:

```json
{
  "date": "2026-08-18",
  "entry_count": 1,
  "entries": [
    {
      "meal": "breakfast",
      "name": "Oatmeal",
      "description": "1 serving",
      "calories": 250.0,
      "protein_g": 9.0,
      "fat_g": 5.0,
      "carbohydrate_g": 42.0,
      "fiber_g": 6.0,
      "sugar_g": 8.0
    }
  ]
}
```

### `get_daily_macros`

Calculates nutrition totals from all diary entries for one day.

Parameters:

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `date_iso` | `string` or `null` | No | Date in `YYYY-MM-DD` format. Defaults to the current date in the `Asia/Almaty` time zone. |

The response contains the date, entry count, calories, protein, fat, carbohydrates, fiber, and sugar. Numeric totals are rounded to one decimal place.

### `get_weight_history`

Returns weight entries for a range of calendar months and calculates the total change between the first and latest entry.

Parameters:

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `months` | `integer` | No | `3` | Number of calendar months to retrieve, from `1` to `24`. |
| `end_date_iso` | `string` or `null` | No | Current date | Date in `YYYY-MM-DD` format whose calendar month is the final month in the range. |

The response includes the requested month count, entry count, date range, first and latest weights, weight change in kilograms, and the sorted weight entries. Each entry contains a date, weight in kilograms, and an optional comment. If no data exists, the response contains an empty `entries` array.

### `get_progress_summary`

Combines daily nutrition totals and weight history for a date range.

Parameters:

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `days` | `integer` | No | `30` | Number of calendar days to analyze, from `7` to `365`. |
| `end_date_iso` | `string` or `null` | No | Current date | Inclusive end date in `YYYY-MM-DD` format. |

The response contains:

- `period`: the number of days and inclusive start and end dates.
- `nutrition`: logged-day count, logging coverage, and average daily calories and macros, or `null` when no nutrition data is available.
- `weight`: first and latest measurements, total change, and weekly change rate, or `null` when no weight data is available.

## Authentication and data flow

```text
MCP client
    -> Google OAuth authentication
    -> allowed-email check
    -> FatSecret MCP tool
    -> signed FatSecret OAuth 1.0 request
    -> normalized JSON response
```

Google OAuth identifies the MCP client user. The server compares the authenticated email claim with `ALLOWED_EMAIL`; all other users are denied. FatSecret credentials remain on the server and are not returned to MCP clients.

## Error behavior

- Invalid ISO dates are rejected during date parsing.
- `get_weight_history` rejects `months` values outside `1` to `24`.
- `get_progress_summary` rejects `days` values outside `7` to `365`.
- FatSecret HTTP errors are propagated by the server.
- Missing required environment variables prevent the server from starting.
