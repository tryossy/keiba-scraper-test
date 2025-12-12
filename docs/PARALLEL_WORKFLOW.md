# 並列実行ワークフローの説明

## 概要

`scrape-monthly-parallel.yml` は、月次スクレイピングを**週単位に分割**して並列実行するワークフローです。

## 通常版との比較

| 項目 | scrape-monthly.yml | scrape-monthly-parallel.yml |
|-----|-------------------|----------------------------|
| **実行方式** | 1ジョブで月全体を処理 | 複数ジョブで週単位に分割 |
| **実行時間** | 3-6時間 | 1-2時間（並列実行） |
| **タイムアウト対策** | なし | ✓ 各ジョブが短時間 |
| **失敗時の影響** | 全てやり直し | 失敗した週のみ再実行可能 |
| **サーバー負荷** | 低（1ジョブのみ） | 中（最大4ジョブ同時） |

---

## ワークフローの仕組み

### 3つのジョブ構成

```
[ジョブ1: generate-matrix]
  期間を週単位に分割
  ↓
[ジョブ2: scrape] （並列実行）
  week1: 12/1-12/2
  week2: 12/8-12/9    ← 最大4ジョブ同時実行
  week3: 12/15-12/16
  week4: 12/22-12/23
  ↓
[ジョブ3: combine]
  全週のデータを結合
```

---

### ジョブ1: generate-matrix

**役割**: 指定月を週単位に分割してマトリックスを生成

**出力例**:
```json
[
  {
    "name": "week1",
    "start_date": "2024-12-07",
    "end_date": "2024-12-08",
    "year_month": "2024-12"
  },
  {
    "name": "week2",
    "start_date": "2024-12-14",
    "end_date": "2024-12-15",
    "year_month": "2024-12"
  },
  ...
]
```

**分割ロジック**:
- 土曜日〜日曜日を1週として認識
- 各週を独立したジョブとして実行

---

### ジョブ2: scrape（並列実行）

**役割**: 各週のデータを並列スクレイピング

**並列実行の設定**:
```yaml
strategy:
  max-parallel: 4     # 最大4ジョブ同時実行
  fail-fast: false    # 1つ失敗しても他は続行
  matrix:
    range: ${{ fromJson(needs.generate-matrix.outputs.date_ranges) }}
```

**出力**:
- `race_data_2024-12_week1.csv`
- `race_data_2024-12_week2.csv`
- `race_data_2024-12_week3.csv`
- `race_data_2024-12_week4.csv`

各ファイルは Google Drive に個別保存されます。

---

### ジョブ3: combine

**役割**: 全週のデータを1つのCSVに結合

**処理**:
1. Google Drive から全週のCSVをダウンロード
2. pandas で結合
3. 重複削除（race_id でユニーク化）
4. `race_data_combined.csv` として保存
5. Google Drive にアップロード

---

## 使い方

### 手動実行（週分割あり）

1. GitHub リポジトリ → Actions
2. "Monthly Horse Racing Data Scrape (Parallel)" を選択
3. "Run workflow" をクリック
4. 入力:
   - `year_month`: 2024-12
   - `split_weeks`: true
5. "Run workflow" をクリック

### 手動実行（月全体を1ジョブ）

同じ手順で `split_weeks` を `false` に設定

### 自動実行（スケジュール）

毎月1日 午前2時（UTC）に自動実行（週分割あり）

---

## メリット

### 1. タイムアウト対策

**問題**: 1ヶ月分のスクレイピングが6時間を超える場合、GitHub Actionsがタイムアウト

**解決**: 週単位に分割することで、各ジョブは1-2時間で完了

---

### 2. 実行時間の短縮

**通常版**: 順次実行で3-6時間

**並列版**: 最大4ジョブ同時実行で1-2時間

**例**:
- 通常版: week1(60分) → week2(60分) → week3(60分) → week4(60分) = **240分**
- 並列版: week1, week2, week3, week4 同時実行 = **60分**

---

### 3. 失敗時の部分再実行

**問題**: 通常版で week3 が失敗すると、全てやり直し

**解決**: 並列版では week3 のみ再実行可能

**再実行方法**:
1. 失敗したジョブを確認
2. "Re-run failed jobs" をクリック
3. 失敗した週のみ再実行

---

### 4. サーバー負荷の分散

