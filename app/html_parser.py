"""
HTMLパーサー - レースHTMLから特徴量を抽出

data/html/race/*.binファイルから馬情報とレース情報を抽出
"""
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
import re


class RaceHTMLParser:
    """レースHTMLパーサー"""

    def __init__(self, html_dir: str = 'data/html/race'):
        """
        Args:
            html_dir: HTMLファイルの格納ディレクトリ
        """
        self.html_dir = Path(html_dir)

    def parse_race_file(self, race_id: str) -> Tuple[List[Dict], Dict]:
        """
        レースHTMLファイルをパースして馬情報とレース情報を抽出

        Args:
            race_id: レースID

        Returns:
            tuple: (horses_info, race_info)
        """
        file_path = self.html_dir / f'{race_id}.bin'

        if not file_path.exists():
            raise FileNotFoundError(f"レースファイルが見つかりません: {file_path}")

        # HTMLファイルを読み込み
        with open(file_path, 'rb') as f:
            html_bytes = f.read()

        # エンコーディングを試す（EUC-JP → UTF-8 → CP932）
        html = None
        for encoding in ['euc-jp', 'utf-8', 'cp932']:
            try:
                html = html_bytes.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if html is None:
            raise ValueError(f"HTMLのデコードに失敗: {race_id}")

        soup = BeautifulSoup(html, 'html.parser')

        # レース情報を抽出
        race_info = self._parse_race_info(soup, race_id)

        # 馬情報を抽出
        horses_info = self._parse_horses_info(soup, race_id)

        return horses_info, race_info

    def _parse_race_info(self, soup: BeautifulSoup, race_id: str) -> Dict:
        """レース情報を抽出"""
        race_info = {
            'race_id': race_id,
            'race_name': '',
            'distance': 0,
            'track_type': '',  # 芝/ダート
            'weather': '',
            'track_condition': '',
            'num_horses': 0,
        }

        try:
            # レース名
            title = soup.find('h1', class_='RaceName')
            if title:
                race_info['race_name'] = title.get_text(strip=True)

            # 距離・コース種別
            race_data = soup.find('div', class_='RaceData01')
            if race_data:
                text = race_data.get_text()

                # 距離（例: ダ1200m, 芝2000m）
                distance_match = re.search(r'([芝ダ障])(\d+)m', text)
                if distance_match:
                    track_type = distance_match.group(1)
                    race_info['distance'] = int(distance_match.group(2))
                    if track_type == '芝':
                        race_info['track_type'] = 'turf'
                    elif track_type == 'ダ':
                        race_info['track_type'] = 'dirt'
                    else:
                        race_info['track_type'] = 'obstacle'

                # 天気
                weather_match = re.search(r'天候\s*:\s*(\S+)', text)
                if weather_match:
                    race_info['weather'] = weather_match.group(1)

                # 馬場状態
                condition_match = re.search(r'馬場\s*:\s*(\S+)', text)
                if condition_match:
                    race_info['track_condition'] = condition_match.group(1)

        except Exception as e:
            print(f"[警告] レース情報の抽出エラー ({race_id}): {e}")

        return race_info

    def _parse_horses_info(self, soup: BeautifulSoup, race_id: str) -> List[Dict]:
        """馬情報を抽出"""
        horses_info = []

        try:
            # レース結果テーブルを検索（結果ページ）
            table = soup.find('table', class_='race_table_01')

            if not table:
                # 開催前の場合は出馬表テーブル
                table = soup.find('table', class_='Shutuba_Table')

            if not table:
                # 別パターンの出馬表
                table = soup.find('table', summary='出馬表')

            if not table:
                print(f"[警告] 馬情報テーブルが見つかりません: {race_id}")
                return horses_info

            rows = table.find_all('tr')

            for row in rows:
                cells = row.find_all('td')

                if len(cells) < 8:
                    continue

                try:
                    horse_info = self._parse_horse_row(cells, race_id)
                    if horse_info:
                        horses_info.append(horse_info)
                except Exception as e:
                    print(f"[警告] 馬情報の抽出エラー: {e}")
                    continue

        except Exception as e:
            print(f"[エラー] 馬情報テーブルの抽出エラー ({race_id}): {e}")

        return horses_info

    def _parse_horse_row(self, cells: List, race_id: str) -> Optional[Dict]:
        """馬情報の1行をパース

        レース結果テーブルのセル配置（race_table_01）:
        [0]着順 [1]枠 [2]馬番 [3]馬名 [4]性齢 [5]斤量 [6]騎手 [7]タイム
        [8]着差 [9]通過順位 [10]上がり [11]単勝 [12]人気 [13]馬体重
        [14]馬体重変化 [15]調教師 ...
        """
        horse_info = {}

        try:
            # 枠番 (1)
            waku = cells[1].get_text(strip=True) if len(cells) > 1 else ''
            if waku:
                try:
                    horse_info['waku'] = int(waku)
                except ValueError:
                    pass

            # 馬番 (2)
            umaban = cells[2].get_text(strip=True) if len(cells) > 2 else ''
            if umaban:
                try:
                    horse_info['umaban'] = int(umaban)
                except ValueError:
                    pass

            # 馬名 (3)
            if len(cells) > 3:
                horse_link = cells[3].find('a')
                if horse_link:
                    horse_info['horse_name'] = horse_link.get_text(strip=True)
                else:
                    horse_info['horse_name'] = cells[3].get_text(strip=True)

            # 性齢 (4) 例: 牡2, 牝4
            if len(cells) > 4:
                sei_rei = cells[4].get_text(strip=True)
                match = re.match(r'([牡牝セ])(\d+)', sei_rei)
                if match:
                    horse_info['sex'] = match.group(1)
                    horse_info['age'] = int(match.group(2))

            # 斤量 (5)
            if len(cells) > 5:
                kinryo = cells[5].get_text(strip=True)
                try:
                    horse_info['weight'] = float(kinryo)
                except ValueError:
                    pass

            # 騎手 (6)
            if len(cells) > 6:
                jockey_link = cells[6].find('a')
                if jockey_link:
                    horse_info['jockey_name'] = jockey_link.get_text(strip=True)
                else:
                    horse_info['jockey_name'] = cells[6].get_text(strip=True)

            # 単勝オッズ (11 or 12)
            odds_idx = 12 if len(cells) > 12 else 11 if len(cells) > 11 else None
            if odds_idx:
                odds_text = cells[odds_idx].get_text(strip=True)
                try:
                    horse_info['odds'] = float(odds_text)
                except ValueError:
                    horse_info['odds'] = None

            # 馬体重 (14)
            if len(cells) > 14:
                horse_weight_text = cells[14].get_text(strip=True)
                match = re.match(r'(\d+)\(([+-]?\d+)\)', horse_weight_text)
                if match:
                    horse_info['horse_weight'] = int(match.group(1))
                    horse_info['horse_weight_diff'] = int(match.group(2))

            # 調教師 (18 or 19)
            trainer_idx = 18 if len(cells) > 18 else None
            if trainer_idx:
                trainer_text = cells[trainer_idx].get_text(strip=True)
                # 調教師名から地域記号を除去（例: [東]藤沢和雄 → 藤沢和雄）
                trainer_match = re.search(r'\[.\](.+)', trainer_text)
                if trainer_match:
                    horse_info['trainer_name'] = trainer_match.group(1)
                else:
                    horse_info['trainer_name'] = trainer_text

            return horse_info if 'horse_name' in horse_info else None

        except Exception as e:
            print(f"[エラー] 馬行のパース失敗: {e}")
            return None


