# パブリックリポジトリ公開ガイド

## 概要

このディレクトリ（`public-repo/`）には、GitHub公開用の競馬スクレイピングツールが含まれています。
**ローカルスクレイパー**（`app/data_scraper_cli.py`）を使用し、GitHub Actions で自動実行します。

---

## 完成したファイル構成

```
public-repo/
├── .github/
│   └── workflows/
│       ├── scrape-monthly-local.yml      # 月次スクレイピング（1ヶ月を順次処理）
│       └── scrape-yearly-parallel.yml    # 年次並列スクレイピング（12ヶ月を最大6並列）
│
├── scrape_monthly_local.py               # ローカルスクレイパーのラッパースクリプト
├── requirements.txt                      # Python依存関係（keibascraper除外済み）
├── README.md                             # リポジトリ説明
├── NOTICE                                # 免責事項（MIT License）
├── LICENSE                               # MITライセンス全文
├── SETUP.md                              # セットアップガイド
├── LOCAL_SCRAPER_SETUP.md                # ローカルスクレイパー使用ガイド
├── PARALLEL_WORKFLOW.md                  # 並列ワークフロー説明（参考：削除済み）
└── YEARLY_WORKFLOW.md                    # 年次並列ワークフロー説明
```

---

## 公開前の準備（必須）

### 1. 必要なファイルをコピー

パブリックリポジトリに公開する前に、以下のファイルを**手動でコピー**してください：

```bash
# app/ ディレクトリ全体をコピー
cp -r app/ public-repo/app/

# config.json.example を作成（シークレット情報を除外）
cat > public-repo/config.json.example << 'EOF'
{
  "request_settings": {
    "min_interval": 1.5,
    "max_requests_per_day": 40,
    "max_requests_weekday": 8000,
    "max_requests_weekend": 150
  }
}
EOF
```

**重要**: `app/config.json` にシークレット情報がある場合は含めないでください！

---

### 2. GitHub Secrets の設定

パブリックリポジトリで以下のシークレットを設定：

1. **Settings → Secrets and variables → Actions → New repository secret**
2. 必要なシークレット：

| シークレット名 | 説明 | 必須 |
|-------------|------|------|
| `RCLONE_CONFIG` | Google Drive 接続設定 | ✓ |

#### RCLONE_CONFIG の作成方法

```bash
# ローカルで rclone を設定
rclone config

# 設定ファイルの内容を取得
cat ~/.config/rclone/rclone.conf

# 上記の内容を RCLONE_CONFIG シークレットに貼り付け
```

---

## ワークフロー説明

### scrape-monthly-local.yml（月次スクレイピング）

**用途**: 毎月1日に前月のデータを自動取得

**特徴**:
- 1ヶ月分を順次処理（シンプル）
- 実行時間: 1-3時間
- サーバー負荷: 低

**手動実行**:
1. GitHub リポジトリ → Actions
2. "Monthly Horse Racing Data Scrape (Local Scraper)" を選択
3. "Run workflow" をクリック
4. 年月を入力（例: `2024-12`）

**出力**:
- Google Drive: `gdrive:keiba-data/html/race/YYYYMM*.bin`
- GitHub Artifacts: ログファイル（7日間保持）

---

### scrape-yearly-parallel.yml（年次並列スクレイピング）

**用途**: 1年分のデータを高速取得

**特徴**:
- 12ヶ月を最大6ジョブ並列実行
- 実行時間: 約2時間（順次の1/6）
- タイムアウト回避（6時間制限内）

**手動実行**:
1. GitHub リポジトリ → Actions
2. "Yearly Horse Racing Data Scrape (12 Months Parallel)" を選択
3. "Run workflow" をクリック
4. 入力:
   - `year`: 2024
   - `start_month`: 1（開始月）
   - `end_month`: 12（終了月）

**実行イメージ**:
```
グループ1（並列実行）:
  2024-01, 2024-02, 2024-03, 2024-04, 2024-05, 2024-06

グループ2（並列実行）:
  2024-07, 2024-08, 2024-09, 2024-10, 2024-11, 2024-12

所要時間: 最大2時間
```

**出力**:
- Google Drive: `gdrive:keiba-data/html/race/YYYYMM*.bin`
- GitHub Artifacts: 各月のログファイル（7日間保持）

---

## 削除・変更された内容

