# aaover60.com向け newsbot テスト実行ガイド

このガイドでは、newsbotを初めて実行する前の準備と、テスト実行の手順を説明します。

## 🔧 事前準備（ユーザー作業が必要）

### 1. WordPressの準備

#### ✅ WordPress側で確認・設定する項目

1. **newsbotユーザーの確認**
   - aaover60.comのWordPress管理画面にログイン
   - `ユーザー` → `ユーザー一覧` で「newsbot」ユーザーが存在するか確認
   - 存在しない場合は新規作成（権限: 投稿者 または 編集者）

2. **アプリケーションパスワードの確認**
   - 現在の.envに設定されているパスワード: `QjgR KWKW 1nBb aL5y DjrR 36SA`
   - このパスワードが有効か確認するには：
     - WordPress管理画面 → `ユーザー` → `newsbot` → `編集`
     - 下部の「アプリケーションパスワード」セクションを確認
   - 無効な場合は新しいパスワードを生成し、`.env`を更新

3. **REST APIの確認**
   - ブラウザで以下のURLにアクセス:
     ```
     https://aaover60.com/wp-json/wp/v2/posts
     ```
   - JSONデータが表示されればOK（エラーが出なければ問題なし）

### 2. RSSフィードの選択

#### ✅ .envファイルのRSS_FEEDSを設定

`workspace/projects/newsbot/.env`ファイルの18行目を編集します。

現在は:
```env
RSS_FEEDS=https://example.com/feed1.xml,https://example.com/feed2.xml
```

以下のいずれかに変更してください：

**推奨：バランス型（初回テストに最適）**
```env
RSS_FEEDS=https://www.nhk.or.jp/rss/news/cat0.xml,https://www.nhk.or.jp/rss/news/cat6.xml,https://rss.itmedia.co.jp/rss/2.0/news_bursts.xml
```

詳しくは `RSS_FEED_GUIDE.md` を参照してください。

### 3. その他の設定確認

#### ✅ .envファイルの確認項目

| 項目 | 現在の設定 | 確認内容 |
|------|-----------|---------|
| `LLM_PROVIDER` | openai | OK（OpenAIを使用） |
| `OPENAI_API_KEY` | 設定済み | 有効なAPIキーか確認 |
| `OPENAI_MODEL` | gpt-5-mini | ⚠️ 正しいモデル名か確認（推奨: `gpt-4o-mini`） |
| `WORDPRESS_URL` | https://aaover60.com | OK |
| `WORDPRESS_USERNAME` | newsbot | OK |
| `WORDPRESS_APP_PASSWORD` | 設定済み | WordPressで有効か確認 |

**重要**: `OPENAI_MODEL`が`gpt-5-mini`になっていますが、これは存在しないモデル名です。
以下のいずれかに変更してください：
- `gpt-4o-mini` （推奨：コスト効率が良い）
- `gpt-4o` （高品質）
- `gpt-4-turbo` （旧モデル）

## 🚀 テスト実行手順

### ステップ1: Python環境の確認

```bash
cd C:\Users\wandt\AI_coding\workspace\projects\newsbot
python --version
```

Python 3.11以上が必要です。

### ステップ2: 仮想環境の作成（推奨）

```powershell
# PowerShellの場合
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# コマンドプロンプトの場合
python -m venv .venv
.venv\Scripts\activate.bat
```

### ステップ3: 依存関係のインストール

```bash
pip install -r requirements.txt
```

### ステップ4: 初回テスト実行

```bash
python main.py
```

### ステップ5: 結果の確認

#### ✅ 成功時の確認項目

1. **ログファイル**
   ```bash
   notepad newsbot.log
   ```
   - エラーがないか確認
   - "newsbot completed successfully" が表示されていればOK

2. **生成記事**
   ```bash
   notepad out\draft.md
   ```
   - Markdown形式の記事が生成されているか確認
   - 記事の内容が適切か確認

3. **WordPress下書き**
   - https://aaover60.com/wp-admin/ にログイン
   - `投稿` → `投稿一覧` を開く
   - 新しい下書きが作成されているか確認
   - タイトルと内容が適切か確認

#### ❌ エラーが出た場合

1. **エラーメッセージを確認**
   - `newsbot.log`ファイルを開く
   - `out/draft.md`を開く（エラー情報が保存されています）

2. **よくあるエラーと対処法**

| エラー内容 | 原因 | 対処法 |
|-----------|------|--------|
| `OPENAI_API_KEY not set` | APIキーが無効 | .envのAPIキーを確認 |
| `WordPress 認証エラー` | アプリケーションパスワードが無効 | WordPressで新しいパスワードを生成 |
| `RSS_FEEDS not configured` | RSSフィードが未設定 | .envのRSS_FEEDSを設定 |
| `No new articles to process` | キャッシュに記事が残っている | cache.jsonを削除して再実行 |

