"""
過去データスクレイピング - コマンドラインインターフェース
日付範囲を柔軟に指定できるようにする
"""
import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta
import os

# appディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.data_scraper import (
    scrape_date_range_from_calendar,
    scrape_date_range,
    scrape_date_range_from_config,
    scrape_last_week,
    get_request_status
)

def parse_date(date_str):
    """
    日付文字列を解析
    
    サポート形式:
    - YYYY-MM-DD (例: 2025-12-06)
    - YYYYMMDD (例: 20251206)
    - 相対日付: -Ndays, +Ndays (例: -7days, +30days)
    - today, yesterday, last_week, last_month
    
    Args:
        date_str: 日付文字列
    
    Returns:
        datetime.date: 日付オブジェクト
    """
    today = datetime.now().date()
    
    # 相対日付の処理
    if date_str == 'today':
        return today
    elif date_str == 'yesterday':
        return today - timedelta(days=1)
    elif date_str == 'last_week':
        return today - timedelta(days=7)
    elif date_str == 'last_month':
        return today - timedelta(days=30)
    elif date_str.endswith('days'):
        # -Ndays または +Ndays形式
        try:
            # 'days'を除いた部分を取得
            number_part = date_str[:-4]  # 'days'の4文字を除く
            if number_part.startswith('-'):
                days = int(number_part[1:])  # '-'を除いた数字部分
                return today - timedelta(days=days)
            elif number_part.startswith('+'):
                days = int(number_part[1:])  # '+'を除いた数字部分
                return today + timedelta(days=days)
            else:
                # 符号がない場合は正の数として扱う
                days = int(number_part)
                return today + timedelta(days=days)
        except ValueError:
            raise ValueError(f"無効な日付形式: {date_str}")
    
    # YYYY-MM-DD形式
    if len(date_str) == 10 and date_str.count('-') == 2:
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            raise ValueError(f"無効な日付形式: {date_str}")
    
    # YYYYMMDD形式
    if len(date_str) == 8 and date_str.isdigit():
        try:
            return datetime.strptime(date_str, '%Y%m%d').date()
        except ValueError:
            raise ValueError(f"無効な日付形式: {date_str}")
    
    raise ValueError(f"無効な日付形式: {date_str}")

def parse_month(month_str):
    """
    月指定文字列を解析
    
    サポート形式:
    - YYYY-MM (例: 2025-12)
    - YYYY/MM (例: 2025/12)
    - YYYYMM (例: 202512)
    
    Args:
        month_str: 月指定文字列
    
    Returns:
        tuple: (year, month)
    """
    # YYYY-MM形式
    if len(month_str) == 7 and month_str.count('-') == 1:
        try:
            year, month = month_str.split('-')
            return int(year), int(month)
        except ValueError:
            raise ValueError(f"無効な月形式: {month_str}")
    
    # YYYY/MM形式
    if len(month_str) == 7 and month_str.count('/') == 1:
        try:
            year, month = month_str.split('/')
            return int(year), int(month)
        except ValueError:
            raise ValueError(f"無効な月形式: {month_str}")
    
    # YYYYMM形式
    if len(month_str) == 6 and month_str.isdigit():
        try:
            year = int(month_str[:4])
            month = int(month_str[4:6])
            return year, month
        except ValueError:
            raise ValueError(f"無効な月形式: {month_str}")
    
    raise ValueError(f"無効な月形式: {month_str}")

