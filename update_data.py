from datetime import datetime
import time
from app import read_symbols, fetch_and_process_data, update_parquet_file


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
