"""
過去データのスクレイピング機能
平日に実行して、過去のレースデータを取得する
参考: https://note.com/dijzpeb/n/n6b025960fbff
"""
import json
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
from datetime import datetime, timedelta
import random
import re
from pathlib import Path
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

# config読み込み
config_path = Path(__file__).parent.parent / 'config.json'
if not config_path.exists():
    # GitHub Actionsなどで実行される場合はカレントディレクトリから
    config_path = Path('config.json')
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# ===== リクエスト管理用のグローバル変数 =====
last_request_time = 0
request_count = 0
request_count_date = None

# 設定から取得（デフォルト値あり）
request_settings = config.get('request_settings', {})
MIN_REQUEST_INTERVAL = request_settings.get('min_interval', 1.5)
MAX_REQUESTS_WEEKDAY = request_settings.get('max_requests_weekday', 8000)
MAX_REQUESTS_WEEKEND = request_settings.get('max_requests_weekend', 150)

def create_session():
    """スクレイピング対策を施したセッションを作成"""
    session = requests.Session()

    # User-Agentのランダム化
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]
    session.headers.update({
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })

    # リトライ戦略
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session

# グローバルセッション（再利用して接続を維持）
session = create_session()

def get_max_requests_for_today():
    """今日のリクエスト上限を取得（平日/土日で分ける）"""
    today = datetime.now().date()
    is_weekend = today.weekday() >= 5
    return MAX_REQUESTS_WEEKEND if is_weekend else MAX_REQUESTS_WEEKDAY

def reset_request_count_if_needed():
    """日付が変わったらリクエスト数をリセット"""
    global request_count, request_count_date
    today = datetime.now().date()
    if request_count_date != today:
        request_count = 0
        request_count_date = today
        print(f"[リクエストカウントリセット] 日付: {today}, 上限: {get_max_requests_for_today()}")

def get_request_status():
    """現在のリクエスト状態を取得"""
    reset_request_count_if_needed()
    max_requests = get_max_requests_for_today()
    remaining = max_requests - request_count
    today = datetime.now().date()
    is_weekend = today.weekday() >= 5
    return {
        'count': request_count,
        'max': max_requests,
        'remaining': remaining,
        'date': request_count_date,
        'is_weekend': is_weekend,
        'type': 'weekend' if is_weekend else 'weekday'
    }

