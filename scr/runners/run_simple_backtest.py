import yaml
import os
import sys
import pathlib

# 현재 파일의 상위 디렉토리를 Python 경로에 추가
current_dir = pathlib.Path(__file__).parent.parent.parent
sys.path.insert(0, str(current_dir))

from scr.core.data import DataFactory
from scr.core.engine import BacktestEngine
from scr.core import strategies

def main():
    print("--- Running Simple Backtest ---")

    # 1. 설정 로드
    with open("config/main_config.yaml", 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    common_cfg = config['common']
    simple_cfg = config['simple_backtest']
    results_path_cfg = config['results_path']

    # 2. 데이터 준비
    data_factory = DataFactory()
    data_feed = data_factory.get_data_feed(
        symbol=common_cfg['symbol'],
        timeframe=common_cfg['timeframe'],
        start_date=common_cfg['start_date'],
        end_date=common_cfg['end_date']
    )

    # 3. 백테스트 엔진 설정 및 실행
    engine = BacktestEngine(config)
    engine.add_data(data_feed)

    # 문자열로 된 전략 이름을 실제 클래스로 변환
    strategy_class = getattr(strategies, simple_cfg['strategy'])
    engine.add_strategy(strategy_class, simple_cfg['params'])

    results = engine.run()
    
    # 4. 결과 분석 및 출력
    analysis = engine.analyze_results(results[0])
    print("\n--- Backtest Results ---")
    for key, value in analysis.items():
        if value is not None:
            try:
                print(f"{key}: {value:.2f}")
            except (TypeError, ValueError):
                print(f"{key}: {value}")
        else:
            print(f"{key}: None")

    # 5. 차트 저장 (비활성화)
    # plot_dir = os.path.join(results_path_cfg['base'], results_path_cfg['simple'])
    # os.makedirs(plot_dir, exist_ok=True)
    # plot_filename = f"{common_cfg['symbol']}_{simple_cfg['strategy']}.png"
    # engine.plot(plot_path=os.path.join(plot_dir, plot_filename))


if __name__ == '__main__':
    # 프로젝트 루트에서 python -m src.runners.run_simple_backtest 로 실행
    main()