class ShutubaHTMLParser:
    """出馬表HTMLパーサー（開催前レース用）"""

    def __init__(self, html_dir: str = 'data/html/shutuba'):
        """
        Args:
            html_dir: 出馬表HTMLファイルの格納ディレクトリ
        """
        self.html_dir = Path(html_dir)

    def parse_shutuba_file(self, race_id: str) -> Tuple[List[Dict], Dict]:
        """
        出馬表HTMLファイルをパースして馬情報とレース情報を抽出

        Args:
            race_id: レースID

        Returns:
            tuple: (horses_info, race_info)
        """
        file_path = self.html_dir / f'{race_id}.bin'

        if not file_path.exists():
            raise FileNotFoundError(f"出馬表ファイルが見つかりません: {file_path}")

        # HTMLファイルを読み込み
        with open(file_path, 'rb') as f:
            html_bytes = f.read()

        # エンコーディングを試す（EUC-JP → UTF-8 → CP932）
        html = None
        for encoding in ['euc-jp', 'utf-8', 'cp932']:
            try:
                html = html_bytes.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if html is None:
            raise ValueError(f"HTMLのデコードに失敗: {race_id}")

        soup = BeautifulSoup(html, 'html.parser')

        # レース情報を抽出
        race_info = self._parse_race_info_shutuba(soup, race_id)

        # 馬情報を抽出
        horses_info = self._parse_horses_info_shutuba(soup, race_id)

        return horses_info, race_info

    def _parse_race_info_shutuba(self, soup: BeautifulSoup, race_id: str) -> Dict:
        """出馬表からレース情報を抽出（拡張版）"""
        race_info = {
            'race_id': race_id,
            'race_name': '',
            'distance': 0,
            'track_type': '',
            'surface': '',  # 芝/ダート/障害
            'direction': '',  # 右/左/直線
            'weather': '',
            'track_condition': '',
            'num_horses': 0,
            'racetrack': '',  # 競馬場名
            'race_number': 0,  # レース番号
            'grade': '',  # G1, G2, G3, L, オープンなど
            'race_class': '',  # 競争条件
            'race_symbols': [],  # レース記号（牝、混、ハンデなど）
        }

        try:
            # レース名
            title = soup.find('h1', class_='RaceName')
            if title:
                race_info['race_name'] = title.get_text(strip=True)

                # グレード情報（レース名に含まれる場合）
                if 'G1' in race_info['race_name'] or 'GI' in race_info['race_name']:
                    race_info['grade'] = 'G1'
                elif 'G2' in race_info['race_name'] or 'GII' in race_info['race_name']:
                    race_info['grade'] = 'G2'
                elif 'G3' in race_info['race_name'] or 'GIII' in race_info['race_name']:
                    race_info['grade'] = 'G3'

            # RaceData01: 距離・コース種別・回り
            race_data1 = soup.find('div', class_='RaceData01')
            if race_data1:
                text = race_data1.get_text()

                # 距離（例: ダ1200m, 芝2000m(右)）
                distance_match = re.search(r'([芝ダ障])(\d+)m', text)
                if distance_match:
                    surface_char = distance_match.group(1)
                    race_info['distance'] = int(distance_match.group(2))

                    if surface_char == '芝':
                        race_info['track_type'] = 'turf'
                        race_info['surface'] = '芝'
                    elif surface_char == 'ダ':
                        race_info['track_type'] = 'dirt'
                        race_info['surface'] = 'ダート'
                    else:
                        race_info['track_type'] = 'obstacle'
                        race_info['surface'] = '障害'

                # 回り方向（例: (右)、(左)、(直線)）
                if '(右)' in text or '（右）' in text:
                    race_info['direction'] = '右'
                elif '(左)' in text or '（左）' in text:
                    race_info['direction'] = '左'
                elif '(直線)' in text or '（直線）' in text:
                    race_info['direction'] = '直線'

            # RaceData02: 競馬場、回次、日数、競争条件など
            race_data2 = soup.find('div', class_='RaceData02')
            if race_data2:
                spans = race_data2.find_all('span')

                if len(spans) >= 2:
                    # 0番目: 開催回次（例: "5回"）
                    # 1番目: 競馬場名（例: "中山"）
                    race_info['racetrack'] = spans[1].get_text(strip=True) if len(spans) > 1 else ''

                    # レース記号を収集（牝、混、ハンデなど）
                    for span in spans:
                        text = span.get_text(strip=True)
                        if text in ['牝', '牡', '混', 'ハンデ', '定量', '別定', '馬齢',
                                   '見習騎手', 'せん', '国際', '指定', '特指', '抽選']:
                            race_info['race_symbols'].append(text)

                        # 競争条件（例: "サラ系2歳"）
                        if 'サラ' in text or '系' in text:
                            race_info['race_class'] = text

                        # 出走頭数（例: "14頭"）
                        if '頭' in text:
                            num_match = re.search(r'(\d+)頭', text)
                            if num_match:
                                race_info['num_horses'] = int(num_match.group(1))

            # race_idから競馬場コードとレース番号を抽出
            # race_id形式: YYYYMMDD + 競馬場(2) + 開催回(2) + 開催日(2) + レース番号(2)
            if len(race_id) == 12:
                try:
                    race_info['race_number'] = int(race_id[10:12])
                except:
                    pass

        except Exception as e:
            print(f"[警告] レース情報の抽出エラー ({race_id}): {e}")
            import traceback
            traceback.print_exc()

        return race_info

    def _parse_horses_info_shutuba(self, soup: BeautifulSoup, race_id: str) -> List[Dict]:
        """出馬表から馬情報を抽出"""
        horses_info = []

        try:
            # 出馬表テーブル
            table = soup.find('table', class_='Shutuba_Table')

            if not table:
                print(f"[警告] 出馬表テーブルが見つかりません: {race_id}")
                return horses_info

            # HorseList行を検索
            tbody = table.find('tbody')
            if tbody:
                rows = tbody.find_all('tr', class_='HorseList')
            else:
                rows = table.find_all('tr', class_='HorseList')

            for row in rows:
                cells = row.find_all('td')

                if len(cells) < 8:
                    continue

                try:
                    horse_info = self._parse_shutuba_horse_row(cells, race_id)
                    if horse_info:
                        horses_info.append(horse_info)
                except Exception as e:
                    print(f"[警告] 馬情報の抽出エラー: {e}")
                    continue

        except Exception as e:
            print(f"[エラー] 馬情報テーブルの抽出エラー ({race_id}): {e}")

        return horses_info

    def _parse_shutuba_horse_row(self, cells: List, race_id: str) -> Optional[Dict]:
        """出馬表の馬情報1行をパース

        出馬表テーブルのセル配置（HorseList行）:
        [0]枠番 [1]馬番 [2]チェック [3]馬名 [4]性齢 [5]斤量
        [6]騎手 [7]調教師 [8]馬体重 [9]人気（オッズ前は---.-）
        """
        horse_info = {}

        try:
            # 枠番 (0)
            if len(cells) > 0:
                waku_text = cells[0].get_text(strip=True)
                try:
                    horse_info['waku'] = int(waku_text)
                except ValueError:
                    pass

            # 馬番 (1)
            if len(cells) > 1:
                umaban_text = cells[1].get_text(strip=True)
                try:
                    horse_info['umaban'] = int(umaban_text)
                except ValueError:
                    pass

            # 馬名 (3) - HorseInfoクラス内
            if len(cells) > 3:
                horse_cell = cells[3]
                # span.HorseNameを探す
                horse_name_span = horse_cell.find('span', class_='HorseName')
                if horse_name_span:
                    horse_info['horse_name'] = horse_name_span.get_text(strip=True)
                else:
                    # リンクから取得
                    horse_link = horse_cell.find('a')
                    if horse_link:
                        horse_info['horse_name'] = horse_link.get_text(strip=True)
                    else:
                        horse_info['horse_name'] = horse_cell.get_text(strip=True)

            # 性齢 (4) - Bareiクラス
            if len(cells) > 4:
                barei_text = cells[4].get_text(strip=True)
                match = re.match(r'([牡牝セ])(\d+)', barei_text)
                if match:
                    horse_info['sex'] = match.group(1)
                    horse_info['age'] = int(match.group(2))

            # 斤量 (5)
            if len(cells) > 5:
                kinryo_text = cells[5].get_text(strip=True)
                try:
                    horse_info['weight'] = float(kinryo_text)
                except ValueError:
                    pass

            # 騎手 (6) - Jockeyクラス
            if len(cells) > 6:
                jockey_cell = cells[6]
                jockey_link = jockey_cell.find('a')
                if jockey_link:
                    horse_info['jockey_name'] = jockey_link.get_text(strip=True)
                else:
                    horse_info['jockey_name'] = jockey_cell.get_text(strip=True)

            # 調教師 (7) - Trainerクラス
            if len(cells) > 7:
                trainer_cell = cells[7]
                trainer_link = trainer_cell.find('a')
                if trainer_link:
                    trainer_text = trainer_link.get_text(strip=True)
                else:
                    trainer_text = trainer_cell.get_text(strip=True)

                # 調教師名から地域記号を除去（例: [東]藤沢和雄 → 藤沢和雄）
                trainer_match = re.search(r'\[.\](.+)', trainer_text)
                if trainer_match:
                    horse_info['trainer_name'] = trainer_match.group(1)
                else:
                    horse_info['trainer_name'] = trainer_text

            # 馬体重 (8) - Weightクラス
            if len(cells) > 8:
                weight_text = cells[8].get_text(strip=True)
                match = re.match(r'(\d+)\(([+-]?\d+)\)', weight_text)
                if match:
                    horse_info['horse_weight'] = int(match.group(1))
                    horse_info['horse_weight_diff'] = int(match.group(2))

            # オッズは別途取得（出馬表時点ではなし）
            horse_info['odds'] = None

            return horse_info if 'horse_name' in horse_info else None

        except Exception as e:
            print(f"[エラー] 馬行のパース失敗: {e}")
            return None


