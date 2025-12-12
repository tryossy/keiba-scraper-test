"""
競馬データ月次スクレイピングスクリプト（KeibaScraper ラッパー）

KeibaScraper (https://github.com/new-village/KeibaScraper) を使用して
指定月のレースデータを取得し、CSVファイルに保存します。

使用方法:
    python scrape_monthly.py --year-month 2024-12
    python scrape_monthly.py --year-month 2024-12 --output output.csv
"""
import argparse
import sys
import time
from datetime import datetime, timedelta
from typing import List, Dict
import pandas as pd

try:
    from keibascraper import RaceScraper
except ImportError:
    print("エラー: keibascraper がインストールされていません。")
    print("インストール: pip install keibascraper")
    sys.exit(1)


class MonthlyRaceScraper:
    """月次レースデータスクレイピング"""

    def __init__(self, min_interval: float = 1.5):
        """
        Args:
            min_interval: リクエスト間隔（秒）。サーバー負荷軽減のため最低1.5秒推奨
        """
        self.scraper = RaceScraper()
        self.min_interval = min_interval
        self.last_request_time = 0

    def _wait_for_rate_limit(self):
        """レート制限のための待機"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            wait_time = self.min_interval - elapsed
            print(f"  [レート制限] {wait_time:.1f}秒待機...")
            time.sleep(wait_time)
        self.last_request_time = time.time()

    def get_race_ids_for_month(self, year: int, month: int) -> List[str]:
        """
        指定月のレースIDリストを取得

        Args:
            year: 年（例: 2024）
            month: 月（例: 12）

        Returns:
            レースIDのリスト（例: ['202412010101', '202412010102', ...]）

        Note:
            実際の実装では、カレンダーAPIまたはレース一覧ページから取得する必要があります。
            ここでは簡易的に日付ベースで生成していますが、実際のレース開催日を確認することを推奨します。
        """
        race_ids = []

        # 指定月の最初と最後の日
        first_day = datetime(year, month, 1)
        if month == 12:
            last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = datetime(year, month + 1, 1) - timedelta(days=1)

        print(f"\n[レースID生成] {year}年{month}月 ({first_day.date()} 〜 {last_day.date()})")

        # 各日について
        current_day = first_day
        while current_day <= last_day:
            date_str = current_day.strftime('%Y%m%d')

            # 一般的に土日にレースが開催されることが多い
            # ただし、GWや祝日など例外もあるため、実際には全日チェックが必要
            if current_day.weekday() in [5, 6]:  # 土日
                # 各競馬場・レース番号の組み合わせ
                # 01〜10: 競馬場コード（01=札幌, 02=函館, 03=福島, 04=新潟, 05=東京, 06=中山, 07=中京, 08=京都, 09=阪神, 10=小倉）
                # 01〜12: レース番号
                for place_code in ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10']:
                    for race_num in range(1, 13):  # 1〜12レース
                        race_id = f"{date_str}{place_code}{race_num:02d}"
                        race_ids.append(race_id)

            current_day += timedelta(days=1)

        print(f"  候補レースID数: {len(race_ids)}")
        print(f"  注意: 実際の開催レースのみが取得されます（存在しないレースはスキップ）")

        return race_ids

    def scrape_race(self, race_id: str) -> Dict:
        """
        単一レースのデータを取得

        Args:
            race_id: レースID（例: '202412010101'）

        Returns:
            レースデータの辞書（取得失敗時はNone）
        """
        self._wait_for_rate_limit()

        try:
            print(f"  [取得中] レースID: {race_id}")
            data = self.scraper.scrape_race(race_id)
            return data
        except Exception as e:
            print(f"  [エラー] レースID {race_id}: {e}")
            return None

    def scrape_month(self, year: int, month: int) -> pd.DataFrame:
        """
        指定月の全レースデータを取得

        Args:
            year: 年
            month: 月

        Returns:
            レースデータのDataFrame
        """
        print(f"\n{'='*80}")
        print(f"月次スクレイピング: {year}年{month}月")
        print(f"{'='*80}")

        race_ids = self.get_race_ids_for_month(year, month)

        all_data = []
        success_count = 0
        error_count = 0

        for i, race_id in enumerate(race_ids, 1):
            print(f"\n[{i}/{len(race_ids)}] レースID: {race_id}")

            data = self.scrape_race(race_id)
            if data:
                all_data.append(data)
                success_count += 1
            else:
                error_count += 1

            # 進捗表示
            if i % 10 == 0:
                print(f"\n--- 進捗 ---")
                print(f"  処理済み: {i}/{len(race_ids)}")
                print(f"  成功: {success_count}, エラー: {error_count}")

        print(f"\n{'='*80}")
        print(f"スクレイピング完了")
        print(f"{'='*80}")
        print(f"成功: {success_count} レース")
        print(f"エラー: {error_count} レース")

        if all_data:
            df = pd.DataFrame(all_data)
            return df
        else:
            print("警告: データが取得できませんでした。")
            return pd.DataFrame()


def main():
    parser = argparse.ArgumentParser(
        description='競馬データ月次スクレイピング（KeibaScraper ラッパー）'
    )
    parser.add_argument(
        '--year-month',
        type=str,
        required=True,
        help='取得する年月（例: 2024-12）'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='race_data.csv',
        help='出力CSVファイル名（デフォルト: race_data.csv）'
    )
    parser.add_argument(
        '--interval',
        type=float,
        default=1.5,
        help='リクエスト間隔（秒）（デフォルト: 1.5）'
    )

    args = parser.parse_args()

    # 年月のパース
    try:
        year, month = map(int, args.year_month.split('-'))
    except ValueError:
        print("エラー: 年月の形式が正しくありません。例: 2024-12")
        sys.exit(1)

    # スクレイピング実行
    scraper = MonthlyRaceScraper(min_interval=args.interval)
    df = scraper.scrape_month(year, month)

    # CSV保存
    if not df.empty:
        df.to_csv(args.output, index=False, encoding='utf-8-sig')
        print(f"\n[保存完了] {args.output}")
        print(f"  行数: {len(df)}")
        print(f"  列数: {len(df.columns)}")
    else:
        print("\nエラー: データが空のため保存できませんでした。")
        sys.exit(1)


if __name__ == '__main__':
    main()
