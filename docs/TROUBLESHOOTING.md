# トラブルシューティング

## GitHub Actions でのエラー解決

### エラー1: `RCLONE_CONFIG: file name too long`

**エラーメッセージ:**
```
Failed to load config file "...(long token)...": open ...: file name too long
```

**原因:**
- `echo "${{ secrets.RCLONE_CONFIG }}" > ~/.config/rclone/rclone.conf` で設定内容がファイルパスとして解釈される
- シークレットの内容が長すぎてパス名制限を超える

**解決方法:**

ワークフローファイルの `rclone 設定` ステップを以下のように修正:

```yaml
- name: rclone 設定
  if: env.RCLONE_CONFIG != ''
  run: |
    mkdir -p ~/.config/rclone
    cat > ~/.config/rclone/rclone.conf << 'EOF'
    ${{ secrets.RCLONE_CONFIG }}
    EOF
  env:
    RCLONE_CONFIG: ${{ secrets.RCLONE_CONFIG }}
```

**ポイント:**
- `echo` の代わりに `cat` とヒアドキュメント (`<< 'EOF'`) を使用
- シングルクォート `'EOF'` で変数展開を防ぐ
- `${{ secrets.RCLONE_CONFIG }}` はGitHub Actionsが展開

---

### エラー2: `keibascraper がインストールされていません`

**エラーメッセージ:**
```
エラー: keibascraper がインストールされていません。
インストール: pip install keibascraper
```

**原因:**
- `requirements.txt` が読み込まれていない
- pip のキャッシュ問題
- Python バージョンの不一致

---

**解決方法1: requirements.txt を確認**

`requirements.txt` に以下が含まれていることを確認:

```txt
keibascraper>=2.1.1
pandas>=2.0.0
requests>=2.31.0
```

---

**解決方法2: 明示的なインストールを追加**

ワークフローファイル（`.github/workflows/scrape-monthly.yml`）を以下のように修正:

```yaml
- name: 依存関係のインストール
  run: |
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    # 念のため明示的にインストール
    pip install keibascraper>=2.1.1
```

---

**解決方法3: キャッシュをクリア**

ワークフローの `cache: 'pip'` を一時的に無効化:

```yaml
- name: Python 3.11 のセットアップ
  uses: actions/setup-python@v4
  with:
    python-version: '3.11'
    # cache: 'pip'  # 一時的にコメントアウト
```

その後、ワークフローを再実行。

---

**解決方法4: インストール確認ステップを追加**

```yaml
- name: 依存関係のインストール
  run: |
    python -m pip install --upgrade pip
    pip install -r requirements.txt

- name: インストール確認
  run: |
    python -c "import keibascraper; print(f'keibascraper version: {keibascraper.__version__}')"
    pip list | grep keibascraper
```

これでインストールが成功したか確認できます。

---

### エラー2: `ModuleNotFoundError: No module named 'keibascraper'`

**原因:**
Python のパス問題または仮想環境の問題

**解決方法:**

```yaml
- name: 依存関係のインストール（詳細ログ付き）
  run: |
    python -m pip install --upgrade pip
    pip install -v keibascraper>=2.1.1
    pip install -r requirements.txt

- name: Python パス確認
  run: |
    which python
    python --version
    pip --version
```

---

### エラー3: `keibascraper` のバージョン互換性エラー

**エラーメッセージ:**
```
ERROR: Could not find a version that satisfies the requirement keibascraper>=2.1.1
```

**原因:**
指定したバージョンが存在しない

**解決方法:**

最新版を確認してインストール:

```yaml
- name: 依存関係のインストール
  run: |
    python -m pip install --upgrade pip
    # 最新版をインストール
    pip install keibascraper
    pip install -r requirements.txt
```

または、`requirements.txt` を修正:

```txt
keibascraper  # バージョン指定なし（最新版）
pandas>=2.0.0
requests>=2.31.0
```

---

## ローカルでのエラー解決

### エラー1: ローカルで `keibascraper` がインストールできない

**Windows の場合:**

```powershell
# PowerShell で実行
python -m pip install --upgrade pip
pip install keibascraper
```

**エラーが出る場合:**

```powershell
# 仮想環境を作成
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install keibascraper
```

---

**macOS/Linux の場合:**

```bash
python3 -m pip install --upgrade pip
pip3 install keibascraper
```

**エラーが出る場合:**