### 削除したファイル

1. **scrape_monthly.py**（keibascraper版）
   - 理由: keibascraperのインストールエラー
   - 代替: scrape_monthly_local.py（ローカルスクレイパー使用）

2. **scrape-monthly.yml**（keibascraper版ワークフロー）
   - 理由: keibascraper版を削除
   - 代替: scrape-monthly-local.yml

3. **scrape-monthly-parallel.yml**（週分割ワークフロー）
   - 理由: ユーザー要望（不要）
   - 代替: 月次と年次のみ使用

4. **combine ジョブ**（年次ワークフローから削除）
   - 理由: ローカルスクレイパーは `.bin` ファイルを出力（CSV結合不要）
   - 変更: 各月の `.bin` ファイルを個別にGoogle Driveへアップロード

### ライセンス整理

**変更前**:
- MIT License（本体）
- Apache-2.0（KeibaScraper帰属）

**変更後**:
- MIT License のみ
- NOTICE に免責事項のみ記載

---

## データ保存先

### Google Drive 構造

```
gdrive:keiba-data/
└── html/
    └── race/
        ├── 202401*.bin    # 2024年1月のレースデータ
        ├── 202402*.bin    # 2024年2月のレースデータ
        ├── ...
        └── 202412*.bin    # 2024年12月のレースデータ
```

### ローカル構造（実行時）

```
data/
└── html/
    └── race/
        └── YYYYMM*.bin    # 実行中に作成
```

---

## 使い方（公開後）

### 初回セットアップ

1. リポジトリをフォーク
2. GitHub Secrets に `RCLONE_CONFIG` を設定
3. 手動実行でテスト

### 定期実行

毎月1日午前2時（UTC）に自動実行されます。

### 手動実行（過去データ取得）

**1ヶ月分**:
- `scrape-monthly-local.yml` を使用
- `year_month`: 2024-12

**1年分**:
- `scrape-yearly-parallel.yml` を使用
- `year`: 2024
- `start_month`: 1
- `end_month`: 12

**特定期間**:
- `scrape-yearly-parallel.yml` を使用
- `year`: 2024
- `start_month`: 4（4月から）
- `end_month`: 6（6月まで）

---

## トラブルシューティング

### エラー1: `app/data_scraper_cli.py が見つかりません`

**原因**: app/ ディレクトリがコピーされていない

**解決策**:
```bash
cp -r app/ public-repo/app/
git add public-repo/app/
git commit -m "Add app directory"
git push
```

---

### エラー2: `RCLONE_CONFIG が設定されていません`

**原因**: GitHub Secrets が未設定

**解決策**:
1. Settings → Secrets and variables → Actions
2. "New repository secret" をクリック
3. Name: `RCLONE_CONFIG`
4. Value: rclone.conf の内容を貼り付け

---

### エラー3: ジョブがタイムアウト（6時間超過）

**原因**: 1ヶ月のデータ量が多すぎる

**解決策**:
- 年次並列ワークフローを使用（12ヶ月分割）
- または、開始月・終了月を分割して複数回実行

---

## 技術仕様

### レート制限

- 最小間隔: 1.5秒（変更不可）
- 平日: 8000リクエスト/日
- 週末: 150リクエスト/日

### 並列実行

- 最大並列数: 6ジョブ（年次ワークフロー）
- サーバー負荷考慮済み

### タイムアウト

- 各ジョブ: 6時間（GitHub Actions制限）
- 月次ワークフロー: 3時間（通常）
- 年次ワークフロー: 2時間（並列実行）

---

## 次のステップ

1. **app/ ディレクトリをコピー**
2. **config.json.example を作成**
3. **GitHub Secrets を設定**
4. **public-repo/ を新しいリポジトリとしてpush**
5. **手動実行でテスト**

---

## 参考資料

- [README.md](README.md): リポジトリ説明
- [SETUP.md](SETUP.md): セットアップガイド
- [LOCAL_SCRAPER_SETUP.md](LOCAL_SCRAPER_SETUP.md): ローカルスクレイパー詳細
- [YEARLY_WORKFLOW.md](YEARLY_WORKFLOW.md): 年次並列ワークフロー詳細

---

## ライセンス

MIT License

**免責事項**:
取得したデータは netkeiba.com の所有物です。
利用規約を遵守し、サーバーリソースを尊重してください。
