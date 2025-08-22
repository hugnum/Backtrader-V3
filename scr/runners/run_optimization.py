import yaml
import os
import sys
import pathlib
import glob
import pandas as pd
import backtrader as bt
from datetime import datetime, timedelta
from colorama import init, Fore, Style

# 현재 파일의 상위 디렉토리를 Python 경로에 추가
current_dir = pathlib.Path(__file__).parent.parent.parent
sys.path.insert(0, str(current_dir))

from scr.core.data import DataFactory
from scr.core.engine import BacktestEngine
from scr.core import strategies


def get_available_symbols():
    """data/ohlcv 폴더에서 사용 가능한 종목들을 가져옵니다."""
    data_dir = "data/ohlcv"
    symbols = set()
    
    if os.path.exists(data_dir):
        for file_path in glob.glob(f"{data_dir}/*.csv"):
            filename = os.path.basename(file_path)
            # 파일명에서 종목명 추출 (예: BTCUSDT_1d.csv -> BTCUSDT)
            symbol = filename.split('_')[0]
            symbols.add(symbol)
    
    return sorted(list(symbols))


def get_available_timeframes():
    """사용 가능한 타임프레임을 순서대로 반환합니다."""
    return ['1d', '4h', '1h', '15m', '5m', '3m', '1m']


def get_available_strategies():
    """strategies.py에서 사용 가능한 전략들을 가져옵니다."""
    try:
        # strategies 모듈에서 Strategy 클래스들을 찾기
        strategy_classes = []
        for attr_name in dir(strategies):
            attr = getattr(strategies, attr_name)
            if (isinstance(attr, type) and 
                issubclass(attr, bt.Strategy) and 
                attr != bt.Strategy):
                strategy_classes.append(attr_name)
        
        return sorted(strategy_classes)
    except Exception:
        # 오류 발생 시 기본 전략만 반환
        return ['SmaCrossStrategy']


def select_strategy():
    """전략을 선택합니다."""
    strategies = get_available_strategies()
    
    if not strategies:
        print("❌ 사용 가능한 전략이 없습니다.")
        return 'SmaCrossStrategy'  # 기본값
    
    print(f"\n=== 사용 가능한 전략 ({len(strategies)}개) ===")
    for i, strategy in enumerate(strategies, 1):
        print(f"{i}. {strategy}")
    
    while True:
        try:
            choice = input("\n전략을 선택하세요: ").strip()
            choice_idx = int(choice) - 1
            
            if 0 <= choice_idx < len(strategies):
                selected_strategy = strategies[choice_idx]
                print(f"✅ 선택된 전략: {selected_strategy}")
                return selected_strategy
            else:
                print("❌ 올바른 숫자를 입력해주세요.")
                
        except (ValueError, KeyboardInterrupt):
            if KeyboardInterrupt:
                print("\n\n프로그램을 종료합니다.")
                sys.exit(0)
            print("❌ 올바른 숫자를 입력해주세요.")


def select_config_mode():
    """설정 모드를 선택합니다."""
    print("\n=== 최적화 설정 모드 선택 ===")
    print("1. config 파일 사용 (기본값)")
    print("2. 수동 설정")

    while True:
        try:
            choice = input("\n선택하세요 (1 또는 2, 엔터=기본설정): ").strip()
            if choice == '' or choice == '1':
                return '1'  # 엔터키 또는 1 입력 시 config 파일 사용 (기본값)
            elif choice == '2':
                return '2'  # 2 입력 시 수동 설정
            else:
                print("1, 2 또는 엔터키를 입력해주세요.")
        except KeyboardInterrupt:
            print("\n\n프로그램을 종료합니다.")
            sys.exit(0)


