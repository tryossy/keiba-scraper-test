"""
競馬複勝通知プログラム - メインスクリプト
"""
import json
import requests
from bs4 import BeautifulSoup
import pandas as pd
import lightgbm as lgb
import joblib
from datetime import datetime, timedelta
import schedule
import time
import os
import random
import re
from pathlib import Path
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

# config読み込み（app/ディレクトリから見た相対パス）
config_path = Path(__file__).parent.parent / 'config.json'
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# Discord通知関数
def send_discord_notify(message):
    """Discordに通知を送信"""
    try:
        webhook_url = config['discord_webhook_url']
        data = {"content": message}
        timeout = config.get('timeouts', {}).get('discord_notify', 5)
        response = requests.post(webhook_url, json=data, timeout=timeout)
        if response.status_code == 204:
            print("通知送信成功")
        else:
            print(f"通知エラー: {response.status_code}")
    except Exception as e:
        print(f"通知送信失敗: {e}")

# セッション作成（スクレイピング対策）
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

# リクエスト管理用のグローバル変数
last_request_time = 0
request_count = 0
request_count_date = None

# 設定から取得（デフォルト値あり）
request_settings = config.get('request_settings', {})
MIN_REQUEST_INTERVAL = request_settings.get('min_interval', 1.5)  # 最小リクエスト間隔（秒）
# 平日/土日でリクエスト上限を分ける
MAX_REQUESTS_WEEKDAY = request_settings.get('max_requests_weekday', 8000)  # 平日の最大リクエスト数
MAX_REQUESTS_WEEKEND = request_settings.get('max_requests_weekend', 150)  # 土日の最大リクエスト数
# 後方互換性のため、max_requests_per_dayも残す（デフォルトは土日用）
MAX_REQUESTS_PER_DAY = request_settings.get('max_requests_per_day', MAX_REQUESTS_WEEKEND)  # 1日の最大リクエスト数（後方互換性）

def get_max_requests_for_today():
    """今日のリクエスト上限を取得（平日/土日で分ける）"""
    today = datetime.now().date()
    is_weekend = today.weekday() >= 5  # 土日は5以上
    if is_weekend:
        return MAX_REQUESTS_WEEKEND
    else:
        return MAX_REQUESTS_WEEKDAY