3. **キャッシュのクリア**
   ```bash
   del cache.json
   python main.py
   ```

## 🔄 定期実行の設定（GitHub Actions）

### ステップ1: GitHubリポジトリへのプッシュ

```bash
cd C:\Users\wandt\AI_coding\workspace\projects\newsbot
git add .
git commit -m "Configure newsbot for aaover60.com"
git push origin main
```

### ステップ2: GitHub Secretsの設定

GitHubリポジトリの Settings → Secrets and variables → Actions で以下を設定：

| Secret名 | 値 |
|---------|---|
| `LLM_PROVIDER` | `openai` |
| `OPENAI_API_KEY` | （.envの値をコピー） |
| `OPENAI_MODEL` | `gpt-4o-mini` |
| `WORDPRESS_URL` | `https://aaover60.com` |
| `WORDPRESS_USERNAME` | `newsbot` |
| `WORDPRESS_APP_PASSWORD` | （.envの値をコピー・スペースあり） |
| `RSS_FEEDS` | （.envの値をコピー） |
| `CACHE_DURATION_HOURS` | `24` |
| `MAX_ARTICLES_PER_RUN` | `5` （推奨：コスト管理） |
| `MAX_TOKENS_PER_RUN` | `10000` （推奨：コスト管理） |
| `ALLOWLIST_PATH` | `config/allowlist.txt` |
| `PROMPT_VARIANT` | `default` |
| `JSON_LOGS` | `false` |
| `DRAFT_PATH` | `out/draft.md` |

### ステップ3: GitHub Actionsの確認

1. GitHubリポジトリの `Actions` タブを開く
2. `.github/workflows/newsbot.yml` が存在するか確認
3. 手動実行してテスト:
   - `newsbot` ワークフローを選択
   - `Run workflow` をクリック
   - 実行結果を確認

### ステップ4: 定期実行スケジュールの設定

`.github/workflows/newsbot.yml`のcron設定を確認：

```yaml
on:
  schedule:
    - cron: '0 0 * * *'  # 毎日09:00 JST (00:00 UTC)
```

変更したい場合は、cron式を編集してpush:
- 毎日朝9時: `'0 0 * * *'`
- 毎日昼12時: `'0 3 * * *'`
- 週3回（月・水・金）: `'0 0 * * 1,3,5'`

## 📊 運用モニタリング

### 日次チェック項目

1. **GitHub Actionsの実行結果**
   - 緑のチェックマーク: 成功
   - 赤のバツマーク: 失敗（ログを確認）

2. **WordPress下書き**
   - 記事の品質を確認
   - 必要に応じて編集して公開

3. **コスト管理**
   - OpenAI APIの使用量を確認
   - 予算を超えそうな場合は`MAX_ARTICLES_PER_RUN`を減らす

### 週次チェック項目

1. **RSSフィードの見直し**
   - 不要なフィードを削除
   - 新しいフィードを追加

2. **記事品質の確認**
   - プロンプトの調整が必要か検討
   - `prompts/`ディレクトリ内のファイルを編集

## ❓ トラブルシューティング

### Q: 記事が生成されない

**A**: 以下を確認してください：
1. `cache.json`を削除
2. RSSフィードURLが有効か確認（ブラウザで開いてみる）
3. `allowlist.txt`にドメインが追加されているか確認

### Q: WordPress投稿に失敗する

**A**: 以下を確認してください：
1. アプリケーションパスワードが有効か
2. newsbotユーザーに投稿権限があるか
3. WordPress REST APIが有効か（`https://aaover60.com/wp-json/wp/v2/posts`にアクセス）

### Q: OpenAI APIエラーが出る

**A**: 以下を確認してください：
1. APIキーが有効か
2. モデル名が正しいか（`gpt-4o-mini`など）
3. OpenAIアカウントに残高があるか
4. レート制限に達していないか

### Q: コストが心配

**A**: .envに以下を設定してください：
```env
MAX_ARTICLES_PER_RUN=3
MAX_TOKENS_PER_RUN=5000
```

## 📞 サポート

問題が解決しない場合は、以下の情報を用意してサポートに連絡してください：

1. `newsbot.log`の内容
2. `out/draft.md`の内容
3. エラーメッセージのスクリーンショット
4. `.env`ファイルの内容（APIキーは伏せる）

---

**次のステップ**: このガイドに従ってテスト実行を行ってください。成功したら、GitHub Actionsの設定に進みましょう！
