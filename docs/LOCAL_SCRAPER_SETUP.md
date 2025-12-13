# ローカルスクレイパー使用ガイド

## 概要

`keibascraper` パッケージの代わりに、既存の `app/data_scraper_cli.py` を使用する方法です。

## 必要なファイル

public-repo に以下のファイルをコピーしてください:

```
public-repo/
├── app/
│   ├── __init__.py
│   ├── data_scraper.py
│   ├── data_scraper_cli.py
│   ├── keiba_tool_main.py
│   └── utils/
│       ├── __init__.py
│       ├── logger.py
│       └── error_handler.py
├── config.json.example
└── scrape_monthly_local.py  ← 新しいスクリプト
```

## セットアップ手順

### 1. ファイルをコピー

リポジトリのルートから:

```bash
# app ディレクトリ全体をコピー
cp -r app public-repo/

# config.json のテンプレートを作成
cp config.json public-repo/config.json.example
```

### 2. requirements.txt を更新

`public-repo/requirements.txt`:

```txt
# keibascraper>=3.1.3  ← 不要（コメントアウト）
pandas>=2.0.0
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
schedule>=1.2.0
urllib3>=2.0.0
```

### 3. config.json を作成

`public-repo/config.json.example` を `config.json` にコピー:

```bash
cd public-repo
cp config.json.example config.json
```

または、最小限の設定:

```json
{
  "request_settings": {
    "min_interval": 1.5,
    "max_requests_per_day": 40,
    "max_requests_weekday": 8000,
    "max_requests_weekend": 150
  }
}
```

## 使い方

### ローカルでの実行

```bash
cd public-repo

# 月次スクレイピング
python scrape_monthly_local.py --year-month 2024-12
```

内部的に `app/data_scraper_cli.py` が実行されます。

### GitHub Actions での使用

`.github/workflows/scrape-monthly-local.yml`:

```yaml
name: Monthly Scrape (Local Scraper)

on:
  schedule:
    - cron: '0 2 1 * *'
  workflow_dispatch:
    inputs:
      year_month:
        description: '年月 (例: 2024-12)'
        required: true

jobs:
  scrape:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Python 3.11 セットアップ
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: 依存関係インストール
        run: |
          pip install -r requirements.txt

      - name: config.json 作成
        run: |
          cp config.json.example config.json

      - name: スクレイピング実行
        run: |
          if [ "${{ github.event_name }}" = "workflow_dispatch" ]; then
            YEAR_MONTH="${{ github.event.inputs.year_month }}"
          else
            YEAR_MONTH=$(date -d 'last month' +%Y-%m)
          fi

          python scrape_monthly_local.py --year-month $YEAR_MONTH

      - name: データを Google Drive にアップロード
        if: env.RCLONE_CONFIG != ''
        run: |
          curl https://rclone.org/install.sh | sudo bash
          mkdir -p ~/.config/rclone
          echo "${{ secrets.RCLONE_CONFIG }}" > ~/.config/rclone/rclone.conf

          # data/html/ 配下をアップロード
          rclone copy data/html/ gdrive:keiba-data/html/
        env:
          RCLONE_CONFIG: ${{ secrets.RCLONE_CONFIG }}
```

## 注意事項

### .gitignore に追加

```gitignore
# データファイル
data/
*.csv
*.json  # config.json を除外

# ログ
logs/
```

### config.json は GitHub Secrets で管理（推奨）

Public リポジトリでは `config.json` をコミットしないでください。

代わりに、環境変数で設定:

```yaml
- name: config.json 作成
  run: |
    cat > config.json << EOF
    {
      "request_settings": {
        "min_interval": 1.5,
        "max_requests_per_day": ${{ secrets.MAX_REQUESTS_PER_DAY }},
        "max_requests_weekday": 8000,
        "max_requests_weekend": 150
      }
    }
    EOF
```

## ローカルスクレイパーの利点

1. **依存関係の削減**: `keibascraper` パッケージ不要
2. **カスタマイズ可能**: 既存のコードを自由に変更可能
3. **デバッグ容易**: エラー時にローカルコードを確認可能
4. **レート制限の完全制御**: config.json で細かく設定可能

## トラブルシューティング

### エラー: app/data_scraper_cli.py が見つからない

**原因**: app ディレクトリがコピーされていない

**解決策**:
```bash
cp -r ../app .
```

### エラー: config.json が見つからない

**原因**: config.json が作成されていない

**解決策**:
```bash
cp config.json.example config.json
```

### エラー: ModuleNotFoundError: No module named 'app'

**原因**: Python のパス問題

**解決策**:
```python
# scrape_monthly_local.py の先頭に追加
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
```

## まとめ

- **keibascraper 不要**: 既存のローカルスクレイパーを使用
- **シンプル**: `scrape_monthly_local.py` が内部的に `app/data_scraper_cli.py` を呼び出す
- **GitHub Actions 対応**: ワークフローファイルも調整済み

詳細は README.md を参照してください。
