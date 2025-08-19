import pandas as pd
import backtrader as bt
from datetime import datetime

class DataFactory:
    def __init__(self, data_dir='data/ohlcv'):
        self.data_dir = data_dir

    def get_data_feed(self, symbol, timeframe, start_date, end_date):
        """
        CSV 파일에서 데이터를 로드하여 Backtrader 데이터 피드로 변환합니다.
        """
        filepath = f"{self.data_dir}/{symbol}_{timeframe}.csv"
        try:
            df = pd.read_csv(
                filepath,
                index_col='timestamp',
                parse_dates=True
            )
        except FileNotFoundError:
            print(f"Error: Data file not found at {filepath}")
            raise

        # 날짜 필터링
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        df = df.loc[start_dt:end_dt]

        if df.empty:
            raise ValueError("No data available for the specified date range.")

        # Backtrader의 PandasData 피드로 변환
        data_feed = bt.feeds.PandasData(dataname=df)
        return data_feed