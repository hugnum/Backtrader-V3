import backtrader as bt

class BacktestEngine:
    def __init__(self, config):
        self.config = config
        self.cerebro = bt.Cerebro()

    def add_data(self, data_feed):
        self.cerebro.adddata(data_feed)

    def add_strategy(self, strategy_class, params):
        self.cerebro.addstrategy(strategy_class, **params)

    def add_optimizer(self, strategy_class, params_to_optimize):
        # params_to_optimize의 값들을 range로 변환
        opt_params = {k: range(*v) if isinstance(v, list) and len(v) == 3 else v
                      for k, v in params_to_optimize.items()}
        self.cerebro.optstrategy(strategy_class, **opt_params)

    def run(self):
        """단순 백테스트 또는 최적화를 실행합니다."""
        common_cfg = self.config['common']
        self.cerebro.broker.setcash(common_cfg['initial_cash'])
        self.cerebro.broker.setcommission(commission=common_cfg['commission'])

        # Sizer 추가: 사용 가능한 현금의 95%를 사용하여 자동으로 매수 수량을 계산
        self.cerebro.addsizer(bt.sizers.PercentSizer, percents=95)

        # 분석기 추가
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe_ratio')
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        self.cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade_analyzer')

        results = self.cerebro.run()
        return results

    def analyze_results(self, strategy_result):
        """실행된 전략의 결과를 분석하고 딕셔너리로 반환합니다."""
        analyzers = strategy_result.analyzers
        final_value = self.cerebro.broker.getvalue()
        initial_cash = self.config['common']['initial_cash']

        # 각 분석기에서 결과 추출
        sharpe = analyzers.sharpe_ratio.get_analysis()
        drawdown = analyzers.drawdown.get_analysis()
        returns = analyzers.returns.get_analysis()
        trade_info = analyzers.trade_analyzer.get_analysis()

        analysis = {
            'symbol': self.config['common']['symbol'],
            'period': f"{self.config['common']['start_date']} ~ {self.config['common']['end_date']}",
            'initial_value': initial_cash,
            'final_value': final_value,
            'total_return_pct': (final_value / initial_cash - 1) * 100,
            'sharpe_ratio': sharpe.get('sharperatio', 0),
            'max_drawdown_pct': drawdown.get('max', {}).get('drawdown', 0),
            'total_trades': trade_info.get('total', {}).get('total', 0),
            'win_rate_pct': (trade_info.get('won', {}).get('total', 0) / trade_info.get('total', {}).get('total', 1)) * 100 if trade_info.get('total', {}).get('total', 0) > 0 else 0
        }
        return analysis

    def plot(self, plot_path=None):
        """결과 차트를 그리고, 지정된 경로에 저장합니다."""
        fig = self.cerebro.plot(style='candlestick', barup='green', bardown='red')[0][0]
        if plot_path:
            fig.savefig(plot_path, dpi=300)
            print(f"Plot saved to {plot_path}")
        # plt.show() # 로컬에서 바로 보고 싶을 때 주석 해제