import yaml
import os
import pandas as pd
from datetime import timedelta
from ..core.data import DataFactory
from ..core.engine import BacktestEngine
from ..core import strategies

def run_single_wfa_cycle(config, full_data, train_start, train_end, test_start, test_end):
    """워크포워드 분석의 단일 사이클(훈련 -> 검증)을 실행합니다."""
    wf_cfg = config['walk_forward']
    strategy_class = getattr(strategies, wf_cfg['strategy'])
    
    # 1. 훈련(Optimization) 단계
    train_data = full_data.loc[train_start:train_end]
    train_feed = bt.feeds.PandasData(dataname=train_data)
    
    opt_engine = BacktestEngine(config)
    opt_engine.add_data(train_feed)
    opt_engine.add_optimizer(strategy_class, wf_cfg['params_to_optimize'])
    opt_results = opt_engine.run()

    # 훈련 결과에서 최적 파라미터 찾기
    final_results = []
    for run in opt_results:
        analysis = opt_engine.analyze_results(run[0])
        analysis['params'] = run[0].params.__dict__
        final_results.append(analysis)
    
    if not final_results:
        print(f"Warning: Optimization failed for period {train_start} to {train_end}. Skipping.")
        return None

    best_run = sorted(final_results, key=lambda x: x[wf_cfg['optimize_target']], reverse=True)[0]
    best_params = best_run['params']

    # 2. 검증(Out-of-Sample Test) 단계
    test_data = full_data.loc[test_start:test_end]
    test_feed = bt.feeds.PandasData(dataname=test_data)
    
    test_engine = BacktestEngine(config)
    test_engine.add_data(test_feed)
    test_engine.add_strategy(strategy_class, best_params)
    test_results = test_engine.run()
    
    oos_analysis = test_engine.analyze_results(test_results[0])
    oos_analysis['best_params'] = best_params
    return oos_analysis


def main():
    print("--- Running Walk-Forward Analysis ---")

    # 1. 설정 및 전체 데이터 로드
    with open("config/main_config.yaml", 'r') as f:
        config = yaml.safe_load(f)

    common_cfg = config['common']
    wf_cfg = config['walk_forward']
    
    # DataFactory는 피드 객체를 반환하므로, 원본 DataFrame이 필요함
    filepath = f"data/ohlcv/{common_cfg['symbol']}-{common_cfg['timeframe']}.csv"
    full_df = pd.read_csv(filepath, index_col='Date', parse_dates=True)
    full_df = full_df.loc[common_cfg['start_date']:common_cfg['end_date']]

    # 2. 워크포워드 기간 설정
    start_date = full_df.index[0]
    end_date = full_df.index[-1]
    train_delta = timedelta(days=wf_cfg['train_period_days'])
    test_delta = timedelta(days=wf_cfg['test_period_days'])
    
    all_oos_results = []
    
    current_date = start_date
    while current_date + train_delta + test_delta <= end_date:
        train_start = current_date
        train_end = current_date + train_delta
        test_start = train_end + timedelta(days=1)
        test_end = test_start + test_delta
        
        print(f"\n--- WFA Cycle: Train[{train_start.date()}:{train_end.date()}] -> Test[{test_start.date()}:{test_end.date()}] ---")
        
        cycle_result = run_single_wfa_cycle(config, full_df, train_start, train_end, test_start, test_end)
        
        if cycle_result:
            all_oos_results.append(cycle_result)
            print(f"  > OOS Result: Return={cycle_result['total_return_pct']:.2f}%, MDD={cycle_result['max_drawdown_pct']:.2f}%")
            print(f"  > Best Params Found: {cycle_result['best_params']}")

        # 다음 윈도우로 이동 (슬라이딩 윈도우)
        current_date += test_delta

    # 3. 최종 결과 집계
    if not all_oos_results:
        print("Walk-forward analysis could not be completed.")
        return

    results_df = pd.DataFrame(all_oos_results)
    print("\n\n--- Walk-Forward Analysis Final Summary ---")
    print(f"Number of Out-of-Sample Periods: {len(results_df)}")
    print("\n--- Average Performance ---")
    print(results_df[['total_return_pct', 'sharpe_ratio', 'max_drawdown_pct', 'win_rate_pct']].mean())
    print("\n--- Performance Standard Deviation ---")
    print(results_df[['total_return_pct', 'sharpe_ratio', 'max_drawdown_pct', 'win_rate_pct']].std())

    # 결과 저장
    results_path_cfg = config['results_path']
    save_dir = os.path.join(results_path_cfg['base'], results_path_cfg['walk_forward'])
    os.makedirs(save_dir, exist_ok=True)
    results_df.to_csv(os.path.join(save_dir, "wfa_summary.csv"))
    print(f"\nDetailed WFA results saved to {save_dir}/wfa_summary.csv")


if __name__ == '__main__':
    main()