def select_symbols():
    """종목들을 선택합니다."""
    symbols = get_available_symbols()
    
    if not symbols:
        print("❌ data/ohlcv 폴더에 데이터 파일이 없습니다.")
        sys.exit(1)
    
    print(f"\n=== 사용 가능한 종목 ({len(symbols)}개) ===")
    for i, symbol in enumerate(symbols, 1):
        print(f"{i:2d}. {symbol}")
    
    msg1 = "여러 종목을 선택하려면 쉼표(,)로 구분하세요. (예: 1,3,5)"
    msg2 = "전체 선택: 'all'"
    print(f"\n{Fore.YELLOW}{msg1}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{msg2}{Style.RESET_ALL}")
    
    while True:
        try:
            choice = input("\n종목을 선택하세요: ").strip().lower()
            
            if choice == 'all':
                return symbols
            
            # 쉼표로 구분된 선택 처리
            selected_indices = [int(x.strip()) - 1 for x in choice.split(',')]
            selected_symbols = []
            
            for idx in selected_indices:
                if 0 <= idx < len(symbols):
                    selected_symbols.append(symbols[idx])
                else:
                    print(f"❌ 잘못된 선택: {idx + 1}")
                    break
            
            if len(selected_symbols) == len(selected_indices):
                return selected_symbols
            else:
                print("❌ 올바른 숫자를 입력해주세요.")
                
        except (ValueError, KeyboardInterrupt):
            if KeyboardInterrupt:
                print("\n\n프로그램을 종료합니다.")
                sys.exit(0)
            print("❌ 올바른 형식으로 입력해주세요. (예: 1,3,5 또는 all)")


def select_timeframes():
    """타임프레임들을 선택합니다."""
    timeframes = get_available_timeframes()
    
    print("\n=== 타임프레임 선택 ===")
    for i, tf in enumerate(timeframes, 1):
        print(f"{i}. {tf}")
    
    msg1 = "여러 타임프레임을 선택하려면 쉼표(,)로 구분하세요. (예: 1,2,3)"
    msg2 = "전체 선택: 'all'"
    print(f"\n{Fore.YELLOW}{msg1}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{msg2}{Style.RESET_ALL}")
    
    while True:
        try:
            choice = input("\n타임프레임을 선택하세요: ").strip().lower()
            
            if choice == 'all':
                return timeframes
            
            # 쉼표로 구분된 선택 처리
            selected_indices = [int(x.strip()) - 1 for x in choice.split(',')]
            selected_timeframes = []
            
            for idx in selected_indices:
                if 0 <= idx < len(timeframes):
                    selected_timeframes.append(timeframes[idx])
                else:
                    print(f"❌ 잘못된 선택: {idx + 1}")
                    break
            
            if len(selected_timeframes) == len(selected_indices):
                return selected_timeframes
            else:
                print("❌ 올바른 숫자를 입력해주세요.")
                
        except (ValueError, KeyboardInterrupt):
            if KeyboardInterrupt:
                print("\n\n프로그램을 종료합니다.")
                sys.exit(0)
            print("❌ 올바른 형식으로 입력해주세요. (예: 1,2,3 또는 all)")


def select_backtest_period():
    """백테스트 기간을 선택합니다."""
    print("\n=== 백테스트 기간 선택 ===")
    print("1. 전체기간 (데이터 처음부터 끝까지)")
    print("2. 최근 몇일")
    print("3. 특정기간 (시작일 ~ 종료일)")
    print("4. 기본설정 (config 파일 사용)")
    
    while True:
        try:
            choice = input("\n기간 옵션을 선택하세요 (1-4): ").strip()
            
            if choice == '1':
                return {'type': 'full_period'}
            elif choice == '2':
                days = input("최근 몇일을 사용하시겠습니까? (예: 30): ").strip()
                try:
                    days = int(days)
                    if days > 0:
                        return {'type': 'recent_days', 'days': days}
                    else:
                        print("❌ 0보다 큰 숫자를 입력해주세요.")
                        continue
                except ValueError:
                    print("❌ 올바른 숫자를 입력해주세요.")
                    continue
            elif choice == '3':
                start_date = input("시작일을 입력하세요 (YYYY-MM-DD): ").strip()
                end_date = input("종료일을 입력하세요 (YYYY-MM-DD): ").strip()
                
                # 날짜 형식 검증
                try:
                    datetime.strptime(start_date, '%Y-%m-%d')
                    datetime.strptime(end_date, '%Y-%m-%d')
                    return {
                        'type': 'custom_period', 
                        'start_date': start_date, 
                        'end_date': end_date
                    }
                except ValueError:
                    print("❌ 올바른 날짜 형식을 입력해주세요. (YYYY-MM-DD)")
                    continue
            elif choice == '4':
                return {'type': 'default'}
            else:
                print("❌ 1-4 사이의 숫자를 입력해주세요.")
                
        except KeyboardInterrupt:
            print("\n\n프로그램을 종료합니다.")
            sys.exit(0)


