from datetime import datetime
import time
import requests
import pandas as pd
import json
import pyarrow as pa
import pyarrow.parquet as pq
import pandas as pd
import pickle
import os


def read_pickle_file(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as file:
            return pickle.load(file)
    return pd.DataFrame()


def update_pickle_file(file_path, new_data):
    df = read_pickle_file(file_path)
    new_df = pd.DataFrame([new_data])
    updated_df = pd.concat([df, new_df], ignore_index=True)
    with open(file_path, "wb") as file:
        pickle.dump(updated_df, file)


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

    # 转换可能包含大整数的列为字符串
    columns_to_convert = ["max_supply", "holder_total", "transfer_total"]
    for col in columns_to_convert:
        if col in new_df.columns:
            new_df[col] = new_df[col].astype(str)

    # 处理 top N 总量列
    for i in range(5, 51, 5):
        col = f"top{i}_total_amount"
        if col in new_df.columns:
            new_df[col] = new_df[col].astype(str)

    updated_df = pd.concat([df, new_df], ignore_index=True)

    # 创建 PyArrow 表格，明确指定大整数列的类型
    schema = []
    for col in updated_df.columns:
        if col in columns_to_convert or (
            col.startswith("top") and col.endswith("_total_amount")
        ):
            schema.append((col, pa.string()))
        else:
            # 让 PyArrow 自动推断其他列的类型
            schema.append((col, pa.from_numpy_dtype(updated_df[col].dtype)))

    table = pa.Table.from_pandas(updated_df, schema=pa.schema(schema))
    pq.write_table(table, file_path)


def fetch_and_process_data(symbol):
    url = f"https://api-v2-do.kas.fyi/token/krc20/{symbol}/info?includeCharts=true&interval=7d"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        processed_data = {
            "timestamp": datetime.now().isoformat(),
            "max_supply": str(data["maxSupply"]),  # 转换为字符串
            "status": data["status"],
            # "holders": [
            #     {
            #         "address": holder["address"],
            #         "amount": holder["amount"],
            #         "percentage": holder["amount"] / data["maxSupply"],
            #     }
            #     for holder in data["holders"]
            # ],
            "holder_total": str(data["holderTotal"]),  # 转换为字符串
            "transfer_total": str(data["transferTotal"]),  # 转换为字符串
            "floor_price": data.get("price", {}).get("floorPrice", 0),
            "change24h": data.get("price", {}).get("change24h", 0),
            "price_history": data["priceHistory"],
        }

        # 计算 top 5, 10, 15, ..., 50 的总量和百分比
        for i in range(5, 51, 5):
            total_amount = sum(int(holder["amount"]) for holder in data["holders"][:i])
            total_percentage = total_amount / int(data["maxSupply"])
            processed_data[f"top{i}_total_amount"] = str(total_amount)  # 转换为字符串
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
                # update_parquet_file(f"{symbol}.parquet", data)
                update_pickle_file(f"{symbol}.pkl", data)
                print(f"Data updated for {symbol}")
        time.sleep(60)  # 休眠60秒


if __name__ == "__main__":
    task()
