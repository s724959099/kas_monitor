import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np
import threading
import time
import requests
import json
import pyarrow as pa
import pyarrow.parquet as pq

# 确保这是第一个 Streamlit 命令
st.set_page_config(layout="wide")

# 自定义 CSS 可以放在这里
st.markdown(
    """
<style>
    .reportview-container .main .block-container {
        max-width: 1200px;
        padding-top: 2rem;
        padding-right: 2rem;
        padding-left: 2rem;
        padding-bottom: 2rem;
    }
</style>
""",
    unsafe_allow_html=True,
)


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
            "holders": [
                {
                    "address": holder["address"],
                    "amount": holder["amount"],
                    "percentage": holder["amount"] / data["maxSupply"],
                }
                for holder in data["holders"]
            ],
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


# Read token list
def read_symbols():
    try:
        with open("symbols", "r") as f:
            ret = [line.strip() for line in f if line.strip()]
            print(ret)
            return ret
    except FileNotFoundError:
        return []  # Return default value if file doesn't exist


# Write token list
def write_symbols(symbols):
    with open("symbols", "w") as f:
        for symbol in symbols:
            f.write(f"{symbol}\n")


# Create Streamlit application
st.title("KAS Golden Dog")

# Initialize session state
if "symbols" not in st.session_state:
    st.session_state.symbols = read_symbols()

# Input box for adding new token
new_symbol = st.text_input("Add new token")
if st.button("Add Token"):
    if new_symbol and new_symbol.upper() not in st.session_state.symbols:
        st.session_state.symbols.append(new_symbol.upper())
        write_symbols(st.session_state.symbols)
        st.success(f"Token '{new_symbol}' has been added")

selected_symbol = st.selectbox(
    "Select token to display",
    options=st.session_state.symbols,
    index=0,  # Default to the first token in the list
)

df = read_parquet_file(f"{selected_symbol}.parquet")

if not df.empty:
    st.text(f"Last updated: {df['timestamp'].max()}")

    # 創建並顯示折線圖
    col1, col2 = st.columns(2)
    for idx, i in enumerate(range(5, 51, 5)):
        column_name = f"top{i}_total_percentage"
        fig = px.line(
            df,
            x="timestamp",
            y=column_name,
            title=f"Top {i} Holders Percentage Over Time for {selected_symbol}",
        )
        fig.update_layout(legend_title_text="Holder Group", height=300, width=400)

        if idx % 2 == 0:
            with col1:
                st.plotly_chart(fig, use_container_width=True)
        else:
            with col2:
                st.plotly_chart(fig, use_container_width=True)
else:
    st.write("No data available for this token yet.")

# 創建並啟動後台線程