def safe_request(url, max_retries=3, timeout=None):
    """
    スクレイピング対策を施した安全なリクエスト関数

    Args:
        url: リクエスト先URL
        max_retries: 最大リトライ回数
        timeout: タイムアウト時間（秒）

    Returns:
        Responseオブジェクト（失敗時はNone）
    """
    global last_request_time, request_count

    reset_request_count_if_needed()

    max_requests = get_max_requests_for_today()
    if request_count >= max_requests:
        today = datetime.now().date()
        is_weekend = today.weekday() >= 5
        print(f"[警告] リクエスト上限に到達 ({request_count}/{max_requests}, {'週末' if is_weekend else '平日'})")
        return None

    # レート制限（最小間隔を確保）
    current_time = time.time()
    elapsed = current_time - last_request_time
    if elapsed < MIN_REQUEST_INTERVAL:
        wait_time = MIN_REQUEST_INTERVAL - elapsed
        time.sleep(wait_time)

    # タイムアウト設定
    if timeout is None:
        timeout = config.get('timeouts', {}).get('scraping', 10)

    for attempt in range(max_retries):
        try:
            response = session.get(url, timeout=timeout)
            last_request_time = time.time()
            request_count += 1

            if response.status_code == 200:
                return response
            elif response.status_code == 404:
                print(f"[404] ページが見つかりません: {url}")
                return None
            else:
                print(f"[エラー] ステータスコード {response.status_code}: {url}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"  {wait_time}秒後にリトライ...")
                    time.sleep(wait_time)
        except Exception as e:
            print(f"[リクエストエラー] {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"  {wait_time}秒後にリトライ...")
                time.sleep(wait_time)

    return None

def get_race_ids(kaisai_date):
    """
    指定日のレースID一覧を取得

    Args:
        kaisai_date: 開催日（例: '20241123'）

    Returns:
        list[str]: レースIDのリスト
    """
    url = f'https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={kaisai_date}'
    response = safe_request(url)

    if not response:
        print(f"レースID取得失敗: {url}")
        return []

    try:
        try:
            soup = BeautifulSoup(response.content, 'lxml')
        except:
            soup = BeautifulSoup(response.content, 'html.parser')

        race_ids = []
        for a_tag in soup.select('li.RaceList_DataItem a[href*="/race/"]'):
            href = a_tag.get('href', '')
            match = re.search(r'race_id=(\d+)', href)
            if match:
                race_id = match.group(1)
                if race_id not in race_ids:
                    race_ids.append(race_id)

        return race_ids
    except Exception as e:
        print(f"レースID解析エラー ({kaisai_date}): {e}")
        return []

def get_kaisai_dates(year, month):
    """
    指定年月のレース開催日を取得
    参考: https://race.netkeiba.com/top/calendar.html?year={year}&month={month}
    
    Args:
        year: 年（例: 2025）
        month: 月（例: 11）
    
    Returns:
        list[str]: 開催日のリスト（例: ['20251101', '20251102', ...]）
    """
    url = f'https://race.netkeiba.com/top/calendar.html?year={year}&month={month}'
    response = safe_request(url)
    
    if not response:
        print(f"開催日取得失敗: {url}")
        return []
    
    try:
        try:
            soup = BeautifulSoup(response.content, 'lxml')
        except:
            soup = BeautifulSoup(response.content, 'html.parser')
        
        kaisai_dates = []
        # カレンダーテーブルから開催日を抽出
        for a_tag in soup.select('.Calendar_Table .Week > td > a'):
            href = a_tag.get('href', '')
            match = re.search(r'kaisai_date=(\d+)', href)
            if match:
                kaisai_date = match.group(1)
                if kaisai_date not in kaisai_dates:
                    kaisai_dates.append(kaisai_date)
        
        return sorted(kaisai_dates)
    except Exception as e:
        print(f"開催日解析エラー ({year}-{month:02d}): {e}")
        return []

def get_kaisai_dates_range(start_year, start_month, end_year, end_month):
    """
    指定期間のレース開催日を取得（複数月対応）
    
    Args:
        start_year: 開始年
        start_month: 開始月
        end_year: 終了年
        end_month: 終了月
    
    Returns:
        list[str]: 開催日のリスト（ソート済み）
    """
    all_dates = []
    current_year = start_year
    current_month = start_month
    
    while (current_year < end_year) or (current_year == end_year and current_month <= end_month):
        print(f"  カレンダー取得中: {current_year}年{current_month}月")
        dates = get_kaisai_dates(current_year, current_month)
        all_dates.extend(dates)
        
        # 次の月へ
        current_month += 1
        if current_month > 12:
            current_month = 1
            current_year += 1
        
        # リクエスト間隔を確保
        time.sleep(0.5)
    
    # 重複を除去してソート
    return sorted(list(set(all_dates)))

# データ保存ディレクトリ（参考ページの構造に合わせる）
DATA_DIR = Path('data')
RAW_DATA_DIR = DATA_DIR / 'rawdf'
HTML_DIR = DATA_DIR / 'html'
RACE_HTML_DIR = HTML_DIR / 'race'
HORSE_HTML_DIR = HTML_DIR / 'horse'
RESULT_HTML_DIR = HORSE_HTML_DIR / 'result'
PED_HTML_DIR = HORSE_HTML_DIR / 'ped'
LEADING_HTML_DIR = HTML_DIR / 'leading'

# ディレクトリ作成
for dir_path in [RAW_DATA_DIR, RACE_HTML_DIR, RESULT_HTML_DIR, PED_HTML_DIR, LEADING_HTML_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

def save_html(html_content, file_path):
    """HTMLコンテンツをバイナリ形式で保存"""
    try:
        with open(file_path, 'wb') as f:
            f.write(html_content)
        return True
    except Exception as e:
        print(f"  [エラー] HTML保存エラー ({file_path.name}): {e}")
        return False

def scrape_race_result(race_id, verbose=True):
    """
    レース結果ページをスクレイピング
    
    Args:
        race_id: レースID
        verbose: スキップ時にログを出力するか
    
    Returns:
        tuple: (成功したかどうか, スキップしたかどうか)
    """
    file_path = RACE_HTML_DIR / f'{race_id}.bin'
    
    # 既に取得済みの場合はスキップ
    if file_path.exists():
        if verbose:
            print(f"    [スキップ] レース結果は既に取得済み: {race_id}")
        return True, True  # (成功, スキップ)
    
    url = f'https://db.netkeiba.com/race/{race_id}/'
    response = safe_request(url)
    
    if not response:
        return False, False  # (失敗, スキップなし)
    
    success = save_html(response.content, file_path)
    return success, False  # (成功/失敗, スキップなし)

def extract_horse_ids_from_race(race_id):
    """
    レース結果ページから馬IDを抽出
    
    Args:
        race_id: レースID
    
    Returns:
        list[str]: 馬IDのリスト
    """
    file_path = RACE_HTML_DIR / f'{race_id}.bin'
    
    if not file_path.exists():
        return []
    
    try:
        with open(file_path, 'rb') as f:
            html_content = f.read()
        
        try:
            soup = BeautifulSoup(html_content, 'lxml')
        except:
            soup = BeautifulSoup(html_content, 'html.parser')
        
        horse_ids = []
        # レース結果テーブルから馬IDを抽出
        for a_tag in soup.select('a[href*="/horse/"]'):
            href = a_tag.get('href', '')
            # /horse/{horse_id}/ のパターンを探す
            match = re.search(r'/horse/(\d+)/', href)
            if match:
                horse_id = match.group(1)
                if horse_id not in horse_ids:
                    horse_ids.append(horse_id)
        
        return horse_ids
    except Exception as e:
        print(f"  [警告] 馬ID抽出エラー ({race_id}): {e}")
        return []

def scrape_horse_result(horse_id, verbose=False):
    """
    馬の結果ページをスクレイピング
    
    Args:
        horse_id: 馬ID
        verbose: スキップ時にログを出力するか
    
    Returns:
        tuple: (成功したかどうか, スキップしたかどうか)
    """
    file_path = RESULT_HTML_DIR / f'{horse_id}.bin'
    
    # 既に取得済みの場合はスキップ
    if file_path.exists():
        return True, True  # (成功, スキップ)
    
    url = f'https://db.netkeiba.com/horse/result/{horse_id}/'
    response = safe_request(url)
    
    if not response:
        return False, False  # (失敗, スキップなし)
    
    success = save_html(response.content, file_path)
    return success, False  # (成功/失敗, スキップなし)

def scrape_horse_ped(horse_id, verbose=False):
    """
    馬の血統ページをスクレイピング
    
    Args:
        horse_id: 馬ID
        verbose: スキップ時にログを出力するか
    
    Returns:
        tuple: (成功したかどうか, スキップしたかどうか)
    """
    file_path = PED_HTML_DIR / f'{horse_id}.bin'
    
    # 既に取得済みの場合はスキップ
    if file_path.exists():
        return True, True  # (成功, スキップ)
    
    url = f'https://db.netkeiba.com/horse/ped/{horse_id}/'
    response = safe_request(url)
    
    if not response:
        return False, False  # (失敗, スキップなし)
    
    success = save_html(response.content, file_path)
    return success, False  # (成功/失敗, スキップなし)

def scrape_leading_pages():
    """
    リーディングページ（騎手、調教師、種牡馬）をスクレイピング
    """
    leading_types = {
        'jockey': 'https://db.netkeiba.com/leading/jockey/',
        'trainer': 'https://db.netkeiba.com/leading/trainer/',
        'sire': 'https://db.netkeiba.com/leading/sire/',
    }
    
    for leading_type, url in leading_types.items():
        file_path = LEADING_HTML_DIR / f'{leading_type}.bin'
        
        # リーディングは日次更新のため、毎日取得する（既存ファイルは上書き）
        response = safe_request(url)
        if response:
            if save_html(response.content, file_path):
                print(f"  [完了] {leading_type}リーディング取得完了")
        else:
            print(f"  [エラー] {leading_type}リーディング取得失敗")

def is_holiday(date):
    """
    祝日かどうかを簡易判定（日本の祝日）
    注意: 完全な祝日判定にはholidaysライブラリが必要
    
    Args:
        date: 日付（datetime.date）
    
    Returns:
        bool: 祝日の場合True
    """
    # 簡易版：主要な祝日のみ判定
    # 完全な判定には jpholiday などのライブラリが必要
    month = date.month
    day = date.day
    
    # 元日
    if month == 1 and day == 1:
        return True
    # 成人の日（1月第2月曜日）- 簡易版では1/8-1/14を祝日として扱う
    if month == 1 and 8 <= day <= 14:
        return True
    # 建国記念の日
    if month == 2 and day == 11:
        return True
    # 春分の日（簡易版：3/20-3/21）
    if month == 3 and 20 <= day <= 21:
        return True
    # 昭和の日
    if month == 4 and day == 29:
        return True
    # 憲法記念日
    if month == 5 and day == 3:
        return True
    # みどりの日
    if month == 5 and day == 4:
        return True
    # こどもの日
    if month == 5 and day == 5:
        return True
    # 海の日（7月第3月曜日）- 簡易版では7/15-7/21を祝日として扱う
    if month == 7 and 15 <= day <= 21:
        return True
    # 山の日
    if month == 8 and day == 11:
        return True
    # 敬老の日（9月第3月曜日）- 簡易版では9/15-9/21を祝日として扱う
    if month == 9 and 15 <= day <= 21:
        return True
    # 秋分の日（簡易版：9/22-9/23）
    if month == 9 and 22 <= day <= 23:
        return True
    # スポーツの日（10月第2月曜日）- 簡易版では10/8-10/14を祝日として扱う
    if month == 10 and 8 <= day <= 14:
        return True
    # 文化の日
    if month == 11 and day == 3:
        return True
    # 勤労感謝の日
    if month == 11 and day == 23:
        return True
    # 天皇誕生日
    if month == 2 and day == 23:
        return True
    
    return False

def scrape_date_range_from_calendar(start_year, start_month, end_year, end_month, scrape_horses=True, scrape_peds=True):
    """
    カレンダーページから開催日を取得してスクレイピング
    参考: https://race.netkeiba.com/top/calendar.html?year={year}&month={month}
    
    Args:
        start_year: 開始年
        start_month: 開始月
        end_year: 終了年
        end_month: 終了月
        scrape_horses: 馬データも取得するか
        scrape_peds: 血統データも取得するか
    
    Returns:
        dict: 取得結果の統計
    """
    print(f"カレンダーから開催日を取得: {start_year}年{start_month}月 ～ {end_year}年{end_month}月")
    print("  [進行中] カレンダーページを取得中...")
    
    # カレンダーから開催日を取得
    kaisai_dates = get_kaisai_dates_range(start_year, start_month, end_year, end_month)
    
    if not kaisai_dates:
        print("[警告] 開催日が見つかりませんでした")
        return {
            'dates_processed': 0,
            'races_processed': 0,
            'races_success': 0,
            'races_skipped': 0,
            'horses_processed': 0,
            'horses_success': 0,
            'horses_skipped': 0,
            'peds_processed': 0,
            'peds_success': 0,
            'peds_skipped': 0,
        }
    
    print(f"[完了] {len(kaisai_dates)}件の開催日が見つかりました")
    print(f"  開催日: {', '.join(kaisai_dates[:10])}{'...' if len(kaisai_dates) > 10 else ''}")
    
    # 処理時間の見積もりを表示
    estimated_races = len(kaisai_dates) * 10  # 1開催日あたり平均10レースと仮定
    estimated_horses = estimated_races * 15  # 1レースあたり平均15頭と仮定
    estimated_time_minutes = (estimated_races * 2 + estimated_horses * 3) / 60
    print(f"\n[見積もり] 処理時間: 約{estimated_time_minutes:.1f}分（レース: {estimated_races}件、馬: {estimated_horses}頭を想定）")
    print("  ※ リクエスト間隔（1.5秒）により時間がかかります")
    
    # 開催日を日付オブジェクトに変換
    dates = [datetime.strptime(d, '%Y%m%d').date() for d in kaisai_dates]
    start_date = min(dates)
    end_date = max(dates)
    
    print(f"日付範囲: {start_date} ～ {end_date}")
    
    # 通常のスクレイピングを実行（開催日のみ処理）
    # カレンダーから取得した開催日のみを処理するため、日付を直接指定
    stats = {
        'dates_processed': 0,
        'races_processed': 0,
        'races_success': 0,
        'races_skipped': 0,
        'horses_processed': 0,
        'horses_success': 0,
        'horses_skipped': 0,
        'peds_processed': 0,
        'peds_success': 0,
        'peds_skipped': 0,
    }
    
    today = datetime.now().date()
    
    for kaisai_date_str in kaisai_dates:
        kaisai_date = datetime.strptime(kaisai_date_str, '%Y%m%d').date()
        
        # 今日の日付はスキップ
        if kaisai_date == today:
            print(f"\n{kaisai_date.strftime('%Y-%m-%d')} (今日) - スキップ（当日レース情報取得に注力）")
            continue
        
        # 開催日の処理
        is_weekend = kaisai_date.weekday() >= 5
        is_holiday_date = is_holiday(kaisai_date)
        
        date_type = ""
        if is_weekend and is_holiday_date:
            date_type = " (土日・祝日)"
        elif is_weekend:
            date_type = " (土日)"
        elif is_holiday_date:
            date_type = " (祝日)"
        else:
            date_type = " (平日)"
        
        print(f"\n{'='*80}")
        print(f"処理中: {kaisai_date.strftime('%Y-%m-%d (%A)')}{date_type}")
        print(f"{'='*80}")
        
        race_ids = get_race_ids(kaisai_date_str)
        
        if not race_ids:
            print(f"  [警告] レースが見つかりませんでした")
            continue
        
        print(f"  [完了] {len(race_ids)}レースを発見")
        stats['dates_processed'] += 1
        
        # 各レースを処理
        for i, race_id in enumerate(race_ids, 1):
            print(f"\n  [{i}/{len(race_ids)}] レースID: {race_id} (全体: {stats['races_processed'] + 1}レース目)")
            stats['races_processed'] += 1
            
            # レース結果を取得
            race_success, race_skipped = scrape_race_result(race_id)
            if race_success:
                if race_skipped:
                    stats['races_skipped'] += 1
                    print(f"    [スキップ] 既に取得済み")
                else:
                    stats['races_success'] += 1
                    print(f"    [完了] レース結果取得完了")
                
                # 馬データを取得
                if scrape_horses:
                    horse_ids = extract_horse_ids_from_race(race_id)
                    if horse_ids:
                        print(f"    → {len(horse_ids)}頭の馬データを取得中...")
                        for j, horse_id in enumerate(horse_ids, 1):
                            if j % 5 == 0 or j == len(horse_ids):
                                print(f"      馬データ取得進捗: {j}/{len(horse_ids)}頭 (全体: {stats['horses_processed'] + 1}頭目)")
                            stats['horses_processed'] += 1
                            horse_success, horse_skipped = scrape_horse_result(horse_id)
                            if horse_success:
                                if horse_skipped:
                                    stats['horses_skipped'] += 1
                                else:
                                    stats['horses_success'] += 1
                            
                            # 血統データを取得
                            if scrape_peds:
                                stats['peds_processed'] += 1
                                ped_success, ped_skipped = scrape_horse_ped(horse_id)
                                if ped_success:
                                    if ped_skipped:
                                        stats['peds_skipped'] += 1
                                    else:
                                        stats['peds_success'] += 1
                            
                            # リクエスト間隔を確保
                            time.sleep(0.3)
            else:
                print(f"    [エラー] レース結果取得失敗")
            
            # リクエスト状態を確認
            status = get_request_status()
            if status['remaining'] <= 5:
                print(f"  [警告] 残りリクエスト数: {status['remaining']}回")
                if status['remaining'] <= 0:
                    print("  [警告] 1日のリクエスト上限に達しました。処理を中断します。")
                    return stats
            
            # リクエスト間隔を確保
            time.sleep(0.5)
    
    return stats

def scrape_date_range(start_date, end_date, scrape_horses=True, scrape_peds=True, skip_today=True):
    """
    指定日付範囲のデータをスクレイピング
    
    Args:
        start_date: 開始日（datetime.date）
        end_date: 終了日（datetime.date）
        scrape_horses: 馬データも取得するか
        scrape_peds: 血統データも取得するか
        skip_today: 今日の日付をスキップするか（当日レース情報取得に注力するため）
    
    Returns:
        dict: 取得結果の統計
    """
    stats = {
        'dates_processed': 0,
        'races_processed': 0,
        'races_success': 0,
        'races_skipped': 0,
        'horses_processed': 0,
        'horses_success': 0,
        'horses_skipped': 0,
        'peds_processed': 0,
        'peds_success': 0,
        'peds_skipped': 0,
    }
    
    today = datetime.now().date()
    current_date = start_date
    
    while current_date <= end_date:
        # 今日の日付はスキップ（当日レース情報取得に注力するため）
        if skip_today and current_date == today:
            print(f"\n{current_date.strftime('%Y-%m-%d')} (今日) - スキップ（当日レース情報取得に注力）")
            current_date += timedelta(days=1)
            continue
        
        # 土日・祝日はJRAのレース開催日なので処理する
        is_weekend = current_date.weekday() >= 5
        is_holiday_date = is_holiday(current_date)
        
        date_type = ""
        if is_weekend and is_holiday_date:
            date_type = " (土日・祝日)"
        elif is_weekend:
            date_type = " (土日)"
        elif is_holiday_date:
            date_type = " (祝日)"
        else:
            date_type = " (平日)"
        
        print(f"\n{'='*80}")
        print(f"処理中: {current_date.strftime('%Y-%m-%d (%A)')}{date_type}")
        print(f"{'='*80}")

        # 開催カレンダーから実際の開催日を確認
        year = current_date.year
        month = current_date.month
        kaisai_dates_in_month = get_kaisai_dates(year, month)
        kaisai_date = current_date.strftime('%Y%m%d')

        # 開催日でない場合はスキップ
        if kaisai_date not in kaisai_dates_in_month:
            print(f"  [スキップ] レース開催日ではありません")
            current_date += timedelta(days=1)
            continue

        # レースIDを取得
        race_ids = get_race_ids(kaisai_date)

        if not race_ids:
            print(f"  [警告] レースが見つかりませんでした")
            current_date += timedelta(days=1)
            continue
        
        print(f"  [完了] {len(race_ids)}レースを発見")
        stats['dates_processed'] += 1
        
        # 各レースを処理
        for i, race_id in enumerate(race_ids, 1):
            print(f"\n  [{i}/{len(race_ids)}] レースID: {race_id}")
            stats['races_processed'] += 1
            
            # レース結果を取得
            race_success, race_skipped = scrape_race_result(race_id)
            if race_success:
                if race_skipped:
                    stats['races_skipped'] += 1
                else:
                    stats['races_success'] += 1
                    print(f"    [完了] レース結果取得完了")
                
                # 馬データを取得
                if scrape_horses:
                    horse_ids = extract_horse_ids_from_race(race_id)
                    if horse_ids:
                        print(f"    → {len(horse_ids)}頭の馬データを取得中...")
                        for horse_id in horse_ids:
                            stats['horses_processed'] += 1
                            horse_success, horse_skipped = scrape_horse_result(horse_id)
                            if horse_success:
                                if horse_skipped:
                                    stats['horses_skipped'] += 1
                                else:
                                    stats['horses_success'] += 1
                            
                            # 血統データを取得
                            if scrape_peds:
                                stats['peds_processed'] += 1
                                ped_success, ped_skipped = scrape_horse_ped(horse_id)
                                if ped_success:
                                    if ped_skipped:
                                        stats['peds_skipped'] += 1
                                    else:
                                        stats['peds_success'] += 1
                            
                            # リクエスト間隔を確保
                            time.sleep(0.3)
            else:
                print(f"    [エラー] レース結果取得失敗")
            
            # リクエスト状態を確認
            status = get_request_status()
            if status['remaining'] <= 5:
                print(f"  [警告] 残りリクエスト数: {status['remaining']}回")
                if status['remaining'] <= 0:
                    print("  [警告] 1日のリクエスト上限に達しました。処理を中断します。")
                    return stats
            
            # リクエスト間隔を確保
            time.sleep(0.5)
        
        current_date += timedelta(days=1)
    
    return stats

def find_recent_race_dates(days_back=30, min_races=1, include_weekend=True):
    """
    最近のレース開催日を検索
    
    Args:
        days_back: 過去何日まで検索するか
        min_races: 最低レース数
        include_weekend: 土日を含めるか（JRAは土日に開催されるためTrue推奨）
    
    Returns:
        list[dict]: レース開催日のリスト
    """
    today = datetime.now().date()
    found_dates = []
    
    for i in range(days_back):
        check_date = today - timedelta(days=i)
        # 今日はスキップ（当日レース情報取得に注力するため）
        if check_date == today:
            continue
        
        kaisai_date = check_date.strftime('%Y%m%d')
        race_ids = get_race_ids(kaisai_date)
        
        if race_ids and len(race_ids) >= min_races:
            found_dates.append({
                'date': check_date,
                'kaisai_date': kaisai_date,
                'race_count': len(race_ids)
            })
            if len(found_dates) >= 5:  # 5件見つかったら終了
                break
    
    return found_dates

def scrape_last_week():
    """
    先週のデータをスクレイピング（テスト用）
    カレンダーページから実際の開催日を取得
    """
    today = datetime.now().date()
    last_week_date = today - timedelta(days=7)
    last_week_year = last_week_date.year
    last_week_month = last_week_date.month
    
    print(f"先週のデータを取得します（カレンダーから開催日を取得）")
    print(f"  対象: {last_week_year}年{last_week_month}月")
    
    # カレンダーから開催日を取得
    return scrape_date_range_from_calendar(
        last_week_year, last_week_month,
        last_week_year, last_week_month,
        scrape_horses=True, scrape_peds=True
    )

def scrape_date_range_from_config(scrape_horses=True, scrape_peds=True, skip_today=True):
    """
    config.jsonから日付範囲を読み込んでスクレイピング
    カレンダーページから開催日を取得する方式と、直接日付を指定する方式の両方に対応
    
    Args:
        scrape_horses: 馬データも取得するか
        scrape_peds: 血統データも取得するか
        skip_today: 今日の日付をスキップするか
    """
    scraper_config = config.get('scraper', {})
    
    # カレンダー方式（年月指定）
    start_year = scraper_config.get('start_year')
    start_month = scraper_config.get('start_month')
    end_year = scraper_config.get('end_year')
    end_month = scraper_config.get('end_month')
    
    if start_year and start_month and end_year and end_month:
        print(f"カレンダー方式で取得: {start_year}年{start_month}月 ～ {end_year}年{end_month}月")
        return scrape_date_range_from_calendar(
            start_year, start_month,
            end_year, end_month,
            scrape_horses=scrape_horses, scrape_peds=scrape_peds
        )
    
    # 直接日付指定方式
    start_date_str = scraper_config.get('start_date')
    end_date_str = scraper_config.get('end_date')
    
    if start_date_str and end_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        print(f"日付指定方式で取得: {start_date} ～ {end_date}")
        return scrape_date_range(start_date, end_date, scrape_horses=scrape_horses, scrape_peds=scrape_peds, skip_today=skip_today)
    
    # 設定がない場合は先週のデータを取得
    print("[警告] config.jsonにscraper設定がありません。先週のデータを取得します。")
    return scrape_last_week()

if __name__ == '__main__':
    print("="*80)
    print("過去データスクレイピング開始")
    print("="*80)
    
    # リクエスト状態を確認
    status = get_request_status()
    print(f"\n現在のリクエスト状態:")
    print(f"  使用済み: {status['count']}回")
    print(f"  残り: {status['remaining']}回")
    
    if status['remaining'] <= 0:
        print("[警告] 1日のリクエスト上限に達しています。処理を中断します。")
        exit(1)
    
    # リーディングページを取得（最初に1回だけ）
    print("\n【リーディングページ取得】")
    scrape_leading_pages()
    
    # 先週のデータを取得（テスト）
    print("\n【テストモード】先週のデータを取得します")
    stats = scrape_last_week()
    
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
    
    # 取得したファイル数の確認
    print(f"\n取得したファイル数:")
    print(f"  レース結果: {len(list(RACE_HTML_DIR.glob('*.bin')))}")
    print(f"  馬結果: {len(list(RESULT_HTML_DIR.glob('*.bin')))}")
    print(f"  血統: {len(list(PED_HTML_DIR.glob('*.bin')))}")
