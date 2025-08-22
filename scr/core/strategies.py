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
        print(f"Date: {self.data.datetime.date(0)}, Close: "
              f"{self.data.close[0]:.2f}, Fast MA: {self.sma_fast[0]:.2f}, "
              f"Slow MA: {self.sma_slow[0]:.2f}, Crossover: {self.crossover[0]}")
        
        # 포지션 상태 및 자본 정보 출력
        position_size = self.position.size if self.position else 0
        current_cash = self.broker.getcash()
        portfolio_value = self.broker.getvalue()
        print(f"  Position: {position_size}, Cash: {current_cash:.2f}, "
              f"Portfolio: {portfolio_value:.2f}")
        
        if not self.position:  # 현재 포지션이 없으면
            if self.crossover > 0:  # 빠른 이평선이 느린 이평선을 상향 돌파 (골든 크로스)
                print(f"  🟢 BUY SIGNAL at {self.data.datetime.date(0)} - "
                      f"Attempting to buy...")
                self.buy()
                new_position_size = self.position.size if self.position else 0
                print(f"  ✅ BUY ORDER EXECUTED - New position size: {new_position_size}")
        elif self.crossover < 0:  # 빠른 이평선이 느린 이평선을 하향 돌파 (데드 크로스)
            print(f"  🔴 SELL SIGNAL at {self.data.datetime.date(0)} - "
                  f"Attempting to sell...")
            self.close()
            print("  ✅ SELL ORDER EXECUTED - Position closed")
        
        # 거래 후 상태 확인
        if self.position:
            print(f"  📊 Current Position: Size={self.position.size}, "
                  f"Price={self.position.price:.2f}")
        print("  " + "-"*50)


