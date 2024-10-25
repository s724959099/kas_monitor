from datetime import datetime
import time
import requests
import pandas as pd
import json
import pyarrow as pa
import pyarrow.parquet as pq


def line_notify(message):
    token = "wzIhmaEOkRQpxTGRZUJBdOXPUP7t7rqgZoEQXG47eBK"
    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization": f"Bearer {token}"}
    data = {"message": message}
    response = requests.post(url, headers=headers, data=data)
    return response.status_code


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

    existing_data["current_data"] = new_data
    existing_data["history"].append(new_data)

    with open(file_path, "w") as file:
        json.dump(existing_data, file, indent=2)


def read_parquet_file(file_path):
    try:
        return pd.read_parquet(file_path)
    except FileNotFoundError:
        return pd.DataFrame()


def update_parquet_file(file_path, new_data):
    df = read_parquet_file(file_path)
    new_df = pd.DataFrame([new_data])
    updated_df = pd.concat([df, new_df], ignore_index=True)
    updated_df.to_parquet(file_path, index=False)


def fetch_and_process_data(symbol):
    url = f"https://api-v2-do.kas.fyi/token/krc20/{symbol}/info?includeCharts=true&interval=7d"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        processed_data = {
            "timestamp": datetime.now().isoformat(),
            "max_supply": data["maxSupply"],
            "status": data["status"],
            # "holders": [
            #     {
            #         "address": holder["address"],
            #         "amount": holder["amount"],
            #         "percentage": holder["amount"] / data["maxSupply"],
            #     }
            #     for holder in data["holders"]
            # ],
            "holder_total": data["holderTotal"],
            "transfer_total": data["transferTotal"],
            "floor_price": data["price"]["floorPrice"],
            "change24h": data["price"]["change24h"],
            "price_history": data["priceHistory"],
        }

        # 计算 top 5, 10, 15, ..., 50 的总量和百分比
        for i in range(5, 51, 5):
            total_amount = sum(holder["amount"] for holder in data["holders"][:i])
            total_percentage = total_amount / data["maxSupply"]
            processed_data[f"top{i}_total_amount"] = total_amount
            processed_data[f"top{i}_total_percentage"] = total_percentage

        processed_data["symbol"] = symbol
        return processed_data
    else:
        print(f"Failed to fetch data for {symbol}. Status code: {response.status_code}")
        return None


def write_symbols(symbols):
    with open("symbols", "w") as f:
        for symbol in symbols:
            f.write(f"{symbol}\n")


def read_symbols():
    try:
        with open("symbols", "r") as f:
            ret = [line.strip() for line in f if line.strip()]
            print(ret)
            return ret
    except FileNotFoundError:
        return []  # Return default value if file doesn't exist


def task():
    while True:
        symbols = read_symbols()
        print(f"Task executed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        for symbol in symbols:
            data = fetch_and_process_data(symbol)
            if data:
                update_parquet_file(f"{symbol}.parquet", data)
                print(f"Data updated for {symbol}")
        time.sleep(60)  # 休眠60秒


if __name__ == "__main__":
    task()
