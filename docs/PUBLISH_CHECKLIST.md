# GitHub公開チェックリスト

## 公開前に必ず確認

### 1. 必須ファイルの確認

- [x] `.github/workflows/scrape-monthly-local.yml` - 月次ワークフロー
- [x] `.github/workflows/scrape-yearly-parallel.yml` - 年次並列ワークフロー
- [x] `scrape_monthly_local.py` - ラッパースクリプト
- [x] `requirements.txt` - 依存関係（keibascraper除外済み）
- [x] `README.md` - リポジトリ説明
- [x] `LICENSE` - MITライセンス
- [x] `NOTICE` - 免責事項
- [ ] **`app/` ディレクトリ** - **未コピー（手動で追加必要）**
- [ ] **`config.json.example`** - **未作成（手動で追加必要）**

---

### 2. 手動で追加するファイル

#### app/ ディレクトリのコピー

```bash
# プロジェクトルートから実行
cp -r app/ public-repo/app/

# 確認
ls public-repo/app/
# 出力例:
# data_scraper.py
# data_scraper_cli.py
# utils/
# ...
```

**重要**: 以下のファイルは**除外**してください：
- `app/config.json`（シークレット情報が含まれる可能性）
- `app/__pycache__/`
- `app/*.pyc`

#### config.json.example の作成

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

### 3. シークレット情報の確認

以下のファイルに**シークレット情報が含まれていないか**確認：

```bash
# 確認コマンド
grep -r "password" public-repo/
grep -r "api_key" public-repo/
grep -r "secret" public-repo/
grep -r "token" public-repo/
```

**除外すべき情報**:
- パスワード
- APIキー
- トークン
- メールアドレス
- プライベートな設定

---

### 4. GitHub Secrets の準備

パブリックリポジトリで設定が必要なシークレット：

| シークレット名 | 説明 | 取得方法 |
|-------------|------|---------|
| `RCLONE_CONFIG` | Google Drive接続設定 | `cat ~/.config/rclone/rclone.conf` |

#### RCLONE_CONFIG の取得方法

```bash
# ローカルで rclone を設定（未設定の場合）
rclone config

# 設定ファイルの内容を表示
cat ~/.config/rclone/rclone.conf

# 出力例:
# [gdrive]
# type = drive
# scope = drive
# token = {"access_token":"...","refresh_token":"..."}
```

上記の**全内容**をコピーして、GitHub Secretsに貼り付けます。

---

### 5. .gitignore の確認

以下が除外されていることを確認：

```bash
cat public-repo/.gitignore
```

**必須の除外項目**:
```
# データファイル
data/
*.csv
*.bin

# 設定ファイル
config.json
*.log

# Python
__pycache__/
*.pyc
*.pyo
venv/

# OS
.DS_Store
Thumbs.db
```

---

### 6. 依存関係の確認

```bash
cat public-repo/requirements.txt
```

**確認ポイント**:
- `keibascraper` が**含まれていない**こと（コメントアウトされているはOK）
- 必要な依存関係が全て含まれていること

**現在の依存関係**:
```txt
pandas>=2.0.0
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
schedule>=1.2.0
urllib3>=2.0.0
```

---

### 7. ライセンスの確認

```bash
# MIT License のみ使用
cat public-repo/LICENSE | head -5

# Apache-2.0 帰属が削除されていることを確認
cat public-repo/NOTICE
```

**NOTICE の内容**:
- MIT License 表記
- netkeiba.com 利用規約の免責事項のみ
- **Apache-2.0 への言及なし**

---

### 8. ワークフローの動作確認

#### 月次ワークフロー

```bash
# ファイル存在確認
cat public-repo/.github/workflows/scrape-monthly-local.yml | grep "scrape_monthly_local.py"

# 期待される出力:
# python scrape_monthly_local.py --year-month ${{ inputs.year_month }}
```

#### 年次並列ワークフロー

```bash
# ファイル存在確認
cat public-repo/.github/workflows/scrape-yearly-parallel.yml | grep "max-parallel"

# 期待される出力:
# max-parallel: 6

# combine ジョブが削除されていることを確認
cat public-repo/.github/workflows/scrape-yearly-parallel.yml | grep -c "combine"

# 期待される出力: 0
```

---

## 公開手順

### 1. GitHubでパブリックリポジトリを作成

1. GitHub → **New repository**
2. Repository name: `keiba-auto-scraper`（任意）
3. Description: `競馬データ自動スクレイピングツール（GitHub Actions + Google Drive）`
4. **Public** を選択
5. **Add a README file**: チェックを**外す**（既存のREADMEを使用）
6. **Add .gitignore**: None（既存の.gitignoreを使用）
7. **Choose a license**: None（既存のLICENSEを使用）
8. **Create repository**

---

### 2. ローカルでGit初期化（public-repo/ディレクトリ）

