# 競馬データ月次スクレイピングツール

GitHub Actions を使用して、毎月自動的に競馬データを取得するワークフローツールです。

## 概要

このツールは [KeibaScraper](https://github.com/new-village/KeibaScraper) をラッパーとして使用し、netkeiba.com から競馬レースデータを取得します。

**主な特徴:**
- GitHub Actions による自動実行（無制限利用可能）
- レート制限対応（サーバー負荷軽減）
- Google Drive への自動バックアップ（オプション）
- 月次スケジュール実行

---

## 免責事項

**重要: このツールを使用する前に必ずお読みください**

### 利用上の注意

1. **個人利用・学習目的のみ**
   - 本ツールは個人的な学習・研究目的で作成されました
   - 商用利用は禁止されている可能性があります

2. **利用規約の遵守**
   - netkeiba.com の利用規約を必ず確認し、遵守してください
   - robots.txt の内容を確認してください

3. **サーバー負荷への配慮**
   - デフォルトのレート制限（1.5秒間隔）を変更しないでください
   - 過度なアクセスはサーバーに負荷をかけ、サービス妨害につながります

4. **データの取扱い**
   - 取得したデータの再配布は禁止されている可能性があります
   - データの著作権・データベース権は元のサイトに帰属します
   - このリポジトリではデータを公開していません（ツールのみ）

5. **法的責任**
   - 本ツールの使用によって生じたいかなる損害についても、作者は責任を負いません
   - 利用規約違反やサーバー負荷による問題の責任は利用者にあります

6. **アカウント停止のリスク**
   - 不適切な使用により、netkeiba.com からアクセス制限を受ける可能性があります

### 推奨事項

- 個人利用に限定
- レート制限の厳守
- 取得したデータの非公開
- 不明な点はサイト運営者に問い合わせ

---

## 使用ライブラリ

このツールは以下のオープンソースライブラリを使用しています:

- **[KeibaScraper](https://github.com/new-village/KeibaScraper)** by new-village
  - ライセンス: Apache-2.0
  - 用途: netkeiba.com からのデータ取得

詳細は [NOTICE](NOTICE) を参照してください。

---

## セットアップ

### 前提条件

- Python 3.8以上
- GitHub アカウント（GitHub Actions使用時）

### インストール

```bash
# リポジトリのクローン
git clone https://github.com/yourusername/keiba-scraper-workflow.git
cd keiba-scraper-workflow

# 依存関係のインストール
pip install -r requirements.txt
```

---

## 使い方

### ローカルでの実行

```bash
# 指定月のデータを取得
python scrape_monthly.py --year-month 2024-12

# 出力ファイル名を指定
python scrape_monthly.py --year-month 2024-12 --output dec_2024.csv

# レート制限を変更（非推奨）
python scrape_monthly.py --year-month 2024-12 --interval 2.0
```

**出力:**
- `race_data.csv` (デフォルト)
- レースID、日付、競馬場、レース結果などを含むCSVファイル

---

### GitHub Actions での自動実行

#### 1. GitHub Secrets の設定（Google Drive使用時）

Settings → Secrets and variables → Actions → New repository secret

```
Name: RCLONE_CONFIG
Value: [rclone config file の内容]
```

rclone config の取得方法:
```bash
# ローカルで rclone を設定
rclone config

# 設定ファイルの内容を取得
cat ~/.config/rclone/rclone.conf
```

#### 2. ワークフローの有効化

`.github/workflows/scrape-monthly.yml` が自動的に毎月1日に実行されます。

#### 3. 手動実行

GitHub リポジトリページ → Actions → "Monthly Scrape" → Run workflow

---

## ファイル構成

```
keiba-scraper-workflow/
├── .github/
│   └── workflows/
│       └── scrape-monthly.yml    # GitHub Actions ワークフロー
├── scrape_monthly.py              # メインスクリプト
├── requirements.txt               # Python依存関係
├── .gitignore                     # 除外ファイル設定
├── README.md                      # このファイル
├── NOTICE                         # ライセンス帰属表示
└── LICENSE                        # MITライセンス
```

---

## GitHub Actions の設定

### ワークフロー内容

- **スケジュール**: 毎月1日 午前2時（UTC）
- **手動実行**: 可能
- **タイムアウト**: 6時間（GitHub制限）
- **成果物**: Google Drive に保存（Artifacts は使用しない）

### データの保存先

**重要: GitHub Artifacts は使用しません**

理由:
- Publicリポジトリの Artifacts は**誰でもダウンロード可能**
- データ公開 = 著作権・利用規約違反のリスク

推奨:
- Google Drive（Private）に保存
- rclone を使用して自動アップロード

---

## トラブルシューティング

### エラー1: keibascraper がインストールできない

```bash
pip install --upgrade pip
pip install keibascraper
```

### エラー2: レースIDが見つからない

- 指定した日付にレースが開催されていない可能性があります
- 競馬場コードやレース番号が存在しない可能性があります

### エラー3: GitHub Actions でタイムアウト

- 1ヶ月分のデータ取得に6時間以上かかる場合、週単位に分割してください

---

## ライセンス

### このツール（ワークフローコード）

MIT License

Copyright (c) 2024

### 使用ライブラリ

- **KeibaScraper**: Apache-2.0 License
  - 詳細: [NOTICE](NOTICE)

### 取得したデータ

- データの著作権・データベース権は netkeiba.com に帰属します
- 本ライセンスはデータには適用されません

---

## 貢献

プルリクエストは歓迎しますが、以下の点にご注意ください:

1. レート制限を緩和する変更は受け付けません
2. データを含むコミットは受け付けません
3. 利用規約に違反する機能は受け付けません

---

## 関連リンク

- [KeibaScraper](https://github.com/new-village/KeibaScraper) - 使用しているライブラリ
- [netkeiba.com](https://netkeiba.com/) - データソース
- [rclone](https://rclone.org/) - Google Drive 連携ツール

---

## お問い合わせ

- GitHub Issues: [Issues](https://github.com/yourusername/keiba-scraper-workflow/issues)
- 利用規約に関する質問: netkeiba.com の運営者にお問い合わせください

---

## 変更履歴

### v1.0.0 (2024-12-13)
- 初回リリース
- KeibaScraper ラッパー実装
- GitHub Actions ワークフロー追加
- Google Drive 連携対応