def select_optimization_target():
    """최적화 목표를 선택합니다."""
    print("\n=== 최적화 목표 선택 ===")
    print("1. final_value (최종 포트폴리오 가치)")
    print("2. total_return_pct (총 수익률)")
    print("3. sharpe_ratio (샤프 비율)")
    print("4. calmar_ratio (Calmar 비율)")
    print("5. profit_factor (Profit Factor)")
    print("6. win_rate_pct (승률)")
    
    while True:
        try:
            choice = input("\n최적화 목표를 선택하세요 (1-6): ").strip()
            
            if choice == '1':
                return 'final_value'
            elif choice == '2':
                return 'total_return_pct'
            elif choice == '3':
                return 'sharpe_ratio'
            elif choice == '4':
                return 'calmar_ratio'
            elif choice == '5':
                return 'profit_factor'
            elif choice == '6':
                return 'win_rate_pct'
            else:
                print("❌ 1-6 사이의 숫자를 입력해주세요.")
                
        except KeyboardInterrupt:
            print("\n\n프로그램을 종료합니다.")
            sys.exit(0)


def get_strategy_optimization_params(strategy_name):
    """전략별 최적화 파라미터를 반환합니다."""
    if strategy_name == 'SmaCrossStrategy':
        return {
            'fast_ma': (5, 50, 5),      # (시작값, 끝값, 스텝)
            'slow_ma': (20, 100, 10)
        }
    elif strategy_name == 'MACD_LinePeakStrategy':
        return {
            'p_fast1': (3, 10, 1),
            'p_slow1': (15, 30, 5),
            'p_fast2': (3, 10, 1),
            'p_slow2': (30, 60, 10),
            'p_signal': (5, 15, 2)
        }
    elif strategy_name == 'MACD_LinePeakStrategy_v2':
        return {
            'p_fast1': (3, 10, 1),
            'p_slow1': (15, 30, 5),
            'p_fast2': (3, 10, 1),
            'p_slow2': (30, 60, 10),
            'p_signal': (5, 15, 2),
            'risk_pct': (0.5, 2.0, 0.5),
            'atr_mult': (1.5, 3.0, 0.5)
        }
    else:
        # 기본값
        return {
            'fast_ma': (10, 30, 5),
            'slow_ma': (40, 80, 10)
        }