class OddsFetcher:
    """オッズ取得クラス（開催前レース用）"""

    def __init__(self):
        """初期化"""
        pass

    def fetch_odds(self, race_id: str) -> Dict[str, float]:
        """
        レースの単勝オッズを取得

        Args:
            race_id: レースID

        Returns:
            dict: {馬番: オッズ}
        """
        import requests
        import time
        from app.utils.request_manager import make_request

        odds_url = f'https://race.netkeiba.com/odds/index.html?race_id={race_id}&rf=race_submenu'

        try:
            response = make_request(odds_url)
            if response is None:
                print(f"[エラー] オッズページの取得に失敗: {race_id}")
                return {}

            soup = BeautifulSoup(response.content, 'html.parser')

            odds_dict = {}

            # 単勝オッズテーブルを検索
            odds_table = soup.find('table', class_='Odds_Table')
            if not odds_table:
                print(f"[警告] オッズテーブルが見つかりません: {race_id}")
                return {}

            rows = odds_table.find_all('tr')

            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 2:
                    continue

                # 馬番
                umaban_cell = cells[0].get_text(strip=True)
                try:
                    umaban = int(umaban_cell)
                except ValueError:
                    continue

                # オッズ
                odds_cell = cells[1].get_text(strip=True)
                try:
                    odds = float(odds_cell)
                    odds_dict[umaban] = odds
                except ValueError:
                    continue

            return odds_dict

        except Exception as e:
            print(f"[エラー] オッズ取得エラー ({race_id}): {e}")
            return {}