def reset_request_count_if_needed():
    """日付が変わったらリクエスト数をリセット"""
    global request_count, request_count_date
    today = datetime.now().date()
    
    if request_count_date != today:
        request_count = 0
        request_count_date = today
        print(f"リクエストカウントをリセットしました（日付変更: {today}）")

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
        timeout: タイムアウト時間（秒）。Noneの場合はconfigから取得
    
    Returns:
        Responseオブジェクト（失敗時はNone）
    """
    global last_request_time, request_count
    
    # 日付チェックとリクエスト数リセット
    reset_request_count_if_needed()
    
    # 1日のリクエスト数制限チェック（平日/土日で分ける）
    max_requests = get_max_requests_for_today()
    if request_count >= max_requests:
        today = datetime.now().date()
        is_weekend = today.weekday() >= 5
        day_type = "土日" if is_weekend else "平日"
        print(f"[警告] 1日のリクエスト上限（{max_requests}回、{day_type}）に達しました")
        return None
    
    # タイムアウト設定を取得
    if timeout is None:
        timeout = config.get('timeouts', {}).get('request', 10)
    
    for attempt in range(max_retries):
        try:
            # アクセス間隔を調整（スクレイピング対策）
            # 最初のリクエスト時（last_request_time == 0）は待機しない
            if last_request_time > 0:
                elapsed = time.time() - last_request_time
                if elapsed < MIN_REQUEST_INTERVAL:
                    sleep_time = MIN_REQUEST_INTERVAL - elapsed + random.uniform(0.1, 0.5)
                    time.sleep(sleep_time)
            
            # リクエスト実行（タイムアウト設定）
            response = session.get(url, timeout=timeout)
            response.raise_for_status()
            
            # リクエスト数をカウント
            request_count += 1
            last_request_time = time.time()
            
            return response
        
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + random.uniform(0, 1)  # 指数バックオフ
                print(f"リクエストエラー（リトライ {attempt + 1}/{max_retries}）: {e}")
                time.sleep(wait_time)
            else:
                print(f"リクエスト失敗（最大リトライ回数に達しました）: {e}")
                return None
    
    return None

# URL生成関数
def get_shutuba_url(race_id):
    """出馬表ページのURLを生成"""
    return f'https://race.netkeiba.com/race/shutuba.html?race_id={race_id}'

def get_db_race_url(race_id):
    """データベースレースページのURLを生成"""
    return f'https://db.netkeiba.com/race/{race_id}/'

def get_odds_url(race_id):
    """オッズページのURLを生成"""
    return f'https://race.netkeiba.com/odds/index.html?race_id={race_id}&rf=race_submenu'

# 開催日を取得
def get_kaisai_dates(year, month):
    """
    指定年月のレース開催日を取得
    参考: https://race.netkeiba.com/top/calendar.html?year={year}&month={month}
    
    Args:
        year: 年（例: 2024）
        month: 月（例: 10）
    
    Returns:
        list[str]: 開催日のリスト（例: ['20241005', '20241006', ...]）
    """
    url = f'https://race.netkeiba.com/top/calendar.html?year={year}&month={month}'
    response = safe_request(url)
    
    if not response:
        print(f"開催日取得失敗: {url}")
        return []
    
    try:
        # lxmlパーサーを使用（参考コード準拠）、なければhtml.parserにフォールバック
        try:
            soup = BeautifulSoup(response.content, 'lxml')
        except:
            soup = BeautifulSoup(response.content, 'html.parser')
        kaisai_dates = []
        
        for a_tag in soup.select('.Calendar_Table .Week > td > a'):
            href = a_tag.get('href', '')
            match = re.search(r'kaisai_date=(\d+)', href)
            if match:
                kaisai_dates.append(match.group(1))
        
        return kaisai_dates
    except Exception as e:
        print(f"開催日解析エラー: {e}")
        return []

# レースIDを取得（race_list_sub.htmlを使用）
def get_race_ids(kaisai_date):
    """
    指定日のレースID一覧を取得
    race_list_sub.htmlから取得（実際のレースリストが含まれる）
    
    Args:
        kaisai_date: 開催日（例: '20241123'）
    
    Returns:
        list[str]: レースIDのリスト
    """
    # race_list_sub.htmlから取得（実際のレースリストが含まれる）
    url = f'https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={kaisai_date}'
    response = safe_request(url)
    
    if not response:
        print(f"レースID取得失敗: {url}")
        return []
    
    try:
        # lxmlパーサーを使用（参考コード準拠）、なければhtml.parserにフォールバック
        try:
            soup = BeautifulSoup(response.content, 'lxml')
        except:
            soup = BeautifulSoup(response.content, 'html.parser')
        race_ids = []
        
        # 方法1: id="myhorse_{race_id}" パターンから取得
        for elem in soup.find_all(id=re.compile(r'myhorse_\d+')):
            elem_id = elem.get('id', '')
            match = re.search(r'myhorse_(\d+)', elem_id)
            if match:
                race_id = match.group(1)
                if race_id not in race_ids:
                    race_ids.append(race_id)
        
        # 方法2: リンクから取得（フォールバック）
        if not race_ids:
            for a_tag in soup.find_all('a', href=True):
                href = a_tag.get('href', '')
                match = re.search(r'race_id=(\d+)', href)
                if match:
                    race_id = match.group(1)
                    if race_id not in race_ids:
                        race_ids.append(race_id)
        
        return sorted(race_ids)  # ソートして返す
    except Exception as e:
        print(f"レースID解析エラー: {e}")
        return []

# netkeibaから複勝オッズ取得（全頭対応）
def get_fukusho_odds(race_id):
    """
    指定レースの全頭の複勝オッズを取得
    
    Args:
        race_id: レースID
    
    Returns:
        dict: {馬番: オッズ} の辞書
    """
    odds_url = get_odds_url(race_id)
    response = safe_request(odds_url)
    if not response:
        print(f"オッズ取得失敗: {odds_url}")
        return {}
    
    try:
        start_parse = time.time()
        try:
            soup = BeautifulSoup(response.content, 'lxml')
        except:
            soup = BeautifulSoup(response.content, 'html.parser')
        if (time.time() - start_parse) > config.get('timeouts', {}).get('html_parse', 5):
            print("HTMLパースがタイムアウトしました")
            return {}
        
        odds_dict = {}
        start_table_search = time.time()
        odds_table = soup.select_one('.RaceOdds_HorseList_Table, table#Ninki')
        if not odds_table:
            all_tables = soup.find_all('table')
            for table in all_tables:
                table_text = table.get_text()
                if '複勝' in table_text:
                    odds_table = table
                    break
        if (time.time() - start_table_search) > config.get('timeouts', {}).get('table_search', 2):
            print("オッズテーブル検索がタイムアウトしました")
            return {}
        if not odds_table:
            print("オッズテーブルが見つかりません")
            return {}
        
        table_rows = odds_table.select('tr')
        start_data_extraction = time.time()
        for row in table_rows:
            if row.find('th'):
                continue
            cells = row.select('td')
            if len(cells) < 7:
                continue
            uma_ban = None
            uma_ban_elem = cells[2] if len(cells) > 2 else None
            if uma_ban_elem:
                uma_ban_text = uma_ban_elem.get_text(strip=True)
                if uma_ban_text and uma_ban_text.isdigit():
                    try:
                        uma_ban = int(uma_ban_text)
                    except ValueError:
                        pass
            if not uma_ban:
                uma_ban_elem = row.select_one('td[class*="Umaban"], td.Umaban')
                if uma_ban_elem:
                    uma_ban_text = uma_ban_elem.get_text(strip=True)
                    if uma_ban_text.isdigit():
                        try:
                            uma_ban = int(uma_ban_text)
                        except ValueError:
                            pass
            if not uma_ban:
                continue
            fukusho_odds_elem = None
            if len(cells) >= 7:
                fukusho_odds_elem = cells[6]
            if not fukusho_odds_elem:
                odds_cells = row.select('td.Odds, td[class*="Odds"]')
                if len(odds_cells) >= 2:
                    fukusho_odds_elem = odds_cells[1]
            if fukusho_odds_elem:
                odds_text = fukusho_odds_elem.get_text(strip=True)
                if odds_text and odds_text not in ['---.-', '---', '--', '', '---']:
                    try:
                        odds_value = float(odds_text.replace(',', ''))
                        if 1.0 <= odds_value <= 100.0:
                            odds_dict[uma_ban] = odds_value
                    except (ValueError, AttributeError):
                        continue
        if (time.time() - start_data_extraction) > config.get('timeouts', {}).get('data_extraction', 3):
            print("データ抽出がタイムアウトしました")
            return {}
        return odds_dict if odds_dict else {}
    except Exception as e:
        print(f"オッズ解析エラー: {e}")
        return {}

# 特徴量生成（30個: 馬番、斤量、前走着順など）
def generate_features(horse_data):
    """
    馬データから特徴量を生成
    
    Args:
        horse_data: 馬のデータ辞書
    
    Returns:
        pd.DataFrame: 特徴量のDataFrame
    """
    features = [
        horse_data.get('uma_ban', 0),
        horse_data.get('kinryo', 0),
        horse_data.get('kishu_win_rate', 0),
        horse_data.get('zen_sho_chakushun', 0),
        horse_data.get('zen_sho_agari', 0),
        horse_data.get('kyori_teki', 0),
        # ... (全30個: 実際はJRA-VAN/netkeibaから取得)
        # 残りの特徴量は後で実装
    ]
    return pd.DataFrame([features])

# 複勝確率計算（LightGBMモデル）
def predict_fukusho_prob(features, race_id=None, race_url=None, horse_number=None):
    """
    複勝確率を予測
    
    Args:
        features: 特徴量のDataFrame
        race_id: レースID（オッズ取得用）
        race_url: レースURL（後方互換性のため残す）
        horse_number: 馬番（オッズ取得用）
    
    Returns:
        tuple: (確率, EV, オッズ)
    """
    if not os.path.exists('model.pkl'):
        # 初回学習（サンプルデータでデモ）
        train_data = pd.DataFrame({
            'feature1': [1,2,3]*100, 'target': [1,0,1]*100  # ダミー
        })
        model = lgb.LGBMClassifier()
        model.fit(train_data.drop('target', axis=1), train_data['target'])
        joblib.dump(model, 'model.pkl')
    else:
        model = joblib.load('model.pkl')
    
    base_prob = model.predict_proba(features)[0][1]  # 陽性確率
    
    # オッズを取得
    odds = 1.0
    if race_id:
        odds_dict = get_fukusho_odds(race_id)
        if horse_number and horse_number in odds_dict:
            odds = odds_dict[horse_number]
        elif odds_dict:
            # 馬番が指定されていない場合は最初のオッズを使用
            odds = list(odds_dict.values())[0]
    
    # オッズ暗黙確率と組み合わせ
    if odds > 0:
        odds_implied_prob = 1.0 / odds
        # モデル予測とオッズ暗黙確率を組み合わせ
        final_prob = 0.7 * base_prob + 0.3 * odds_implied_prob
    else:
        final_prob = base_prob
    
    # EV計算
    ev = final_prob * odds if odds > 0 else 0
    
    return final_prob, ev, odds

# 連続的中カウンター（簡易）
renzoku_count = 0

def check_alert(race_id, horse_number=None):
    """
    レースをチェックして通知を送信
    
    Args:
        race_id: レースID
        horse_number: 馬番（オプション）
    """
    global renzoku_count
    if config['max_renzoku'] <= renzoku_count:
        return  # 自動休み
    
    # 馬データ取得（デモ: 固定）
    # TODO: 実際のレースデータを取得する機能を実装
    horse_data = {
        'uma_ban': horse_number or 7,
        'kinryo': 55,
        'kishu_win_rate': 0.25,
        'zen_sho_chakushun': 3,
        'zen_sho_agari': 2.5,
        'kyori_teki': 0.8,
    }
    features = generate_features(horse_data)
    prob, ev, odds = predict_fukusho_prob(features, race_id=race_id, horse_number=horse_number)
    
    if prob >= config['fukusho_threshold'] and odds >= config['odds_threshold'] and ev >= 1.10:
        message = f"{race_id} {horse_number or 7}番 複勝{prob*100:.1f}% オッズ{odds:.2f} EV{ev:.2f} 投資{config['investment_per_bet']}円"
        send_discord_notify(message)
        renzoku_count += 1  # 的中想定（実際は結果確認で+1）

# メインループ（発走7分前チェック）
def job():
    """定期実行ジョブ"""
    now = datetime.now()
    if now.weekday() >= 5:  # 土日
        # 当日のレースを取得
        today = now.date()
        kaisai_date = today.strftime('%Y%m%d')
        race_ids = get_race_ids(kaisai_date)
        
        if not race_ids:
            return
        
        for race_id in race_ids:
            # TODO: 発走7分前判定を正確に実装
            # 現在は簡易版（実際の発走時刻を取得する必要がある）
            if datetime.now().minute == 53:  # 例
                check_alert(race_id)

schedule.every(1).minutes.do(job)

if __name__ == '__main__':
    while True:
        schedule.run_pending()
        time.sleep(1)
