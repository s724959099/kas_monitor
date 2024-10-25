import requests
import json
import time
from datetime import datetime


def line_notify(message):
    token = "wzIhmaEOkRQpxTGRZUJBdOXPUP7t7rqgZoEQXG47eBK"
    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization": f"Bearer {token}"}
    data = {"message": message}
    response = requests.post(url, headers=headers, data=data)
    return response.status_code


def fetch_and_process_data(symbol):
    url = f"https://api-v2-do.kas.fyi/token/krc20/{symbol}/info?includeCharts=true&interval=7d"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        processed_data = {
            "timestamp": datetime.now().isoformat(),
            "max_supply": data["maxSupply"],
            "status": data["status"],
            "top50_total_amount": sum(
                holder["amount"] for holder in data["holders"][:50]
            ),
            "top50_total_percentage": sum(
                holder["amount"] for holder in data["holders"][:50]
            )
            / data["maxSupply"],
            "top10_total_amount": sum(
                holder["amount"] for holder in data["holders"][:10]
            ),
            "top10_total_percentage": sum(
                holder["amount"] for holder in data["holders"][:10]
            )
            / data["maxSupply"],
            "holder_total": data["holderTotal"],
            "transfer_total": data["transferTotal"],
            "floor_price": data["price"]["floorPrice"],
            "change24h": data["price"]["change24h"],
            "price_history": data["priceHistory"],
        }
        return processed_data
    else:
        print(f"Failed to fetch data for {symbol}. Status code: {response.status_code}")
        return None


def read_existing_data(file_path):
    try:
        with open(file_path, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {"symbol": "", "current_data": {}, "history": []}


def update_json_file(file_path, symbol, new_data):
    existing_data = read_existing_data(file_path)

    if existing_data["symbol"] == "":
        existing_data["symbol"] = symbol

    # 比較新數據與最新歷史記錄
    if existing_data["history"]:
        latest_history = existing_data["history"][-1]
        changes = []
        fields_to_compare = [
            "top50_total_amount",
            "top50_total_percentage",
            "top10_total_amount",
            "top10_total_percentage",
            "holder_total",
            "transfer_total",
            "floor_price",
        ]

        for field in fields_to_compare:
            if new_data[field] != latest_history[field]:
                change = new_data[field] - latest_history[field]
                changes.append(
                    f"{field}: {latest_history[field]} -> {new_data[field]} | change: {change}"
                )

        if changes:
            notification_message = "\n".join(changes)
            line_notify(notification_message)

    existing_data["current_data"] = new_data
    existing_data["history"].append(new_data)

    with open(file_path, "w") as file:
        json.dump(existing_data, file, indent=2)


def main():
    symbol = "BAKA"
    file_path = f"{symbol}_data.json"

    while True:
        current_time = datetime.now()
        data = fetch_and_process_data(symbol)
        if data:
            update_json_file(file_path, symbol, data)
            print(f"Data updated at {current_time}")
        else:
            print(f"Failed to update data at {current_time}")
        time.sleep(300)  # 等待5分鐘


if __name__ == "__main__":
    main()
