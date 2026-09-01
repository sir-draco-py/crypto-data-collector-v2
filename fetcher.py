"""
Crypto Data Fetcher - CoinGecko API
Mengambil data harga & market crypto, lalu simpan ke Google Sheets
"""

import requests
import datetime
import os
import json
import gspread
from google.oauth2.service_account import Credentials

# ==== KONFIGURASI ====
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
    """Autentikasi ke Google Sheets pakai service account dari env variable"""
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def fetch_crypto_data():
    """Ambil data dari CoinGecko dalam 1 API call untuk semua coin"""
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
    """Ubah response JSON jadi list of records yang siap disimpan"""
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
    """Validasi sederhana: pastikan price_usd (index ke-2) tidak None"""
    valid_records = []
    for r in records:
        if r[2] is not None:
            valid_records.append(r)
        else:
            print(f"[WARNING] Data invalid untuk {r[1]}, dilewati")
    return valid_records


def save_to_gsheet(records):
    """Kirim data ke Google Sheets"""
    client = get_gsheet_client()
    sheet = client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)
    sheet.append_rows(records, value_input_option="USER_ENTERED")


def main():
    print(f"[{datetime.datetime.utcnow()}] Mulai fetch data...")

    try:
        raw_data = fetch_crypto_data()
        records = transform_data(raw_data)
        valid_records = validate_records(records)

        if valid_records:
            save_to_gsheet(valid_records)
            print(f"[SUCCESS] {len(valid_records)} record berhasil disimpan")
        else:
            print("[ERROR] Tidak ada data valid untuk disimpan")

    except Exception as e:
        print(f"[FAILED] Fetch gagal: {e}")


if __name__ == "__main__":
    main()