**並列実行でもレート制限を守る**:
- 各ジョブ: 1.5秒間隔（変更不可）
- 最大4ジョブ同時実行
- 合計: 約6リクエスト/秒（許容範囲内）

---

## デメリットと対策

### デメリット1: サーバー負荷が増加

**対策**: `max-parallel: 4` で同時実行数を制限

### デメリット2: ジョブ数が増える

**影響**: GitHub Actionsの同時実行数制限（Publicリポジトリ: 20ジョブ）

**対策**: 月に最大4-5週なので問題なし

### デメリット3: データ結合の手間

**対策**: `combine` ジョブで自動結合

---

## カスタマイズ

### 同時実行数を変更

```yaml
strategy:
  max-parallel: 2  # 2ジョブ同時実行（サーバー負荷を抑える）
```

### 日単位に分割

`generate-matrix` ジョブの Python スクリプトを変更:

```python
# 日単位で分割
current_date = first_day
while current_date <= last_day:
    # 土日のみ
    if current_date.weekday() in [5, 6]:
        date_ranges.append({
            'name': current_date.strftime('%Y%m%d'),
            'start_date': current_date.strftime('%Y-%m-%d'),
            'end_date': current_date.strftime('%Y-%m-%d'),
            'year_month': year_month
        })
    current_date += timedelta(days=1)
```

### 競馬場単位に分割

```python
# 競馬場コード
place_codes = {
    '01': '札幌', '02': '函館', '03': '福島', '04': '新潟',
    '05': '東京', '06': '中山', '07': '中京', '08': '京都',
    '09': '阪神', '10': '小倉'
}

for place_code, place_name in place_codes.items():
    date_ranges.append({
        'name': place_name,
        'start_date': first_day.strftime('%Y-%m-%d'),
        'end_date': last_day.strftime('%Y-%m-%d'),
        'year_month': year_month,
        'place_code': place_code  # 追加パラメータ
    })
```

---

## トラブルシューティング

### エラー1: "Matrix contains too many jobs"

**原因**: マトリックスジョブ数が256を超えた

**解決策**:
- 週単位に分割（通常4-5ジョブ）
- 日単位は避ける（30ジョブ）

---

### エラー2: 一部のジョブが失敗

**症状**: week2 のジョブだけ失敗

**原因**: その週にレースが開催されていない、またはネットワークエラー

**解決策**:
1. 失敗したジョブのログを確認
2. "Re-run failed jobs" で再実行
3. レースがない週は無視してOK

---

### エラー3: combine ジョブが失敗

**原因**: Google Drive に週次データがない

**解決策**:
1. scrape ジョブが成功したか確認
2. RCLONE_CONFIG が正しく設定されているか確認
3. Google Drive の認証トークンが有効か確認

---

## 実行結果の確認

### GitHub Actions

1. Actions タブ → 実行履歴
2. 各ジョブの実行ログを確認
3. 成功/失敗の状態を確認

### Google Drive

```
keiba-data/
├── 2024-12/
│   ├── race_data_2024-12_week1.csv
│   ├── race_data_2024-12_week2.csv
│   ├── race_data_2024-12_week3.csv
│   ├── race_data_2024-12_week4.csv
│   └── race_data_combined.csv  ← 結合データ
```

---

## どちらのワークフローを使うべきか

### scrape-monthly.yml（通常版）を使う場合

- ✓ データ量が少ない（1ヶ月で100レース未満）
- ✓ サーバー負荷を最小限にしたい
- ✓ シンプルな構成が良い

### scrape-monthly-parallel.yml（並列版）を使う場合

- ✓ データ量が多い（1ヶ月で200レース以上）
- ✓ タイムアウトが心配
- ✓ 実行時間を短縮したい
- ✓ 一部失敗しても再実行したい

---

## まとめ

**並列実行ワークフローの特徴**:

| 項目 | 詳細 |
|-----|------|
| **ジョブ分割** | 週単位（カスタマイズ可能） |
| **並列実行数** | 最大4ジョブ |
| **実行時間** | 1-2時間（通常版の1/3） |
| **タイムアウト対策** | ✓ 各ジョブが短時間 |
| **部分再実行** | ✓ 失敗した週のみ |
| **データ結合** | ✓ 自動（combine ジョブ） |

**推奨**: データ量が多い場合は並列版を使用