def main():
    parser = argparse.ArgumentParser(
        description='過去データスクレイピング - 日付範囲を柔軟に指定',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
日付指定の例:
  日付範囲指定:
    --start-date 2025-12-01 --end-date 2025-12-07
    --start-date -7days --end-date yesterday
    --start-date 20251201 --end-date 20251207
  
  年月範囲指定（カレンダー方式）:
    --start-month 2025-11 --end-month 2025-12
    --start-month 2025/11 --end-month 2025/12
    --start-year 2025 --start-month 11 --end-year 2025 --end-month 12
  
  相対日付指定:
    --start-date -30days --end-date -1days  (過去30日間)
    --start-date last_week --end-date yesterday  (先週から昨日まで)
    --start-date -7days --end-date today  (過去7日間)
  
  環境変数での指定:
    export SCRAPER_START_DATE=2025-12-01
    export SCRAPER_END_DATE=2025-12-07
    python data_scraper_cli.py
  
  設定ファイル優先:
    config.jsonのscraper設定が優先されます
        """
    )
    
    # 日付範囲指定（直接日付）
    parser.add_argument(
        '--start-date',
        type=str,
        help='開始日 (YYYY-MM-DD, YYYYMMDD, -Ndays, +Ndays, today, yesterday, last_week, last_month)'
    )
    parser.add_argument(
        '--end-date',
        type=str,
        help='終了日 (YYYY-MM-DD, YYYYMMDD, -Ndays, +Ndays, today, yesterday, last_week, last_month)'
    )
    
    # 年月範囲指定（カレンダー方式）
    parser.add_argument(
        '--start-month',
        type=str,
        help='開始月 (YYYY-MM, YYYY/MM, YYYYMM)'
    )
    parser.add_argument(
        '--end-month',
        type=str,
        help='終了月 (YYYY-MM, YYYY/MM, YYYYMM)'
    )
    
    # 年月個別指定（カレンダー方式）
    parser.add_argument(
        '--start-year',
        type=int,
        help='開始年'
    )
    parser.add_argument(
        '--start-month-num',
        type=int,
        help='開始月（1-12）',
        dest='start_month_num'
    )
    parser.add_argument(
        '--end-year',
        type=int,
        help='終了年'
    )
    parser.add_argument(
        '--end-month-num',
        type=int,
        help='終了月（1-12）',
        dest='end_month_num'
    )
    
    # オプション
    parser.add_argument(
        '--no-horses',
        action='store_true',
        help='馬データを取得しない'
    )
    parser.add_argument(
        '--no-peds',
        action='store_true',
        help='血統データを取得しない'
    )
    parser.add_argument(
        '--include-today',
        action='store_true',
        help='今日の日付も含める（デフォルトはスキップ）'
    )
    parser.add_argument(
        '--use-config',
        action='store_true',
        help='config.jsonの設定を優先して使用'
    )
    parser.add_argument(
        '--last-week',
        action='store_true',
        help='先週のデータを取得（テスト用）'
    )
    
    args = parser.parse_args()
    
    # リクエスト状態を確認
    status = get_request_status()
    print("="*80)
    print("過去データスクレイピング開始")
    print("="*80)
    print(f"\n現在のリクエスト状態:")
    print(f"  使用済み: {status['count']}回")
    print(f"  残り: {status['remaining']}回")
    if 'type' in status:
        print(f"  日付タイプ: {status['type']}")
    
    if status['remaining'] <= 0:
        print("\n[警告] 1日のリクエスト上限に達しています。処理を中断します。")
        sys.exit(1)
    
    print("\n[注意] スクレイピングには時間がかかります:")
    print("  - 各リクエスト間に1.5秒の待機時間があります（スクレイピング対策）")
    print("  - 10月・11月のデータ取得には数時間かかる可能性があります")
    print("  - 進捗状況は随時表示されます")
    
    # オプションの処理
    scrape_horses = not args.no_horses
    scrape_peds = not args.no_peds
    skip_today = not args.include_today
    
    # config.jsonを優先する場合
    if args.use_config:
        print("\n[設定] config.jsonの設定を使用します")
        stats = scrape_date_range_from_config()
    # 先週のデータを取得
    elif args.last_week:
        print("\n[設定] 先週のデータを取得します")
        stats = scrape_last_week()
    # 年月範囲指定（カレンダー方式）
    elif args.start_month and args.end_month:
        try:
            start_year, start_month = parse_month(args.start_month)
            end_year, end_month = parse_month(args.end_month)
            print(f"\n[設定] カレンダー方式: {start_year}年{start_month}月 ～ {end_year}年{end_month}月")
            stats = scrape_date_range_from_calendar(
                start_year, start_month,
                end_year, end_month,
                scrape_horses=scrape_horses,
                scrape_peds=scrape_peds
            )
        except ValueError as e:
            print(f"\n[エラー] {e}")
            sys.exit(1)
    # 年月個別指定（カレンダー方式）
    elif args.start_year and args.start_month_num and args.end_year and args.end_month_num:
        print(f"\n[設定] カレンダー方式: {args.start_year}年{args.start_month_num}月 ～ {args.end_year}年{args.end_month_num}月")
        stats = scrape_date_range_from_calendar(
            args.start_year, args.start_month_num,
            args.end_year, args.end_month_num,
            scrape_horses=scrape_horses,
            scrape_peds=scrape_peds
        )
    # 日付範囲指定
    elif args.start_date and args.end_date:
        try:
            start_date = parse_date(args.start_date)
            end_date = parse_date(args.end_date)
            
            if start_date > end_date:
                print(f"\n[エラー] 開始日が終了日より後です: {start_date} > {end_date}")
                sys.exit(1)
            
            print(f"\n[設定] 日付範囲: {start_date} ～ {end_date}")
            stats = scrape_date_range(
                start_date, end_date,
                scrape_horses=scrape_horses,
                scrape_peds=scrape_peds,
                skip_today=skip_today
            )
        except ValueError as e:
            print(f"\n[エラー] {e}")
            sys.exit(1)
    # 環境変数から取得
    elif os.getenv('SCRAPER_START_DATE') and os.getenv('SCRAPER_END_DATE'):
        try:
            start_date = parse_date(os.getenv('SCRAPER_START_DATE'))
            end_date = parse_date(os.getenv('SCRAPER_END_DATE'))
            
            if start_date > end_date:
                print(f"\n[エラー] 開始日が終了日より後です: {start_date} > {end_date}")
                sys.exit(1)
            
            print(f"\n[設定] 環境変数から取得: {start_date} ～ {end_date}")
            stats = scrape_date_range(
                start_date, end_date,
                scrape_horses=scrape_horses,
                scrape_peds=scrape_peds,
                skip_today=skip_today
            )
        except ValueError as e:
            print(f"\n[エラー] {e}")
            sys.exit(1)
    # 環境変数から年月取得
    elif os.getenv('SCRAPER_START_MONTH') and os.getenv('SCRAPER_END_MONTH'):
        try:
            start_year, start_month = parse_month(os.getenv('SCRAPER_START_MONTH'))
            end_year, end_month = parse_month(os.getenv('SCRAPER_END_MONTH'))
            print(f"\n[設定] 環境変数から取得（カレンダー方式）: {start_year}年{start_month}月 ～ {end_year}年{end_month}月")
            stats = scrape_date_range_from_calendar(
                start_year, start_month,
                end_year, end_month,
                scrape_horses=scrape_horses,
                scrape_peds=scrape_peds
            )
        except ValueError as e:
            print(f"\n[エラー] {e}")
            sys.exit(1)
    # デフォルト: config.jsonから取得
    else:
        print("\n[設定] 引数が指定されていません。config.jsonの設定を使用します")
        stats = scrape_date_range_from_config()
    
    # 結果表示
    print("\n" + "="*80)
    print("スクレイピング結果")
    print("="*80)
    print(f"処理した日数: {stats['dates_processed']}")
    print(f"処理したレース数: {stats['races_processed']}")
    print(f"成功したレース数: {stats['races_success']}")
    print(f"スキップしたレース数: {stats['races_skipped']}")
    print(f"処理した馬数: {stats['horses_processed']}")
    print(f"成功した馬数: {stats['horses_success']}")
    print(f"スキップした馬数: {stats['horses_skipped']}")
    print(f"処理した血統数: {stats['peds_processed']}")
    print(f"成功した血統数: {stats['peds_success']}")
    print(f"スキップした血統数: {stats['peds_skipped']}")
    
    # 最終的なリクエスト状態
    final_status = get_request_status()
    print(f"\n最終リクエスト状態:")
    print(f"  使用済み: {final_status['count']}回")
    print(f"  残り: {final_status['remaining']}回")

if __name__ == '__main__':
    main()

