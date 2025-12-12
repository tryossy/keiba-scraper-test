# セットアップガイド

このドキュメントでは、パブリックリポジトリとして公開するための手順を説明します。

## ファイル構成

```
public-repo/  （この フォルダをGitHubリポジトリとして公開）
├── .github/
│   └── workflows/
│       └── scrape-monthly.yml    # GitHub Actions ワークフロー
├── scrape_monthly.py              # メインスクリプト
├── requirements.txt               # Python依存関係
├── .gitignore                     # 除外ファイル設定
├── README.md                      # 使い方・免責事項
├── NOTICE                         # Apache-2.0 帰属表示
├── LICENSE                        # MITライセンス
└── SETUP.md                       # このファイル
```

---

## GitHub リポジトリの作成

### 1. 新しいリポジトリを作成

1. GitHub にログイン
2. 右上の `+` → `New repository` をクリック
3. 以下を設定:
   - Repository name: `keiba-scraper-workflow`
   - Description: `Monthly horse racing data scraper using GitHub Actions`
   - **Public** を選択（重要: 無制限利用のため）
   - `Add a README file`: チェックしない（既に README.md があるため）
   - `Add .gitignore`: None
   - `Choose a license`: None（既に LICENSE があるため）
4. `Create repository` をクリック

---

### 2. ローカルファイルをプッシュ

```bash
# public-repo フォルダに移動
cd public-repo

# Git初期化
git init

# 全ファイルを追加
git add .

# 初回コミット
git commit -m "Initial commit: KeibaScraper wrapper with GitHub Actions"

# リモートリポジトリを追加（your-username を実際のユーザー名に変更）
git remote add origin https://github.com/your-username/keiba-scraper-workflow.git

# mainブランチに変更（GitHubのデフォルトブランチ名に合わせる）
git branch -M main

# プッシュ
git push -u origin main
```

---

## GitHub Secrets の設定（Google Drive使用時）

### 1. rclone の設定（ローカルPC）

```bash
# rclone のインストール（Windows）
# https://rclone.org/downloads/ からダウンロード

# または、PowerShell で
winget install Rclone.Rclone

# rclone 設定
rclone config

# 以下のように設定:
# n) New remote
# name> gdrive
# Storage> google drive（番号を選択）
# client_id> （空Enter）
# client_secret> （空Enter）
# scope> 1（Full access）
# root_folder_id> （空Enter）
# service_account_file> （空Enter）
# Edit advanced config? n
# Use auto config? y （ブラウザが開いてGoogle認証）
# Configure this as a team drive? n
# y) Yes this is OK
# q) Quit config
```

### 2. rclone 設定ファイルの内容を取得

```bash
# Windows
type %USERPROFILE%\.config\rclone\rclone.conf

# macOS/Linux
cat ~/.config/rclone/rclone.conf
```

出力例:
```
[gdrive]
type = drive
scope = drive
token = {"access_token":"...","token_type":"Bearer",...}
```

**この内容全体をコピー**

---

### 3. GitHub Secrets に登録

1. GitHubリポジトリページを開く
2. `Settings` → `Secrets and variables` → `Actions`
3. `New repository secret` をクリック
4. 以下を入力:
   - **Name**: `RCLONE_CONFIG`
   - **Secret**: 先ほどコピーした rclone.conf の内容を貼り付け
5. `Add secret` をクリック

---

## Fork 実行制限の設定（推奨）

第三者がリポジトリをForkして大量実行するのを防ぐため:

1. GitHubリポジトリページ → `Settings`
2. 左メニュー → `Actions` → `General`
3. `Fork pull request workflows from outside collaborators` セクション:
   - **`Require approval for first-time contributors`** を選択
4. `Save` をクリック

これにより、Forkからのワークフロー実行には承認が必要になります。

---

## ワークフローのテスト

### 手動実行でテスト

1. GitHubリポジトリページ → `Actions`
2. 左メニューから `Monthly Horse Racing Data Scrape` を選択
3. 右側の `Run workflow` をクリック
4. `year_month` に `2024-12` などを入力
5. `Run workflow` をクリック

**注意**: 初回実行は数時間かかる可能性があります。

---

## データの確認

### Google Drive で確認

1. Google Drive を開く
2. `keiba-data/` フォルダを確認
3. `2024-12/race_data_2024-12.csv` が保存されているはず

---

## トラブルシューティング

### エラー1: Workflow fails with "keibascraper not found"

**原因**: requirements.txt が正しく読み込まれていない

**解決策**:
1. requirements.txt が public-repo/ 直下にあることを確認
2. ワークフローの `pip install -r requirements.txt` 行を確認

---

### エラー2: Google Drive upload fails

**原因**: RCLONE_CONFIG が正しく設定されていない

**解決策**:
1. GitHub Secrets に `RCLONE_CONFIG` が存在するか確認
2. rclone.conf の内容が完全にコピーされているか確認
3. Google Drive の認証トークンが有効か確認（期限切れの場合は再設定）

---

### エラー3: "No races found"

**原因**: 指定した月にレースが開催されていない、またはレースIDの生成ロジックが実際の開催日と合っていない

**解決策**:
1. scrape_monthly.py の `get_race_ids_for_month()` 関数を確認
2. 実際のレース開催日を netkeiba.com で確認
3. 必要に応じてレースID生成ロジックを調整

---

## セキュリティチェックリスト

Public化する前に以下を確認:

- [ ] data/ フォルダが .gitignore に含まれている
- [ ] *.csv が .gitignore に含まれている
- [ ] config.json が .gitignore に含まれている
- [ ] 過去のコミット履歴に機密情報が含まれていない
- [ ] RCLONE_CONFIG が GitHub Secrets に設定されている（コードには含まれていない）
- [ ] README.md に免責事項が記載されている
- [ ] NOTICE に Apache-2.0 帰属表示がある
- [ ] Artifacts にデータをアップロードしていない

---

## メンテナンス

### 定期的な確認事項

1. **KeibaScraper のバージョン更新**
   ```bash
   pip install --upgrade keibascraper
   # requirements.txt を更新
   ```

2. **Google Drive 認証の更新**
   - 認証トークンは通常数ヶ月で期限切れ
   - エラーが出たら rclone config を再実行

3. **ワークフローの実行ログ確認**
   - GitHub Actions → 各実行ログを確認
   - エラーがあれば対応

---

## よくある質問

### Q1: Publicリポジトリにして大丈夫ですか？

A: 以下の条件を満たせば問題ありません:
- データを含めない（.gitignore で除外）
- 免責事項を明記
- レート制限を守る
- Google Drive への保存は Private

### Q2: GitHub Actions の無制限利用は本当ですか？

A: Publicリポジトリの場合、実行時間は無制限です（ただし1ジョブあたり6時間の制限あり）。

### Q3: 他の人がForkして実行したらどうなりますか？

A:
- Fork先では元のリポジトリの Secrets は使えません
- 各自が RCLONE_CONFIG を設定する必要があります
- Fork実行制限を設定することで、承認制にできます

### Q4: データはどこに保存されますか？

A:
- GitHub Artifacts には保存されません（誰でも見れるため）
- Google Drive（Private）に保存されます
- Secrets を設定しなければ、ワークフロー実行後に削除されます

---

## サポート

問題が発生した場合:

1. GitHub Issues で報告: https://github.com/your-username/keiba-scraper-workflow/issues
2. KeibaScraper の問題: https://github.com/new-village/KeibaScraper/issues
3. 利用規約に関する質問: netkeiba.com の運営者に問い合わせ