class MACD_LinePeakStrategy_v2(bt.Strategy):
    """
    [롱 전용] 3-MACD 고급 전략 - 리스크 기반 사이징 + 동적 스톱로스

    - 리스크 관리:
      1. 1% 리스크 기반 포지션 사이징
      2. ATR/퍼센트/틱 기반 동적 스톱로스
      3. 3단계 청산 시스템 (스톱로스 + 부분청산 + 최종청산)

    - 진입 조건:
      1. 3개 MACD(5/20, 5/40, 20/40)의 MACD 선이 모두 상승 추세
      2. 5/40 MACD의 MACD 선이 0선 위에 있을 것

    - 청산 로직:
      1. 스톱로스: ATR/퍼센트/틱 기반 손절
      2. 부분청산(50%): 5/40 MACD 선 피크아웃 시
      3. 최종청산: MACD 데드크로스 시
    """
    params = (
        ('p_fast1', 5),
        ('p_slow1', 20),
        ('p_fast2', 5),
        ('p_slow2', 40),  # 핵심 신호 MACD
        ('p_fast3', 20),
        ('p_slow3', 40),
        ('p_signal', 9),
        # 리스크 관리 파라미터
        ('risk_pct', 1.0),           # 거래당 리스크 (%)
        ('sl_mode', 'ATR'),          # 스톱로스 모드: 'ATR', 'Percent', 'Ticks'
        ('atr_len', 14),             # ATR 기간
        ('atr_mult', 2.0),           # ATR 배수
        ('sl_percent', 1.5),         # 퍼센트 스톱로스 (%)
        ('sl_ticks', 50),            # 틱 기반 스톱로스
        ('min_qty', 0.0001),         # 최소 주문 수량
        ('debug', False),
    )

    def __init__(self):
        # 3개의 MACD 지표 생성
        self.macd_1 = bt.ind.MACD(self.data.close,
                                  period_me1=self.p.p_fast1, period_me2=self.p.p_slow1,
                                  period_signal=self.p.p_signal)
        self.macd_2_main = bt.ind.MACD(self.data.close,
                                       period_me1=self.p.p_fast2, period_me2=self.p.p_slow2,
                                       period_signal=self.p.p_signal)
        self.macd_3 = bt.ind.MACD(self.data.close,
                                  period_me1=self.p.p_fast3, period_me2=self.p.p_slow3,
                                  period_signal=self.p.p_signal)

        # ATR 지표 (스톱로스용)
        self.atr = bt.ind.ATR(self.data, period=self.p.atr_len)

        # 최종 청산을 위한 5/40 MACD선-시그널선 교차 지표
        self.macd_cross_signal = bt.ind.CrossOver(
            self.macd_2_main.macd, self.macd_2_main.signal)

        # 상태 변수
        self.order = None
        self.position_level = 0  # 0: 무포지션, 1: 1/2 포지션, 2: 풀포지션
        self.peak_detected = False
        self.stop_price = None
        self.entry_price = None

    def _log(self, txt, dt=None):
        if self.p.debug:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'[{dt.isoformat()}] {txt}')

    def calculate_stop_distance(self, entry_price):
        """스톱로스 거리 계산"""
        if self.p.sl_mode == 'ATR':
            return self.atr[0] * self.p.atr_mult
        elif self.p.sl_mode == 'Percent':
            return entry_price * (self.p.sl_percent / 100)
        else:  # 'Ticks'
            # 기본 틱 사이즈를 0.01로 가정 (실제로는 거래소별로 다름)
            tick_size = 0.01
            return self.p.sl_ticks * tick_size

    def calculate_position_size(self, entry_price, stop_distance):
        """리스크 기반 포지션 사이징"""
        try:
            portfolio_value = self.broker.getvalue()
            risk_cash = portfolio_value * (self.p.risk_pct / 100)
            
            if stop_distance > 0:
                position_size = risk_cash / stop_distance
                return max(position_size / entry_price, self.p.min_qty)
            else:
                # 스톱 거리가 0이면 기본 사이징
                return portfolio_value * 0.02 / entry_price  # 2% 포지션
        except Exception:
            return self.p.min_qty

    def check_stop_loss(self):
        """스톱로스 체크"""
        if self.position and self.stop_price:
            return self.data.close[0] <= self.stop_price
        return False

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.entry_price = order.executed.price
                # 스톱로스 가격 계산
                stop_distance = self.calculate_stop_distance(self.entry_price)
                self.stop_price = self.entry_price - stop_distance
                self._log(f'BUY EXECUTED: Price={self.entry_price:.4f}, '
                         f'Stop={self.stop_price:.4f}')
            self.order = None
            if not self.position:  # 포지션이 완전히 청산되면 상태 초기화
                self.position_level = 0
                self.peak_detected = False
                self.stop_price = None
                self.entry_price = None
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.order = None

    def next(self):
        if self.order:
            return
        # 모든 MACD가 안정적으로 계산될 수 있는 기간
        if len(self.data) < self.p.p_slow2 + self.p.p_signal:
            return

        # TradingView와 동일하게 봉 마감 기준으로만 실행 (리페인트 방지)
        if len(self.data) > 1 and self.data.datetime.date(0) <= self.data.datetime.date(-1):
            return

        # 신호 중복 방지
        if hasattr(self, 'last_signal_bar') and self.last_signal_bar == len(self.data):
            return

        # --- 1. 스톱로스 체크 (최우선) ---
        if self.check_stop_loss():
            self._log(f'STOP LOSS TRIGGERED: Price={self.data.close[0]:.4f}, '
                     f'Stop={self.stop_price:.4f}')
            self.order = self.close()
            self.last_signal_bar = len(self.data)
            return

        # --- 2. 진입 조건 계산 ---
        trend_1_rising = self.macd_1.macd[0] > self.macd_1.macd[-1]
        trend_2_rising = self.macd_2_main.macd[0] > self.macd_2_main.macd[-1]
        trend_3_rising = self.macd_3.macd[0] > self.macd_3.macd[-1]
        is_unified_uptrend = trend_1_rising and trend_2_rising and trend_3_rising
        is_macd2_above_zero = self.macd_2_main.macd[0] > 0

        # --- 3. 청산 조건 계산 ---
        m = self.macd_2_main.macd
        is_macd_line_peaked = m[-2] < m[-1] > m[0]
        is_macd_cross_down = self.macd_cross_signal[0] < 0

        signal_generated = False

        # --- 4. 진입 로직 ---
        if not self.position:
            if is_unified_uptrend and is_macd2_above_zero:
                entry_price = self.data.close[0]
                stop_distance = self.calculate_stop_distance(entry_price)
                position_size = self.calculate_position_size(entry_price, stop_distance)
                
                self._log(f'BUY SIGNAL: Entry={entry_price:.4f}, '
                         f'StopDist={stop_distance:.4f}, Size={position_size:.6f}')
                
                self.order = self.buy(size=position_size)
                self.position_level = 2
                self.peak_detected = False
                signal_generated = True

        # --- 5. 청산 로직 ---
        elif self.position:
            # 부분 청산 (MACD 피크)
            if (self.position_level == 2 and is_macd_line_peaked
                    and not self.peak_detected):
                size_to_sell = self.position.size * 0.5
                self._log(f'EXIT-1/2 SIGNAL: MACD Line peak detected. '
                         f'Selling 50%: {size_to_sell:.6f}')
                self.order = self.sell(size=size_to_sell)
                self.position_level = 1
                self.peak_detected = True
                signal_generated = True

            # 최종 청산 (데드크로스)
            elif self.position_level > 0 and is_macd_cross_down:
                self._log('EXIT-FINAL SIGNAL: MACD/Signal cross down. '
                         f'Closing remaining position.')
                self.order = self.close()
                signal_generated = True

        # 신호가 발생한 경우 현재 봉을 기록하여 중복 실행 방지
        if signal_generated:
            self.last_signal_bar = len(self.data)


