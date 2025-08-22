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
    print("\n=== 백테스트 설정 모드 선택 ===")
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


def run_backtest_with_config():
    """config 파일을 사용하여 백테스트를 실행합니다."""
    print("\n=== config 파일을 사용한 백테스트 ===")
    
    try:
        with open("config/main_config.yaml", 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        common_cfg = config['common']
        simple_cfg = config['simple_backtest']
        
        # 다종목, 다중 타임프레임 설정 확인
        if 'symbols' in common_cfg and 'timeframes' in common_cfg:
            print(f"다종목: {', '.join(common_cfg['symbols'])}")
            print(f"다중 타임프레임: {', '.join(common_cfg['timeframes'])}")
            print(f"기간: {common_cfg['start_date']} ~ {common_cfg['end_date']}")
            print(f"전략: {simple_cfg['strategy']}")
            
            # 모든 조합에 대한 config 리스트 생성
            configs = []
            for symbol in common_cfg['symbols']:
                for timeframe in common_cfg['timeframes']:
                    # 기존 config를 복사하고 symbol, timeframe만 변경
                    config_copy = config.copy()
                    config_copy['common'] = config_copy['common'].copy()
                    config_copy['common']['symbol'] = symbol
                    config_copy['common']['timeframe'] = timeframe
                    configs.append(config_copy)
            
            return configs
        else:
            # 기존 단일 설정 사용
            print(f"종목: {common_cfg['symbol']}")
            print(f"타임프레임: {common_cfg['timeframe']}")
            print(f"기간: {common_cfg['start_date']} ~ {common_cfg['end_date']}")
            print(f"전략: {simple_cfg['strategy']}")
            
            return config
        
    except FileNotFoundError:
        print("❌ config/main_config.yaml 파일을 찾을 수 없습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ config 파일 로드 오류: {e}")
        sys.exit(1)


def run_backtest_manual(symbols, timeframes, period_config, selected_strategy):
    """수동 설정으로 백테스트를 실행합니다."""
    print(f"\n=== 수동 설정 백테스트 ===")
    print(f"선택된 종목: {', '.join(symbols)}")
    print(f"선택된 타임프레임: {', '.join(timeframes)}")
    print(f"선택된 전략: {selected_strategy}")
    
    # 기간 설정에 따른 시작일과 종료일 결정
    start_date, end_date = get_period_dates(period_config)
    print(f"백테스트 기간: {start_date} ~ {end_date}")
    
    # 전략별 기본 파라미터 설정
    strategy_params = get_strategy_default_params(selected_strategy)
    
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
                'simple_backtest': {
                    'strategy': selected_strategy,
                    'params': strategy_params
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


def get_strategy_default_params(strategy_name):
    """전략별 기본 파라미터를 반환합니다."""
    if strategy_name == 'SmaCrossStrategy':
        return {
            'fast_ma': 20,
            'slow_ma': 50
        }
    elif strategy_name == 'MACD_LinePeakStrategy':
        return {
            'p_fast1': 5,
            'p_slow1': 20,
            'p_fast2': 5,
            'p_slow2': 40,
            'p_fast3': 20,
            'p_slow3': 40,
            'p_signal': 9,
            'debug': True
        }
    elif strategy_name == 'MACD_LinePeakStrategy_v2':
        return {
            'p_fast1': 5,
            'p_slow1': 20,
            'p_fast2': 5,
            'p_slow2': 40,
            'p_fast3': 20,
            'p_slow3': 40,
            'p_signal': 9,
            # 리스크 관리 파라미터
            'risk_pct': 1.0,        # 거래당 1% 리스크
            'sl_mode': 'ATR',       # ATR 기반 스톱로스
            'atr_len': 14,          # ATR 14기간
            'atr_mult': 2.0,        # ATR 2배수
            'sl_percent': 1.5,      # 1.5% 퍼센트 스톱로스
            'sl_ticks': 50,         # 50틱 스톱로스
            'min_qty': 0.0001,      # 최소 주문량
            'debug': True
        }
    else:
        # 기본값
        return {}


def get_period_dates(period_config):
    """기간 설정에 따라 시작일과 종료일을 반환합니다."""
    if period_config['type'] == 'full_period':
        # 전체기간: 데이터의 처음부터 끝까지
        # 실제 데이터 파일에서 시작일과 종료일을 확인
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


def execute_backtest(configs):
    """백테스트를 실행합니다."""
    if isinstance(configs, dict):
        # 단일 config인 경우
        configs = [configs]
    
    print(f"\n=== 백테스트 실행 중... (총 {len(configs)}개 조합) ===")
    
    all_results = []
    
    for i, config in enumerate(configs, 1):
        print(f"\n{Fore.CYAN}[{i}/{len(configs)}] {config['common']['symbol']} {config['common']['timeframe']} 실행 중...{Style.RESET_ALL}")
        
        try:
            # 데이터 준비
            data_factory = DataFactory()
            data_feed = data_factory.get_data_feed(
                symbol=config['common']['symbol'],
                timeframe=config['common']['timeframe'],
                start_date=config['common']['start_date'],
                end_date=config['common']['end_date']
            )
            
            # 백테스트 엔진 설정 및 실행
            engine = BacktestEngine(config)
            engine.add_data(data_feed)

            # config 구조 디버깅
            print("🔍 Config 구조 확인:")
            print(f"   - common keys: {list(config.get('common', {}).keys())}")
            print(f"   - simple_backtest keys: "
                  f"{list(config.get('simple_backtest', {}).keys())}")
            
            # 전략 추가 (안전하게)
            try:
                if 'strategy' in config.get('common', {}):
                    strategy_name = config['common']['strategy']
                elif 'strategy' in config.get('simple_backtest', {}):
                    strategy_name = config['simple_backtest']['strategy']
                else:
                    print("❌ Config에 strategy 정보가 없습니다")
                    strategy_name = 'SmaCrossStrategy'  # 기본값
                
                print(f"🎯 사용할 전략: {strategy_name}")
                strategy_class = getattr(strategies, strategy_name)
                engine.add_strategy(strategy_class, 
                                 config['simple_backtest']['params'])
                print("✅ 전략 추가 완료")
            except Exception as strategy_error:
                print(f"❌ 전략 추가 실패: {strategy_error}")
                raise strategy_error
            
            # 백테스트 실행
            print("🔄 백테스트 실행 중...")
            try:
                results = engine.run()
                print("✅ engine.run() 완료")
            except Exception as run_error:
                print(f"❌ engine.run() 실패: {run_error}")
                results = None
            
            # 디버깅: results 상태 확인
            print(f"📊 Results 타입: {type(results)}")
            print(f"📊 Results 길이: {len(results) if results else 'None'}")
            if results and len(results) > 0:
                print(f"📊 First result 타입: {type(results[0])}")
                print(f"📊 First result 내용: {results[0]}")
            else:
                print("❌ Results가 비어있거나 None입니다")
            
            # 결과 분석
            if results and len(results) > 0:
                try:
                    analysis = engine.analyze_results(results[0])
                    print("✅ 결과 분석 완료")
                except Exception as analyze_error:
                    print(f"❌ 결과 분석 실패: {analyze_error}")
                    # 기본 분석 결과 생성
                    analysis = {
                        'symbol': config['common']['symbol'],
                        'timeframe': config['common']['timeframe'],
                        'error': f"분석 실패: {analyze_error}"
                    }
            else:
                print("❌ 백테스트 결과가 없습니다")
                analysis = {
                    'symbol': config['common']['symbol'],
                    'timeframe': config['common']['timeframe'],
                    'error': "백테스트 결과 없음"
                }
            
            # period 정보와 strategy 정보 추가
            period_str = f"{config['common']['start_date']} ~ {config['common']['end_date']}"
            analysis['period'] = period_str
            
            # strategy 정보 추가 (안전하게)
            try:
                if 'strategy' in config['simple_backtest']:
                    analysis['strategy'] = config['simple_backtest']['strategy']
                elif 'strategy' in config['common']:
                    analysis['strategy'] = config['common']['strategy']
                else:
                    analysis['strategy'] = 'Unknown Strategy'
            except Exception as strategy_error:
                print(f"⚠️ Strategy 정보 추가 실패: {strategy_error}")
                analysis['strategy'] = 'Unknown Strategy'
            
            all_results.append(analysis)
            
            print(f"{Fore.GREEN}✅ 완료{Style.RESET_ALL}")
                
        except Exception as e:
            print(f"{Fore.RED}❌ 오류: {e}{Style.RESET_ALL}")
            # 오류 발생 시 기본 결과 추가
            all_results.append({
                'symbol': config['common']['symbol'],
                'timeframe': config['common']['timeframe'],
                'error': str(e)
            })
    
    # 모든 결과를 테이블 형태로 출력
    print_comparison_table(all_results)


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


def print_comparison_table(all_results):
    """여러 백테스트 결과를 비교 테이블로 출력합니다."""
    print(f"\n{Fore.CYAN}{Style.BRIGHT}=== 백테스트 결과 비교 ==={Style.RESET_ALL}")
    
    if not all_results:
        print("❌ 결과가 없습니다.")
        return
    
    # 오류가 없는 결과만 필터링하고 종목명으로 정렬
    valid_results = [r for r in all_results if 'error' not in r]
    valid_results.sort(key=lambda x: x.get('symbol', ''))
    
    # 전략 이름 출력
    if all_results and len(all_results) > 0:
        first_result = all_results[0]
        if 'strategy' in first_result:
            print(f"{Fore.CYAN}📊 전략: {first_result['strategy']}{Style.RESET_ALL}")
        else:
            # strategy가 없는 경우 config에서 직접 가져오기
            try:
                with open("config/main_config.yaml", 'r', encoding='utf-8') as f:
                    config_from_file = yaml.safe_load(f)
                strategy = config_from_file['simple_backtest']['strategy']
                print(f"{Fore.CYAN}📊 전략: {strategy}{Style.RESET_ALL}")
            except Exception:
                pass

    # 백테스트 기간 정보를 먼저 표시
    if all_results and len(all_results) > 0:
        first_result = all_results[0]
        if 'period' in first_result:
            print(f"{Fore.CYAN}📅 백테스트 기간: {first_result['period']}{Style.RESET_ALL}")
        else:
            # period가 없는 경우 config에서 직접 가져오기
            try:
                with open("config/main_config.yaml", 'r', encoding='utf-8') as f:
                    config_from_file = yaml.safe_load(f)
                start_date = config_from_file['common']['start_date']
                end_date = config_from_file['common']['end_date']
                print(f"{Fore.CYAN}📅 백테스트 기간: {start_date} ~ {end_date}{Style.RESET_ALL}")
            except Exception:
                pass
    
    print()  # 빈 줄 추가
    
    # 헤더 출력 (컬럼 너비 최적화 + 오른쪽으로 5칸 이동)
    print(f"     {Fore.YELLOW}{Style.BRIGHT}{'Symbol':<10} {'TF':<5} {'Calmar':>8} {'Return% (CAGR)':>15} {'MDD%':>7} {'Trades(월평균)':>15} {'Win%':>7} {'PF':>6} {'Sharpe':>8}{Style.RESET_ALL}")
    print("     " + "=" * 100)
    
    # 각 결과 출력
    for result in valid_results:
        # 정상 결과 (None 값 안전 처리)
        symbol = result.get('symbol', 'N/A')
        timeframe = result.get('timeframe', 'N/A')
        return_pct = result.get('total_return_pct', 0) or 0
        sharpe = result.get('sharpe_ratio', 0) or 0
        mdd = result.get('max_drawdown_pct', 0) or 0
        trades = result.get('total_trades', 0) or 0
        win_rate = result.get('win_rate_pct', 0) or 0
        profit_factor = result.get('profit_factor', 0) or 0
        
        # Calmar Ratio 계산 (수익률 / 최대낙폭) - 안전 처리
        calmar_ratio = (return_pct / abs(mdd)) if mdd and mdd != 0 else 0
        
        # 색상 결정
        color = Fore.GREEN if return_pct and return_pct > 0 else Fore.RED
        
        # CAGR(연복리 수익률) 계산
        cagr = calculate_cagr(return_pct, result.get('period', ''))
        
        # 월평균 거래수 계산
        monthly_trades = calculate_monthly_trades(trades, result.get('period', ''))
        
        # 가독성 향상을 위한 포맷팅 (총수익률(CAGR) 형태, 총거래수(월거래수) 형태)
        return_cagr_display = f"{return_pct:.1f}({cagr:.1f})"
        trades_display = f"{trades:.0f}({monthly_trades:.2f})"
        print(f"     {color}{symbol:<10} {timeframe:<5} {calmar_ratio:>8.2f} {return_cagr_display:>14} {mdd:>7.1f}% {trades_display:>14} {win_rate:>7.1f}% {profit_factor:>6.2f} {sharpe:>8.2f}{Style.RESET_ALL}")
    
    # 오류가 있는 결과도 표시
    error_results = [r for r in all_results if 'error' in r]
    if error_results:
        print("     " + "-" * 90)
        for result in error_results:
            print(f"     {Fore.RED}{result['symbol']:<10} {result['timeframe']:<5} {'ERROR':>8} {'':>9} {'':>7} {'':>8} {'':>7} {'':>6} {'':>8}{Style.RESET_ALL}")
    
    print("     " + "=" * 90)





def main():
    # colorama 초기화
    init(autoreset=True)
    
    print("🚀 Backtrader-V3 대화형 백테스트 시스템")
    print("=" * 50)
    
    # 1. 설정 모드 선택
    mode = select_config_mode()
    
    if mode == '1':
        # config 파일 사용
        config = run_backtest_with_config()
    else:
        # 수동 설정
        selected_strategy = select_strategy()
        symbols = select_symbols()
        timeframes = select_timeframes()
        period_config = select_backtest_period()
        configs = run_backtest_manual(symbols, timeframes, period_config, selected_strategy)
    
    # 2. 백테스트 실행
    if mode == '1':
        execute_backtest(config)
    else:
        execute_backtest(configs)
    
    print(f"\n{Fore.GREEN}✅ 백테스트가 완료되었습니다!{Style.RESET_ALL}")


if __name__ == '__main__':
    main()