```bash
cd public-repo/

# Git初期化
git init

# リモートリポジトリを追加（URLは自分のリポジトリに変更）
git remote add origin https://github.com/YOUR_USERNAME/keiba-auto-scraper.git

# ファイルをステージング
git add .

# 初回コミット
git commit -m "Initial commit: Local scraper with GitHub Actions workflows"

# プッシュ
git branch -M main
git push -u origin main
```

---

### 3. GitHub Secrets の設定

1. リポジトリページ → **Settings**
2. 左メニュー → **Secrets and variables** → **Actions**
3. **New repository secret** をクリック
4. シークレット名: `RCLONE_CONFIG`
5. Value: rclone.conf の内容を貼り付け
6. **Add secret**

---

### 4. ワークフローの手動実行テスト

#### 月次ワークフローのテスト

1. リポジトリページ → **Actions**
2. 左メニュー → **Monthly Horse Racing Data Scrape (Local Scraper)**
3. **Run workflow** をクリック
4. 入力:
   - `year_month`: `2024-12`（テスト用に過去月を指定）
5. **Run workflow**
6. ジョブの実行ログを確認

**成功の条件**:
- `app/data_scraper_cli.py` が正常に実行される
- Google Drive にデータがアップロードされる
- ログが GitHub Artifacts にアップロードされる

#### 年次並列ワークフローのテスト

1. リポジトリページ → **Actions**
2. 左メニュー → **Yearly Horse Racing Data Scrape (12 Months Parallel)**
3. **Run workflow** をクリック
4. 入力:
   - `year`: `2024`
   - `start_month`: `1`（テスト用に短期間を指定推奨: 1-2など）
   - `end_month`: `2`
5. **Run workflow**
6. 複数のジョブが並列実行されることを確認

**成功の条件**:
- 12ジョブ（または指定月数）が生成される
- 最大6ジョブが同時実行される
- 各月のデータが個別に Google Drive にアップロードされる

---

## トラブルシューティング

### エラー1: `app/data_scraper_cli.py が見つかりません`

**原因**: app/ ディレクトリが含まれていない

**解決策**:
```bash
# public-repo/ディレクトリで実行
git add app/
git commit -m "Add app directory"
git push
```

---

### エラー2: `ModuleNotFoundError: No module named 'xxx'`

**原因**: requirements.txt の依存関係が不足

**解決策**:
```bash
# 不足しているモジュールを追加
echo "missing-module>=1.0.0" >> public-repo/requirements.txt
git add requirements.txt
git commit -m "Add missing dependency"
git push
```

---

### エラー3: `RCLONE_CONFIG が設定されていません`

**原因**: GitHub Secrets が未設定

**解決策**:
1. Settings → Secrets and variables → Actions
2. "New repository secret" をクリック
3. Name: `RCLONE_CONFIG`
4. Value: `cat ~/.config/rclone/rclone.conf` の出力を貼り付け

---

### エラー4: Google Drive へのアップロードが失敗

**原因**: rclone の認証トークンが期限切れ

**解決策**:
```bash
# ローカルで rclone を再認証
rclone config reconnect gdrive

# 新しい設定を取得
cat ~/.config/rclone/rclone.conf

# GitHub Secrets を更新
```

---

## 公開後の定期メンテナンス

### 毎月の確認事項

1. **ワークフローの実行ログ確認**
   - Actions タブ → 最新の実行履歴
   - エラーがないか確認

2. **Google Drive の容量確認**
   - データが正常にアップロードされているか
   - 容量が逼迫していないか

3. **依存関係の更新**
   - `pip list --outdated` で古いパッケージを確認
   - セキュリティパッチがあれば更新

### 四半期ごとの確認事項

1. **rclone トークンの更新**
   - Google Drive の認証トークンは90日で期限切れの可能性
   - 必要に応じて再認証

2. **ワークフローの最適化**
   - 実行時間が長い場合は並列数を調整
   - レート制限の見直し

---

## まとめ

### 公開前のチェックリスト

- [ ] app/ ディレクトリをコピー
- [ ] config.json.example を作成
- [ ] シークレット情報の確認（パスワード、APIキー等）
- [ ] .gitignore の確認
- [ ] requirements.txt の確認（keibascraper除外）
- [ ] LICENSE の確認（MIT のみ）
- [ ] NOTICE の確認（Apache-2.0 帰属削除）
- [ ] ワークフローファイルの確認（combine ジョブ削除）

### 公開後のチェックリスト

- [ ] GitHub Secrets の設定（RCLONE_CONFIG）
- [ ] 月次ワークフローのテスト実行
- [ ] 年次並列ワークフローのテスト実行
- [ ] Google Drive へのアップロード確認
- [ ] README の更新（リポジトリURLなど）

---

## 完了！

全てのチェック項目が完了したら、パブリックリポジトリとして公開完了です。

**次のステップ**:
- [PUBLIC_REPO_GUIDE.md](PUBLIC_REPO_GUIDE.md) を参照して使い方を確認
- [YEARLY_WORKFLOW.md](YEARLY_WORKFLOW.md) で年次並列ワークフローの詳細を確認