class MACD_LinePeakStrategy(bt.Strategy):
    """
    [롱 전용] 3-MACD 추세 확인 및 MACD 선(Line) 피크아웃 분할 청산 전략

    - 롱 진입 조건 (모두 충족 시):
      1. 3개 MACD(5/20, 5/40, 20/40)의 MACD 선이 모두 상승 추세일 것.
      2. 5/40 MACD의 MACD 선이 0선 위에 있을 것.

    - 롱 청산 로직 (2단계):
      1. (1/2 청산): 5/40 MACD '선'이 정점(Peak)을 찍고 하락으로 전환될 때.
      2. (나머지 청산): 이후, 5/40 MACD 선이 시그널 선을 하향 돌파(데드크로스)할 때.
    """
    params = (
        ('p_fast1', 5),
        ('p_slow1', 20),
        ('p_fast2', 5),
        ('p_slow2', 40),  # 핵심 신호 MACD
        ('p_fast3', 20),
        ('p_slow3', 40),
        ('p_signal', 9),
        ('debug', False),
    )

    def __init__(self):
        # 3개의 MACD 지표 생성
        self.macd_1 = bt.ind.MACD(self.data.close,
                                  period_me1=self.p.p_fast1, period_me2=self.p.p_slow1,
                                  period_signal=self.p.p_signal)
        self.macd_2_main = bt.ind.MACD(self.data.close,
                                       period_me1=self.p.p_fast2, period_me2=self.p.p_slow2,
                                       period_signal=self.p.p_signal)
        self.macd_3 = bt.ind.MACD(self.data.close,
                                  period_me1=self.p.p_fast3, period_me2=self.p.p_slow3,
                                  period_signal=self.p.p_signal)

        # 최종 청산을 위한 5/40 MACD선-시그널선 교차 지표
        self.macd_cross_signal = bt.ind.CrossOver(
            self.macd_2_main.macd, self.macd_2_main.signal)

        # 상태 변수
        self.order = None
        self.position_level = 0  # 0: 무포지션, 1: 1/2 포지션, 2: 풀포지션
        self.peak_detected = False  # MACD 선 피크 감지 플래그

    def _log(self, txt, dt=None):
        if self.p.debug:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'[{dt.isoformat()}] {txt}')

    def notify_order(self, order):
        if order.status in [order.Completed]:
            self.order = None
            if not self.position:  # 포지션이 완전히 청산되면 상태 초기화
                self.position_level = 0
                self.peak_detected = False
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.order = None

    def next(self):
        if self.order:
            return
        # 모든 MACD가 안정적으로 계산될 수 있는 기간 + 추세 판단 1봉
        if len(self.data) < self.p.p_slow2 + self.p.p_signal:
            return

        # TradingView와 동일하게 봉 마감 기준으로만 실행 (리페인트 방지)
        # 현재 봉이 이전 봉보다 작거나 같을 때만 실행 (봉 마감 후)
        if len(self.data) > 1 and self.data.datetime.date(0) <= self.data.datetime.date(-1):
            return

        # 신호 중복 방지: 이미 신호가 발생한 봉인지 확인
        if hasattr(self, 'last_signal_bar') and self.last_signal_bar == len(self.data):
            return

        # --- 1. 진입 조건 계산 ---
        trend_1_rising = self.macd_1.macd[0] > self.macd_1.macd[-1]
        trend_2_rising = self.macd_2_main.macd[0] > self.macd_2_main.macd[-1]
        trend_3_rising = self.macd_3.macd[0] > self.macd_3.macd[-1]
        is_unified_uptrend = trend_1_rising and trend_2_rising and trend_3_rising
        is_macd2_above_zero = self.macd_2_main.macd[0] > 0

        # --- 2. 청산 조건 계산 ---
        # 2-1. [수정] 5/40 'MACD 선'이 피크를 찍고 하락 전환했는가?
        m = self.macd_2_main.macd
        # TradingView와 동일한 로직: 직전 봉이 국소 최대값
        # macd2[2] < macd2[1] > macd2 (이전 < 직전 > 현재)
        is_macd_line_peaked = m[-2] < m[-1] > m[0]

        # 2-2. 5/40 MACD선이 시그널선을 하향 돌파했는가?
        is_macd_cross_down = self.macd_cross_signal[0] < 0

        # --- 3. 매매 실행 로직 ---
        signal_generated = False  # 신호 발생 플래그

        # [진입 로직]
        if not self.position:
            if is_unified_uptrend and is_macd2_above_zero:
                self._log('BUY SIGNAL: All conditions met. Entering FULL Long position.')
                self.order = self.buy()
                self.position_level = 2
                self.peak_detected = False
                signal_generated = True
        
        # [청산 로직]
        elif self.position:
            # [1단계 청산] 풀 포지션 상태에서 MACD 선 피크 첫 감지 시
            if (self.position_level == 2 and is_macd_line_peaked
                    and not self.peak_detected):
                size_to_sell = self.position.size / 2.0
                self._log(f'EXIT-1/2 SIGNAL: MACD Line peak detected. '
                         f'Selling half size: {size_to_sell:.4f}')
                self.order = self.sell(size=size_to_sell)
                self.position_level = 1
                self.peak_detected = True  # 피크 감지를 기록하여 반복 실행 방지
                signal_generated = True

            # [2단계 청산] 포지션 보유 중(1/2 또는 풀포지션) MACD 데드크로스 발생 시
            elif self.position_level > 0 and is_macd_cross_down:
                self._log('EXIT-FINAL SIGNAL: MACD/Signal cross down. '
                         f'Closing remaining position.')
                self.order = self.close()
                signal_generated = True

        # 신호가 발생한 경우 현재 봉을 기록하여 중복 실행 방지
        if signal_generated:
            self.last_signal_bar = len(self.data)


# 여기에 새로운 전략들을 계속 추가할 수 있습니다.
# 예: class RsiStrategy(bt.Strategy): ...