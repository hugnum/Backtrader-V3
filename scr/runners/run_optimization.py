import yaml
import os
from ..core.data import DataFactory
from ..core.engine import BacktestEngine
from ..core import strategies

def main():
    print("--- Running Parameter Optimization ---")

    # 1. 설정 로드
    with open("config/main_config.yaml", 'r') as f:
        config = yaml.safe_load(f)

    common_cfg = config['common']
    opt_cfg = config['optimization']

    # 2. 데이터 준비
    data_factory = DataFactory()
    data_feed = data_factory.get_data_feed(
        symbol=common_cfg['symbol'],
        timeframe=common_cfg['timeframe'],
        start_date=common_cfg['start_date'],
        end_date=common_cfg['end_date']
    )

    # 3. 최적화 엔진 설정 및 실행
    # 최적화는 매 실행마다 새로운 엔진 인스턴스가 필요
    engine = BacktestEngine(config)
    engine.add_data(data_feed)

    strategy_class = getattr(strategies, opt_cfg['strategy'])
    engine.add_optimizer(strategy_class, opt_cfg['params_to_optimize'])

    opt_results = engine.run()

    # 4. 최적화 결과 분석
    print("\n--- Optimization Results ---")
    final_results = []
    for run in opt_results:
        # 각 실행(run)은 전략의 리스트를 포함, 첫 번째 전략의 분석 결과 추출
        analysis = engine.analyze_results(run[0])
        params = run[0].params.__dict__ # 사용된 파라미터 추출
        analysis['params'] = params
        final_results.append(analysis)
    
    # 목표 지표(optimize_target)를 기준으로 정렬
    sorted_results = sorted(final_results, key=lambda x: x[opt_cfg['optimize_target']], reverse=True)

    print(f"Optimization target: {opt_cfg['optimize_target']}")
    print("\n--- Best 5 Results ---")
    for i, res in enumerate(sorted_results[:5]):
        print(f"Rank {i+1}:")
        print(f"  Params: {res['params']}")
        print(f"  {opt_cfg['optimize_target']}: {res[opt_cfg['optimize_target']]:.2f}")
        print(f"  Final Value: {res['final_value']:.2f}, Return: {res['total_return_pct']:.2f}%")
        print("-" * 20)


if __name__ == '__main__':
    main()