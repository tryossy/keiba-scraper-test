"""
競馬データ月次スクレイピングスクリプト（ローカルスクレイパー使用）

既存の app/data_scraper_cli.py を使用して月次データを取得します。

使用方法:
    python scrape_monthly_local.py --year-month 2024-12
"""
import argparse
import sys
import subprocess
from datetime import datetime, timedelta
from pathlib import Path


def get_month_date_range(year: int, month: int):
    """
    指定月の開始日と終了日を取得

    Args:
        year: 年（例: 2024）
        month: 月（例: 12）

    Returns:
        tuple: (start_date, end_date) の文字列（例: ('20241201', '20241231')）
    """
    first_day = datetime(year, month, 1)

    # 月の最終日を取得
    if month == 12:
        last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = datetime(year, month + 1, 1) - timedelta(days=1)

    start_date = first_day.strftime('%Y%m%d')
    end_date = last_day.strftime('%Y%m%d')

    return start_date, end_date


def run_scraper(start_date: str, end_date: str):
    """
    app/data_scraper_cli.py を実行してスクレイピング

    Args:
        start_date: 開始日（例: '20241201'）
        end_date: 終了日（例: '20241231'）

    Returns:
        int: 終了コード（0=成功、1=失敗）
    """
    # data_scraper_cli.py のパスを確認
    scraper_path = Path('app/data_scraper_cli.py')

    if not scraper_path.exists():
        print(f"エラー: {scraper_path} が見つかりません")
        print("このスクリプトはリポジトリのルートディレクトリから実行してください")
        return 1

    # スクレイピングコマンドを実行
    cmd = [
        sys.executable,
        str(scraper_path),
        '--start-date', start_date,
        '--end-date', end_date
    ]

    print(f"\n{'='*80}")
    print(f"スクレイピング実行: {start_date} ~ {end_date}")
    print(f"コマンド: {' '.join(cmd)}")
    print(f"{'='*80}\n")

    try:
        result = subprocess.run(
            cmd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8'
        )

        # 出力を表示
        print(result.stdout)

        if result.returncode == 0:
            print(f"\n{'='*80}")
            print("スクレイピング完了")
            print(f"{'='*80}")
        else:
            print(f"\n{'='*80}")
            print(f"スクレイピング失敗（終了コード: {result.returncode}）")
            print(f"{'='*80}")

        return result.returncode

    except Exception as e:
        print(f"\nエラー: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description='競馬データ月次スクレイピング（ローカルスクレイパー使用）'
    )
    parser.add_argument(
        '--year-month',
        type=str,
        required=True,
        help='取得する年月（例: 2024-12）'
    )

    args = parser.parse_args()

    # 年月のパース
    try:
        year, month = map(int, args.year_month.split('-'))
    except ValueError:
        print("エラー: 年月の形式が正しくありません。例: 2024-12")
        sys.exit(1)

    # 日付範囲を取得
    start_date, end_date = get_month_date_range(year, month)

    print(f"\n{'='*80}")
    print(f"月次スクレイピング: {year}年{month}月")
    print(f"期間: {start_date} ~ {end_date}")
    print(f"{'='*80}")

    # スクレイピング実行
    exit_code = run_scraper(start_date, end_date)

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