def parse_race(race_id: str, fetch_odds: bool = False, html_dir: str = 'data/html/race') -> Tuple[List[Dict], Dict]:
    """
    レースIDから馬情報とレース情報を抽出（便利関数）

    Args:
        race_id: レースID
        fetch_odds: オッズを取得するか（開催前レース用）
        html_dir: HTMLディレクトリ

    Returns:
        tuple: (horses_info, race_info)
    """
    parser = RaceHTMLParser(html_dir=html_dir)
    horses_info, race_info = parser.parse_race_file(race_id)

    # オッズを取得する場合
    if fetch_odds:
        fetcher = OddsFetcher()
        odds_dict = fetcher.fetch_odds(race_id)

        # 馬情報にオッズを追加
        for horse in horses_info:
            umaban = horse.get('umaban')
            if umaban and umaban in odds_dict:
                horse['odds'] = odds_dict[umaban]
            elif 'odds' not in horse or horse['odds'] is None:
                # デフォルトオッズ
                horse['odds'] = 5.0

    # オッズがない馬にデフォルト値を設定
    for horse in horses_info:
        if 'odds' not in horse or horse['odds'] is None:
            horse['odds'] = 5.0

    race_info['num_horses'] = len(horses_info)

    return horses_info, race_info


def parse_shutuba(race_id: str, fetch_odds: bool = True, html_dir: str = 'data/html/shutuba') -> Tuple[List[Dict], Dict]:
    """
    出馬表から馬情報とレース情報を抽出（便利関数）

    Args:
        race_id: レースID
        fetch_odds: オッズを取得するか（デフォルト: True）
        html_dir: 出馬表HTMLディレクトリ

    Returns:
        tuple: (horses_info, race_info)
    """
    parser = ShutubaHTMLParser(html_dir=html_dir)
    horses_info, race_info = parser.parse_shutuba_file(race_id)

    # オッズを取得する場合
    if fetch_odds:
        fetcher = OddsFetcher()
        odds_dict = fetcher.fetch_odds(race_id)

        # 馬情報にオッズを追加
        for horse in horses_info:
            umaban = horse.get('umaban')
            if umaban and umaban in odds_dict:
                horse['odds'] = odds_dict[umaban]
            elif 'odds' not in horse or horse['odds'] is None:
                # デフォルトオッズ（オッズ取得失敗時）
                horse['odds'] = 5.0
    else:
        # オッズ取得しない場合はデフォルト値
        for horse in horses_info:
            if 'odds' not in horse or horse['odds'] is None:
                horse['odds'] = 5.0

    race_info['num_horses'] = len(horses_info)

    return horses_info, race_info
