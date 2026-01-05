# GitHub Secrets セットアップガイド

このガイドに従って、GitHub Actionsで自動実行するために必要なSecretsを設定してください。

## Secretsの設定方法

1. GitHubリポジトリページを開く
2. **Settings** タブをクリック
3. 左サイドバーから **Secrets and variables** → **Actions** を選択
4. **New repository secret** ボタンをクリック
5. 以下の各Secretを追加

## 必須設定

### LLM Provider (どちらか1つ)

#### OpenAI を使用する場合
- **Name**: `OPENAI_API_KEY`
- **Value**: `sk-proj-...` (OpenAI API キー)

#### Anthropic を使用する場合
- **Name**: `ANTHROPIC_API_KEY`
- **Value**: `sk-ant-...` (Anthropic API キー)

### WordPress設定

- **Name**: `WORDPRESS_URL`
- **Value**: `https://your-site.com` (WordPressサイトURL)

- **Name**: `WORDPRESS_USERNAME`
- **Value**: `your-username` (WordPressユーザー名)

- **Name**: `WORDPRESS_APP_PASSWORD`
- **Value**: `xxxx xxxx xxxx xxxx` (WordPressアプリケーションパスワード)

### RSS設定

- **Name**: `RSS_FEEDS`
- **Value**: `https://feed1.xml,https://feed2.xml` (カンマ区切り)

### Unsplash設定（オプション - アイキャッチ画像用）

- **Name**: `UNSPLASH_ACCESS_KEY`
- **Value**: `your-access-key` (Unsplash API Access Key)
- **説明**: アイキャッチ画像を自動取得するために必要。設定しない場合は画像なしで投稿されます

## オプション設定（推奨）

以下のSecretsは必須ではありませんが、設定することでコスト管理やカスタマイズが可能です。

- **Name**: `LLM_PROVIDER`
- **Value**: `openai`
- **説明**: 使用するLLMプロバイダー（`openai` または `anthropic`）

- **Name**: `OPENAI_MODEL`
- **Value**: `gpt-4o-mini`
- **説明**: OpenAIのモデル名（例: `gpt-4o-mini`, `gpt-4o`）

- **Name**: `ANTHROPIC_MODEL`
- **Value**: `claude-sonnet-4-5`
- **説明**: Anthropicのモデル名（例: `claude-sonnet-4-5`, `claude-opus-4`）

- **Name**: `MAX_ARTICLES_PER_RUN`
- **Value**: `5`
- **説明**: 1回の実行で処理する最大記事数（コスト制御に有効）

- **Name**: `MAX_TOKENS_PER_RUN`
- **Value**: `10000`
- **説明**: 1回の実行で使用する最大トークン数（コスト制御に有効）

- **Name**: `CACHE_DURATION_HOURS`
- **Value**: `24`
- **説明**: キャッシュの有効期限（時間）。同じ記事を重複投稿しないための仕組み

- **Name**: `PROMPT_VARIANT`
- **Value**: `default`
- **説明**: プロンプトのバリアント名（`prompts/`ディレクトリ内のサブディレクトリ名）

- **Name**: `JSON_LOGS`
- **Value**: `false`
- **説明**: JSON形式でログを出力する場合は`true`に設定（メトリクス収集に便利）

## WordPress アプリケーションパスワードの取得方法

1. WordPressダッシュボードにログイン
2. **ユーザー** → **プロフィール**
3. 下にスクロールして「**アプリケーションパスワード**」セクションを見つける
4. 新しいアプリケーション名（例: "newsbot"）を入力
5. 「**新しいアプリケーションパスワードを追加**」をクリック
6. 表示されたパスワード（スペース区切り）をコピー
7. GitHub Secretsの `WORDPRESS_APP_PASSWORD` に設定

## Unsplash API Access Keyの取得方法

1. [Unsplash Developers](https://unsplash.com/developers)にアクセス
2. **Register as a developer**をクリックしてアカウント作成（既にアカウントがある場合はログイン）
3. **Your apps**から**New Application**をクリック
4. 利用規約に同意し、アプリケーション名（例: "newsbot"）と説明を入力
5. **Create application**をクリック
6. **Keys**セクションに表示される**Access Key**をコピー
7. GitHub Secretsの `UNSPLASH_ACCESS_KEY` に設定

**注意事項:**
- 無料プランは50リクエスト/時間まで
- 商用利用可能（Unsplashライセンス）
- 画像使用時は撮影者のクレジット表示が推奨されます（自動で設定されます）

## 設定確認

全て設定したら、GitHub Actionsの「Actions」タブで手動実行して確認できます：

1. **Actions** タブを開く
2. **newsbot** ワークフローを選択
3. **Run workflow** ボタンをクリック
4. ブランチを選択（chore/hardening-mvp または main）
5. **Run workflow** を実行

## aaover60.com 用の設定例

以下は、aaover60.comで使用している実際の設定値の例です（APIキーとパスワードは除く）：

```
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4o-mini
WORDPRESS_URL=https://aaover60.com
WORDPRESS_USERNAME=newsbot
RSS_FEEDS=https://www.nhk.or.jp/rss/news/cat0.xml,https://www.nhk.or.jp/rss/news/cat6.xml,https://rss.itmedia.co.jp/rss/2.0/news_bursts.xml
CACHE_DURATION_HOURS=24
MAX_ARTICLES_PER_RUN=5
MAX_TOKENS_PER_RUN=10000
PROMPT_VARIANT=default
JSON_LOGS=false
```

## セキュリティ注意事項

- Secretsは暗号化されて保存されます
- ログには `***` でマスクされます
- 決してコードにハードコードしないでください
- 定期的にキーをローテーションしてください

## スケジュール設定

現在の設定では、**毎日18:00 JST（09:00 UTC）**に自動実行されます。
スケジュールを変更したい場合は、`.github/workflows/newsbot.yml`の`cron`行を編集してください。

例：
- `'0 0 * * *'` → 毎日 09:00 JST（00:00 UTC）
- `'0 3 * * *'` → 毎日 12:00 JST（03:00 UTC）
- `'0 9 * * *'` → 毎日 18:00 JST（09:00 UTC）【現在の設定】