```bash
# 仮想環境を作成
python3 -m venv venv
source venv/bin/activate
pip install keibascraper
```

---

### エラー2: `pip install` が遅い

**原因:**
PyPI のミラーサーバーが遅い

**解決方法:**

```bash
# 国内ミラーを使用（日本）
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple keibascraper

# または Aliyun ミラー
pip install -i https://mirrors.aliyun.com/pypi/simple/ keibascraper
```

---

## GitHub Actions 特有の問題

### エラー1: ワークフローが途中で止まる

**症状:**
依存関係のインストール中にワークフローが応答なし

**解決方法:**

タイムアウトを設定:

```yaml
- name: 依存関係のインストール
  run: |
    python -m pip install --upgrade pip
    pip install --timeout 300 keibascraper
    pip install --timeout 300 -r requirements.txt
```

---

### エラー2: `setup-python@v4` が古い

**解決方法:**

最新版を使用:

```yaml
- name: Python 3.11 のセットアップ
  uses: actions/setup-python@v5  # v4 → v5
  with:
    python-version: '3.11'
    cache: 'pip'
```

---

## 完全に動作する修正版ワークフロー

以下は、`keibascraper` のインストール問題を完全に解決したワークフロー例:

```yaml
name: Monthly Scrape (Fixed)

on:
  workflow_dispatch:

jobs:
  scrape:
    runs-on: ubuntu-latest

    steps:
      - name: リポジトリをチェックアウト
        uses: actions/checkout@v4

      - name: Python 3.11 のセットアップ
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: pip のアップグレード
        run: |
          python -m pip install --upgrade pip setuptools wheel

      - name: keibascraper のインストール（明示的）
        run: |
          pip install keibascraper>=2.1.1

      - name: その他の依存関係のインストール
        run: |
          pip install pandas>=2.0.0 requests>=2.31.0

      - name: インストール確認
        run: |
          pip list
          python -c "import keibascraper; print('keibascraper OK')"
          python -c "import pandas; print('pandas OK')"

      - name: スクレイピング実行
        run: |
          python scrape_monthly.py --year-month 2024-12
```

---

## デバッグ用ワークフロー

問題を診断するためのワークフロー:

```yaml
name: Debug Installation

on:
  workflow_dispatch:

jobs:
  debug:
    runs-on: ubuntu-latest

    steps:
      - name: リポジトリをチェックアウト
        uses: actions/checkout@v4

      - name: Python 3.11 のセットアップ
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: 環境情報の表示
        run: |
          echo "=== Python 情報 ==="
          which python
          python --version

          echo "=== pip 情報 ==="
          which pip
          pip --version

          echo "=== 環境変数 ==="
          env | grep PYTHON

      - name: requirements.txt の内容確認
        run: |
          echo "=== requirements.txt ==="
          cat requirements.txt

      - name: pip install の詳細ログ
        run: |
          pip install -v keibascraper 2>&1 | tee install_log.txt

      - name: インストール結果確認
        run: |
          pip list | grep -i keiba
          python -c "import sys; print(sys.path)"
          python -c "import keibascraper; print(keibascraper.__file__)"

      - name: ログのアップロード
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: debug-logs
          path: install_log.txt
```

---

## よくある質問

### Q1: ローカルでは動くのに GitHub Actions で失敗する

**A:** Python のバージョンが異なる可能性があります。

```yaml
# ローカルと同じバージョンを指定
- name: Python 3.11 のセットアップ
  uses: actions/setup-python@v5
  with:
    python-version: '3.11.5'  # 具体的なバージョンを指定
```

---

### Q2: `keibascraper` は正式なパッケージですか？

**A:** はい、PyPI に公開されている正式なパッケージです。

確認方法:
```bash
pip search keibascraper
# または
pip show keibascraper
```

---

### Q3: 代替のインストール方法はありますか？

**A:** GitHub から直接インストールする方法もあります（非推奨）:

```bash
pip install git+https://github.com/new-village/KeibaScraper.git
```

ただし、通常は PyPI からのインストールを推奨します。

---

## サポート

それでも解決しない場合:

1. **GitHub Issues で報告**: リポジトリの Issues タブ
2. **KeibaScraper の Issues**: https://github.com/new-village/KeibaScraper/issues
3. **ワークフローのログを確認**: Actions タブ → 失敗したワークフロー → ログ全体をダウンロード
