import backtrader as bt

class SmaCrossStrategy(bt.Strategy):
    """간단한 이동평균선 교차 전략"""
    params = (
        ('fast_ma', 10),
        ('slow_ma', 50),
    )

    def __init__(self):
        # 파라미터로 받은 기간을 사용하여 이동평균선 지표 생성
        self.sma_fast = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.fast_ma
        )
        self.sma_slow = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.slow_ma
        )
        # 빠른 이평선이 느린 이평선을 상향 돌파/하향 돌파하는 것을 감지
        self.crossover = bt.indicators.CrossOver(self.sma_fast, self.sma_slow)

    def next(self):
        # 디버깅: 현재 데이터 상태 출력
        print(f"Date: {self.data.datetime.date(0)}, Close: {self.data.close[0]:.2f}, Fast MA: {self.sma_fast[0]:.2f}, Slow MA: {self.sma_slow[0]:.2f}, Crossover: {self.crossover[0]}")
        
        # 포지션 상태 및 자본 정보 출력
        position_size = self.position.size if self.position else 0
        current_cash = self.broker.getcash()
        portfolio_value = self.broker.getvalue()
        print(f"  Position: {position_size}, Cash: {current_cash:.2f}, Portfolio: {portfolio_value:.2f}")
        
        if not self.position:  # 현재 포지션이 없으면
            if self.crossover > 0:  # 빠른 이평선이 느린 이평선을 상향 돌파 (골든 크로스)
                print(f"  🟢 BUY SIGNAL at {self.data.datetime.date(0)} - Attempting to buy...")
                self.buy()
                print(f"  ✅ BUY ORDER EXECUTED - New position size: {self.position.size if self.position else 0}")
        elif self.crossover < 0:  # 빠른 이평선이 느린 이평선을 하향 돌파 (데드 크로스)
            print(f"  🔴 SELL SIGNAL at {self.data.datetime.date(0)} - Attempting to sell...")
            self.close()
            print(f"  ✅ SELL ORDER EXECUTED - Position closed")
        
        # 거래 후 상태 확인
        if self.position:
            print(f"  📊 Current Position: Size={self.position.size}, Price={self.position.price:.2f}")
        print("  " + "-"*50)

# 여기에 새로운 전략들을 계속 추가할 수 있습니다.
# 예: class RsiStrategy(bt.Strategy): ...