def run_optimization_with_config():
    """config 파일을 사용하여 최적화를 실행합니다."""
    
    try:
        with open("config/main_config.yaml", 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        common_cfg = config['common']
        opt_cfg = config['optimization']
        
        # 다종목, 다중 타임프레임 설정 확인
        if 'symbols' in common_cfg and 'timeframes' in common_cfg:
            print(f"종목: {', '.join(common_cfg['symbols'])}")
            print(f"타임프레임: {', '.join(common_cfg['timeframes'])}")
        else:
            print(f"종목: {common_cfg['symbol']}")
            print(f"타임프레임: {common_cfg['timeframe']}")
        
        print(f"기간: {common_cfg['start_date']} ~ {common_cfg['end_date']}")
        print(f"전략: {opt_cfg['strategy']}")
        print(f"최적화 목표: {opt_cfg['optimize_target']}")
        
        # 다종목, 다중 타임프레임 설정인 경우 config를 확장
        if 'symbols' in common_cfg and 'timeframes' in common_cfg:
            configs = []
            for symbol in common_cfg['symbols']:
                for timeframe in common_cfg['timeframes']:
                    # 각 조합에 대한 개별 config 생성
                    single_config = {
                        'common': {
                            'symbol': symbol,
                            'timeframe': timeframe,
                            'start_date': common_cfg['start_date'],
                            'end_date': common_cfg['end_date'],
                            'initial_cash': common_cfg.get('initial_cash', 1000.0),
                            'commission': common_cfg.get('commission', 0.0015)
                        },
                        'optimization': opt_cfg.copy(),
                        'results_path': config.get('results_path', {})
                    }
                    configs.append(single_config)
            return configs
        else:
            return config
        
    except FileNotFoundError:
        print("❌ config/main_config.yaml 파일을 찾을 수 없습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ config 파일 로드 오류: {e}")
        sys.exit(1)


def run_optimization_manual(symbols, timeframes, period_config, selected_strategy, optimization_target):
    """수동 설정으로 최적화를 실행합니다."""
    print(f"\n=== 수동 설정 최적화 ===")
    print(f"선택된 종목: {', '.join(symbols)}")
    print(f"선택된 타임프레임: {', '.join(timeframes)}")
    print(f"선택된 전략: {selected_strategy}")
    print(f"최적화 목표: {optimization_target}")
    
    # 기간 설정에 따른 시작일과 종료일 결정
    start_date, end_date = get_period_dates(period_config)
    print(f"백테스트 기간: {start_date} ~ {end_date}")
    
    # 전략별 최적화 파라미터 설정
    optimization_params = get_strategy_optimization_params(selected_strategy)
    
    # 모든 조합에 대한 config 리스트 생성
    configs = []
    
    for symbol in symbols:
        for timeframe in timeframes:
            config = {
                'common': {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'start_date': start_date,
                    'end_date': end_date,
                    'initial_cash': 1000.0,
                    'commission': 0.0015
                },
                'optimization': {
                    'strategy': selected_strategy,
                    'params_to_optimize': optimization_params,
                    'optimize_target': optimization_target
                },
                'results_path': {
                    'base': 'results',
                    'simple': 'simple',
                    'optimization': 'optimization',
                    'walk_forward': 'walk_forward'
                }
            }
            configs.append(config)
    
    return configs


def get_period_dates(period_config):
    """기간 설정에 따라 시작일과 종료일을 반환합니다."""
    if period_config['type'] == 'full_period':
        # 전체기간: 데이터의 처음부터 끝까지
        return get_actual_data_period()
    
    elif period_config['type'] == 'recent_days':
        # 최근 몇일
        days = period_config['days']
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
    
    elif period_config['type'] == 'custom_period':
        # 특정기간
        return period_config['start_date'], period_config['end_date']
    
    else:  # default
        # 기본설정: config 파일 사용
        try:
            with open("config/main_config.yaml", 'r', encoding='utf-8') as f:
                config_from_file = yaml.safe_load(f)
            start_date = config_from_file['common']['start_date']
            end_date = config_from_file['common']['end_date']
            return start_date, end_date
        except Exception:
            # config 파일을 읽을 수 없는 경우 기본값 반환
            return '2024-01-01', '2025-01-01'


def get_actual_data_period():
    """실제 데이터 파일에서 사용 가능한 기간을 확인합니다."""
    try:
        # data/ohlcv 폴더에서 첫 번째 CSV 파일을 찾아서 기간 확인
        data_dir = "data/ohlcv"
        if os.path.exists(data_dir):
            csv_files = glob.glob(f"{data_dir}/*.csv")
            if csv_files:
                # 첫 번째 파일로 기간 확인
                sample_file = csv_files[0]
                df = pd.read_csv(sample_file)
                
                if 'timestamp' in df.columns:
                    # timestamp 컬럼을 datetime으로 변환
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    
                    # 시작일과 종료일 추출
                    start_date = df['timestamp'].min().strftime('%Y-%m-%d')
                    end_date = df['timestamp'].max().strftime('%Y-%m-%d')
                    
                    return start_date, end_date
        
        # 기본값 반환 (데이터 파일을 찾을 수 없는 경우)
        return '2024-01-01', '2025-01-01'
        
    except Exception:
        # 오류 발생 시 기본값 반환
        return '2024-01-01', '2025-01-01'


def calculate_cagr(total_return_pct, period_str):
    """연복리 수익률(CAGR)을 계산합니다."""
    try:
        # period 문자열에서 시작일과 종료일 추출
        if '~' in period_str:
            start_date, end_date = period_str.split('~')
            start_date = start_date.strip()
            end_date = end_date.strip()
            
            # 날짜 파싱
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            # 기간 계산 (년 단위)
            years = (end_dt - start_dt).days / 365.25
            
            if years > 0:
                # CAGR 공식: (1 + total_return)^(1/years) - 1
                total_return = total_return_pct / 100
                cagr = ((1 + total_return) ** (1/years) - 1) * 100
                return cagr
            else:
                return total_return_pct
        else:
            # period 정보가 없으면 원래 수익률 반환
            return total_return_pct
            
    except Exception:
        # 오류 발생 시 원래 수익률 반환
        return total_return_pct


def calculate_monthly_trades(total_trades, period_str):
    """월평균 거래수를 계산합니다."""
    try:
        # period 문자열에서 시작일과 종료일을 추출
        if '~' in period_str:
            start_date, end_date = period_str.split('~')
            start_date = start_date.strip()
            end_date = end_date.strip()
            
            # 날짜 파싱
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            # 기간 계산 (월 단위)
            months = (end_dt - start_dt).days / 30.44  # 평균 월 일수
            
            if months > 0:
                # 월평균 거래수 계산
                monthly_trades = total_trades / months
                return monthly_trades
            else:
                return total_trades
        else:
            # period 정보가 없으면 원래 거래수 반환
            return total_trades
            
    except Exception:
        # 오류 발생 시 원래 거래수 반환
        return total_trades


def print_optimization_summary(all_results, target_metric='final_value'):
    """최적화 결과를 상세하고 가독성 좋게 출력합니다."""
    print(f"\n{Fore.CYAN}{Style.BRIGHT}=== 최적화 결과 요약 ==={Style.RESET_ALL}")
    
    if not all_results:
        print("❌ 결과가 없습니다.")
        return
    
    # 유효한 결과만 필터링
    valid_results = [r for r in all_results if target_metric in r and r[target_metric] is not None]
    
    if not valid_results:
        print("❌ 유효한 결과가 없습니다.")
        return
    
    # 결과를 target_metric 기준으로 정렬
    valid_results.sort(key=lambda x: x[target_metric], reverse=True)
    
    # 전체 통계 정보
    total_combinations = len(valid_results)
    profitable_count = len([r for r in valid_results if r.get('total_return_pct', 0) > 0])
    profitable_rate = (profitable_count / total_combinations * 100) if total_combinations > 0 else 0
    
    best_result = valid_results[0] if valid_results else None
    worst_result = valid_results[-1] if valid_results else None
    
    print(f"{Fore.CYAN}📊 전체 통계:{Style.RESET_ALL}")
    print(f"   • 총 테스트 조합: {total_combinations:,}개")
    print(f"   • 수익성 조합: {profitable_count:,}개 ({profitable_rate:.1f}%)")
    if best_result:
        print(f"   • 최고 수익률: {best_result.get('total_return_pct', 0):.2f}%")
        print(f"   • 최고 {target_metric}: {best_result[target_metric]:.2f}")
    if worst_result:
        print(f"   • 최저 수익률: {worst_result.get('total_return_pct', 0):.2f}%")
    
    # 백테스트 기간 정보
    if valid_results and 'period' in valid_results[0]:
        print(f"   • 백테스트 기간: {valid_results[0]['period']}")
    
    print()
    
    # 상위 10개 결과를 상세 테이블로 출력
    print(f"{Fore.YELLOW}{Style.BRIGHT}🏆 {target_metric} 기준 상위 결과:{Style.RESET_ALL}")
    print()
    
    # 헤더 출력
    print(f"{Fore.YELLOW}{Style.BRIGHT}{'Rank':<6} {'Symbol':<10} {'TF':<5} {'Params':<30} {'Return% (CAGR)':>15} {'Sharpe':>8} {'Calmar':>8} {'MDD%':>7} {'Trades':>8} {'Win%':>7} {'PF':>6}{Style.RESET_ALL}")
    print("=" * 120)
    
    # 상위 10개 결과 출력
    top_results = valid_results[:10]
    for rank, result in enumerate(top_results, 1):
        # 기본 정보
        symbol = result.get('symbol', 'N/A')
        timeframe = result.get('timeframe', 'N/A')
        params = result.get('params', {})
        
        # 성과 지표 (안전 처리)
        return_pct = result.get('total_return_pct', 0) or 0
        sharpe = result.get('sharpe_ratio', 0) or 0
        mdd = abs(result.get('max_drawdown_pct', 0) or 0)
        trades = result.get('total_trades', 0) or 0
        win_rate = result.get('win_rate_pct', 0) or 0
        profit_factor = result.get('profit_factor', 0) or 0
        
        # Calmar Ratio 계산
        calmar_ratio = (return_pct / mdd) if mdd > 0 else 0
        
        # CAGR 계산
        period_str = result.get('period', '')
        cagr = calculate_cagr(return_pct, period_str)
        
        # 파라미터 문자열 생성 (간략화)
        if params:
            param_str = ', '.join([f"{k}={v}" for k, v in list(params.items())[:3]])
            if len(params) > 3:
                param_str += "..."
        else:
            param_str = "N/A"
        
        # 파라미터 문자열 길이 제한
        if len(param_str) > 28:
            param_str = param_str[:25] + "..."
        
        # 색상 결정
        color = Fore.GREEN if return_pct > 0 else Fore.RED
        
        # 수익률 표시 형태: 총수익률(CAGR)
        return_cagr_display = f"{return_pct:.1f}({cagr:.1f})"
        
        print(f"{color}{rank:<6} {symbol:<10} {timeframe:<5} {param_str:<30} {return_cagr_display:>14} {sharpe:>8.2f} {calmar_ratio:>8.2f} {mdd:>7.1f}% {trades:>8.0f} {win_rate:>7.1f}% {profit_factor:>6.2f}{Style.RESET_ALL}")
    
    print("=" * 120)
    
    # 최적 파라미터 상세 정보
    if best_result:
        print(f"\n{Fore.GREEN}{Style.BRIGHT}🥇 최적 파라미터 상세 정보:{Style.RESET_ALL}")
        print(f"   • 종목/타임프레임: {best_result.get('symbol', 'N/A')} {best_result.get('timeframe', 'N/A')}")
        print(f"   • 최종 포트폴리오 가치: {best_result[target_metric]:,.2f}")
        print(f"   • 총 수익률: {best_result.get('total_return_pct', 0):.2f}%")
        
        # CAGR 계산 및 표시
        period_str = best_result.get('period', '')
        if period_str:
            cagr = calculate_cagr(best_result.get('total_return_pct', 0), period_str)
            print(f"   • 연복리 수익률(CAGR): {cagr:.2f}%")
        
        print(f"   • Sharpe Ratio: {best_result.get('sharpe_ratio', 0):.2f}")
        mdd_val = abs(best_result.get('max_drawdown_pct', 1))
        calmar_val = (best_result.get('total_return_pct', 0) / mdd_val) if mdd_val > 0 else 0
        print(f"   • Calmar Ratio: {calmar_val:.2f}")
        print(f"   • 최대 낙폭: {mdd_val:.2f}%")
        print(f"   • 총 거래수: {best_result.get('total_trades', 0):.0f}")
        print(f"   • 승률: {best_result.get('win_rate_pct', 0):.1f}%")
        print(f"   • Profit Factor: {best_result.get('profit_factor', 0):.2f}")
        
        # 월평균 거래수 계산
        if period_str:
            monthly_trades = calculate_monthly_trades(best_result.get('total_trades', 0), period_str)
            print(f"   • 월평균 거래수: {monthly_trades:.2f}")
        
        print(f"\n   📋 최적 파라미터:")
        params = best_result.get('params', {})
        if params:
            for key, value in params.items():
                print(f"      - {key}: {value}")
        else:
            print(f"      - 파라미터 정보 없음")


def print_final_analysis_settings(configs):
    """최종 분석 설정을 출력합니다."""
    print(f"\n{Fore.CYAN}{Style.BRIGHT}{'='*60}")
    print(f"📋 Final Analysis Settings")
    print(f"{'='*60}{Style.RESET_ALL}")
    
    if isinstance(configs, dict):
        configs = [configs]
    
    # 첫 번째 config에서 공통 정보 추출
    first_config = configs[0]
    common = first_config['common']
    optimization = first_config['optimization']
    
    # 전략 정보
    strategy_name = optimization['strategy']
    print(f"  - Strategy: {strategy_name}")
    
    # 종목 정보 (첫 번째 config의 symbol만 표시)
    symbol = common['symbol']
    print(f"  - Symbols: {symbol}")
    
    # 타임프레임 정보 (첫 번째 config의 timeframe만 표시)
    timeframe = common['timeframe']
    print(f"  - Timeframes: {timeframe}")
    
    # 기간 정보
    start_date = common['start_date']
    end_date = common['end_date']
    print(f"  - Period: {start_date} ~ {end_date}")
    
    # 레버리지 정보 (기본값 1x)
    leverage = "1x"
    print(f"  - Leverage: {leverage}")
    
    # 최적화 목표
    optimize_target = optimization['optimize_target']
    target_display = {
        'final_value': 'Return Maximization',
        'total_return_pct': 'Return Maximization', 
        'sharpe_ratio': 'Sharpe Ratio Maximization',
        'calmar_ratio': 'Calmar Ratio Maximization',
        'profit_factor': 'Profit Factor Maximization',
        'win_rate_pct': 'Win Rate Maximization'
    }.get(optimize_target, optimize_target)
    
    print(f"  - Objectives: {target_display}")
    
    # 사용자 확인
    print(f"\n{Fore.YELLOW}위 설정으로 최적화를 실행하시겠습니까? (엔터=실행, n=취소): {Style.RESET_ALL}", end="")
    
    while True:
        try:
            confirm = input().strip().lower()
            if confirm == '' or confirm in ['y', 'yes', 'ㅇ']:
                print(f"{Fore.GREEN}✅ 최적화를 시작합니다...{Style.RESET_ALL}")
                return True
            elif confirm in ['n', 'no', 'ㄴ']:
                print(f"{Fore.RED}❌ 최적화를 취소합니다.{Style.RESET_ALL}")
                return False
            else:
                print(f"{Fore.YELLOW}엔터키(실행) 또는 n(취소)를 입력해주세요: {Style.RESET_ALL}", end="")
        except KeyboardInterrupt:
            print(f"\n{Fore.RED}❌ 사용자가 취소했습니다.{Style.RESET_ALL}")
            return False


def execute_optimization(configs):
    """최적화를 실행합니다."""
    if isinstance(configs, dict):
        # 단일 config인 경우
        configs = [configs]
    
    print(f"\n=== 최적화 실행 중... (총 {len(configs)}개 조합) ===")
    
    all_results = []
    
    for i, config in enumerate(configs, 1):
        print(f"\n{Fore.CYAN}[{i}/{len(configs)}] "
              f"{config['common']['symbol']} {config['common']['timeframe']} "
              f"최적화 중...{Style.RESET_ALL}")
        
        try:
            # 데이터 준비
            data_factory = DataFactory()
            data_feed = data_factory.get_data_feed(
                symbol=config['common']['symbol'],
                timeframe=config['common']['timeframe'],
                start_date=config['common']['start_date'],
                end_date=config['common']['end_date']
            )
            
            # 최적화 엔진 설정 및 실행
            engine = BacktestEngine(config)
            engine.add_data(data_feed)
            
            # 전략 추가
            strategy_class = getattr(strategies, 
                                   config['optimization']['strategy'])
            engine.add_optimizer(strategy_class, 
                               config['optimization']['params_to_optimize'])
            
            print("🔄 최적화 실행 중...")
            opt_results = engine.run()
            
            if opt_results:
                print(f"✅ 최적화 완료: {len(opt_results)}개 조합 테스트")
                
                # 최적화 결과 분석
                final_results = []
                for run in opt_results:
                    try:
                        analysis = engine.analyze_results(run[0])
                        params = run[0].params.__dict__
                        analysis['params'] = params
                        analysis['symbol'] = config['common']['symbol']
                        analysis['timeframe'] = config['common']['timeframe']
                        
                        # 백테스트 기간 정보 추가
                        period_str = f"{config['common']['start_date']} ~ {config['common']['end_date']}"
                        analysis['period'] = period_str
                        
                        final_results.append(analysis)
                    except Exception as analyze_error:
                        print(f"⚠️ 결과 분석 실패: {analyze_error}")
                        continue
                
                # 최적화 목표 기준으로 정렬
                optimize_target = config['optimization']['optimize_target']
                sorted_results = sorted(final_results, 
                                      key=lambda x: x.get(optimize_target, 0), 
                                      reverse=True)
                
                # 상위 5개 결과 출력
                print(f"\n🏆 {optimize_target} 기준 상위 5개 결과:")
                for rank, result in enumerate(sorted_results[:5], 1):
                    target_value = result.get(optimize_target, 0)
                    print(f"  Rank {rank}: {target_value:.2f}")
                    print(f"    Params: {result['params']}")
                    print(f"    Return: {result.get('total_return_pct', 0):.2f}%")
                    print(f"    Sharpe: {result.get('sharpe_ratio', 0):.2f}")
                    print("-" * 30)
                
                all_results.extend(sorted_results)
                
            else:
                print("❌ 최적화 결과가 없습니다")
                
        except Exception as e:
            print(f"{Fore.RED}❌ 오류: {e}{Style.RESET_ALL}")
    
    # 전체 결과 요약
    if all_results:
        print(f"\n{Fore.GREEN}=== 전체 최적화 완료 ==={Style.RESET_ALL}")
        print(f"총 {len(all_results)}개 결과 생성")
        
        # 상세한 최적화 결과 테이블 출력
        if configs and len(configs) > 0:
            optimize_target = configs[0]['optimization']['optimize_target']
            print_optimization_summary(all_results, optimize_target)
    else:
        print(f"\n{Fore.RED}❌ 최적화 결과가 없습니다{Style.RESET_ALL}")


def main():
    # colorama 초기화
    init(autoreset=True)
    
    print("🚀 Backtrader-V3 대화형 최적화 시스템")
    print("=" * 50)
    
    # 1. 설정 모드 선택
    mode = select_config_mode()
    
    if mode == '1':
        # config 파일 사용
        config = run_optimization_with_config()
    else:
        # 수동 설정
        selected_strategy = select_strategy()
        symbols = select_symbols()
        timeframes = select_timeframes()
        period_config = select_backtest_period()
        optimization_target = select_optimization_target()
        configs = run_optimization_manual(symbols, timeframes, 
                                        period_config, selected_strategy, 
                                        optimization_target)
    
    # 2. 최종 설정 확인 및 최적화 실행
    if mode == '1':
        # config 파일 사용 시
        if print_final_analysis_settings(config):
            execute_optimization(config)
        else:
            return
    else:
        # 수동 설정 시
        if print_final_analysis_settings(configs):
            execute_optimization(configs)
        else:
            return
    
    print(f"\n{Fore.GREEN}✅ 최적화가 완료되었습니다!{Style.RESET_ALL}")


if __name__ == '__main__':
    main()