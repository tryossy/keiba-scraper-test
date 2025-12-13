# パブリックリポジトリ最終構成

## 完成したファイル構成

```
public-repo/
├── .github/
│   └── workflows/
│       ├── scrape-monthly-local.yml      # 月次スクレイピング（1ヶ月を順次処理）
│       └── scrape-yearly-parallel.yml    # 年次並列スクレイピング（12ヶ月を最大6並列）
│
├── app/                                  # スクレイパー関連のみ
│   ├── data_scraper.py                   # スクレイピングコア
│   ├── data_scraper_cli.py               # CLIインターフェース
│   ├── html_parser.py                    # HTMLパーサー
│   └── utils/                            # ユーティリティ
│       ├── __init__.py
│       ├── error_handler.py
│       └── logger.py
│
├── docs/                                 # ドキュメント（全て移動済み）
│   ├── LOCAL_SCRAPER_SETUP.md            # ローカルスクレイパー詳細
│   ├── PARALLEL_WORKFLOW.md              # 並列ワークフロー説明（参考）
│   ├── PUBLIC_REPO_GUIDE.md              # 総合ガイド
│   ├── PUBLISH_CHECKLIST.md              # 公開前チェックリスト
│   ├── SETUP.md                          # セットアップガイド
│   ├── TROUBLESHOOTING.md                # トラブルシューティング
│   ├── YEARLY_WORKFLOW.md                # 年次並列ワークフロー詳細
│   └── FINAL_STRUCTURE.md                # このファイル
│
├── .gitignore                            # Git除外設定
├── README.md                             # メインREADME（ライセンス記述削除済み）
├── requirements.txt                      # Python依存関係
└── scrape_monthly_local.py               # ラッパースクリプト
```

---

## 削除されたファイル

### app/ から削除
- `auto_update.py` - 自動更新ロジック（不要）
- `feature_engineering.py` - 特徴量エンジニアリング（ML用）
- `feature_extractor.py` - 特徴量抽出（ML用）
- `horse_characteristics.py` - 馬特性（ML用）
- `keiba_tool_main.py` - メインツール（ライブ予測用）
- `ml_pipeline.py` - MLパイプライン（ML用）
- `prediction_engine.py` - 予測エンジン（ML用）
- `predictor.py` - 予測器v1（ML用）
- `predictor_multitarget.py` - マルチターゲット予測器（ML用）
- `predictor_v2.py` - 予測器v2（ML用）
- `shutuba_scraper.py` - 出馬表スクレイパー（ライブ予測用）

### ルートから削除
- `LICENSE` - MITライセンス（不要）
- `NOTICE` - ライセンス帰属（不要）

### ドキュメントの整理
- README.md からライセンス記述を削除
- 全てのドキュメントを `docs/` に移動

---

## 残したファイルの理由

### スクレイパーコア（app/）
- **data_scraper.py**: スクレイピングの中核ロジック
- **data_scraper_cli.py**: コマンドライン実行用
- **html_parser.py**: ページパース処理（スクレイピングに必要）
- **utils/**: エラーハンドリングとロギング（スクレイパーで使用）

### ワークフロー（.github/workflows/）
- **scrape-monthly-local.yml**: 月次自動実行用
- **scrape-yearly-parallel.yml**: 年次並列実行用（最大6並列）

### その他
- **scrape_monthly_local.py**: ワークフローから呼び出すラッパー
- **requirements.txt**: スクレイパー用の依存関係のみ
- **README.md**: リポジトリ説明（ライセンス記述削除）
- **.gitignore**: データファイルやログを除外

---

## 主な変更点

### 1. app/ ディレクトリの簡素化
**変更前**: 17ファイル（ML、予測、スクレイパー混在）
**変更後**: 4ファイル（スクレイパーのみ）

### 2. ライセンスの削除
**変更前**:
- LICENSE（MIT License）
- NOTICE（Apache-2.0帰属含む）
- README に両方のライセンス記載

**変更後**:
- LICENSE削除
- NOTICE削除
- README は免責事項のみ（netkeiba.com利用規約遵守）

### 3. ドキュメント構造の整理
**変更前**: ルートに7つのMarkdownファイル散在
**変更後**: docs/ に集約（README.md のみルート）

---

## 公開前に追加が必要なファイル

### config.json.example

```bash
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

---

## 使用方法

### 1. GitHub リポジトリ作成

```bash
cd public-repo/
git init
git remote add origin https://github.com/YOUR_USERNAME/keiba-scraper.git
git add .
git commit -m "Initial commit: Minimal horse racing scraper"
git branch -M main
git push -u origin main
```

### 2. GitHub Secrets 設定

Settings → Secrets and variables → Actions → New repository secret

| Secret名 | 値 |
|---------|---|
| `RCLONE_CONFIG` | `cat ~/.config/rclone/rclone.conf` の出力 |

### 3. ワークフロー実行

#### 月次スクレイピング
- Actions → "Monthly Horse Racing Data Scrape (Local Scraper)"
- Run workflow → year_month: `2024-12`

#### 年次並列スクレイピング
- Actions → "Yearly Horse Racing Data Scrape (12 Months Parallel)"
- Run workflow → year: `2024`, start_month: `1`, end_month: `12`

---

## 依存関係

```txt
pandas>=2.0.0
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
schedule>=1.2.0
urllib3>=2.0.0
```

**外部ライブラリ不使用**: keibascraper を削除、完全にローカルスクレイパーのみ使用

---

## 技術仕様

### スクレイピング設定
- **レート制限**: 1.5秒間隔（固定）
- **平日**: 8000リクエスト/日
- **週末**: 150リクエスト/日

### 並列実行
- **最大並列数**: 6ジョブ
- **年次ワークフロー**: 12ヶ月を2グループに分割（各6並列）
- **所要時間**: 約2時間（順次実行の1/6）

### データ保存
- **フォーマット**: `.bin`（バイナリHTML）
- **保存先**: Google Drive (`gdrive:keiba-data/html/race/`)
- **ローカル**: `data/html/race/YYYYMM*.bin`

---

## まとめ

### 最小構成の達成
- スクレイパー機能のみに集約
- ML/予測関連のファイルは全て削除
- ライセンス記述を削除
- ドキュメントを `docs/` に整理

### 公開準備完了
- `config.json.example` を追加
- GitHub Secrets に `RCLONE_CONFIG` を設定
- ワークフローを手動実行してテスト

詳細は [docs/PUBLISH_CHECKLIST.md](PUBLISH_CHECKLIST.md) を参照してください。
