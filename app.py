"""
Crypto Data Fetcher - CoinGecko API (Flask version for Render + cron-job.org)
"""

from flask import Flask, jsonify
import requests
import datetime
import os
import json
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)

COIN_IDS = [
    "bitcoin", "ethereum", "binancecoin", "solana",
    "cardano", "ripple", "dogecoin", "polkadot"
]

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
SHEET_NAME = "crypto_price_data"
WORKSHEET_NAME = "prices"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_gsheet_client():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def fetch_crypto_data():
    params = {
        "ids": ",".join(COIN_IDS),
        "vs_currencies": "usd",
        "include_market_cap": "true",
        "include_24hr_vol": "true",
        "include_24hr_change": "true",
    }
    response = requests.get(COINGECKO_URL, params=params, timeout=10)
    if response.status_code != 200:
        raise Exception(f"API Error: {response.status_code} - {response.text}")
    return response.json()


def transform_data(raw_data):
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"
    records = []
    for coin_id, data in raw_data.items():
        record = [
            timestamp,
            coin_id,
            data.get("usd"),
            data.get("usd_market_cap"),
            data.get("usd_24h_vol"),
            data.get("usd_24h_change"),
        ]
        records.append(record)
    return records


def validate_records(records):
    valid_records = []
    for r in records:
        if r[2] is not None:
            valid_records.append(r)
    return valid_records


def save_to_gsheet(records):
    client = get_gsheet_client()
    sheet = client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)
    sheet.append_rows(records, value_input_option="USER_ENTERED")


@app.route("/")
def home():
    return "Crypto Fetcher is running. Hit /fetch to trigger a data pull."


@app.route("/fetch")
def fetch():
    try:
        raw_data = fetch_crypto_data()
        records = transform_data(raw_data)
        valid_records = validate_records(records)

        if valid_records:
            save_to_gsheet(valid_records)
            return jsonify({
                "status": "success",
                "records_saved": len(valid_records),
                "timestamp": datetime.datetime.utcnow().isoformat()
            })
        else:
            return jsonify({"status": "error", "message": "No valid records"}), 400

    except Exception as e:
        return jsonify({"status": "failed", "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
