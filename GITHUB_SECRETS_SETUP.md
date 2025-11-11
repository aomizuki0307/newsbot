# GitHub Secrets セットアップガイド

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

## オプション設定（推奨）

### 初回テスト用

- **Name**: `DRY_RUN`
- **Value**: `true`
- **説明**: 初回実行時はtrueにして、WordPressへの投稿をスキップ

### プロンプトバリアント

- **Name**: `PROMPT_VARIANT`
- **Value**: `default`
- **説明**: プロンプトのバリアントを指定（デフォルトは"default"）

### ログ形式

- **Name**: `JSON_LOGS`
- **Value**: `true`
- **説明**: JSON形式でログを出力（メトリクス収集に便利）

### その他

- **Name**: `LLM_PROVIDER`
- **Value**: `openai` または `anthropic`
- **説明**: 使用するLLMプロバイダー

- **Name**: `MAX_ARTICLES_PER_RUN`
- **Value**: `10`
- **説明**: 1回の実行で処理する最大記事数

- **Name**: `MAX_TOKENS_PER_RUN`
- **Value**: `50000`
- **説明**: 1回の実行で使用する最大トークン数

- **Name**: `CACHE_DURATION_HOURS`
- **Value**: `24`
- **説明**: キャッシュの有効期限（時間）

## WordPress アプリケーションパスワードの取得方法

1. WordPressダッシュボードにログイン
2. **ユーザー** → **プロフィール**
3. 下にスクロールして「**アプリケーションパスワード**」セクションを見つける
4. 新しいアプリケーション名（例: "newsbot"）を入力
5. 「**新しいアプリケーションパスワードを追加**」をクリック
6. 表示されたパスワード（スペース区切り）をコピー
7. GitHub Secretsの `WORDPRESS_APP_PASSWORD` に設定

## 設定確認

全て設定したら、GitHub Actionsの「Actions」タブで手動実行して確認できます：

1. **Actions** タブを開く
2. **newsbot** ワークフローを選択
3. **Run workflow** ボタンをクリック
4. ブランチを選択（chore/hardening-mvp または main）
5. **Run workflow** を実行

## セキュリティ注意事項

- Secretsは暗号化されて保存されます
- ログには `***` でマスクされます
- 決してコードにハードコードしないでください
- 定期的にキーをローテーションしてください
