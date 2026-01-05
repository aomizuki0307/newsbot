# GitHub Actions セットアップ手順

**作成日**: 2026-01-04  
**目的**: GitHub Actions で newsbot を自動実行する

---

## ✅ 現在の状況

- `.github/workflows/newsbot-seo-hatena.yml` が存在します（SEO記事専用）
- 手動実行（workflow_dispatch）と定期実行（cron）の両方に対応済み
- はてなブログへの自動投稿設定済み

---

## 📋 実行可能かどうかの確認結果

**結論**: はい、実行可能です！

以下の2つの方法で実行できます：

### 1. **手動実行** (今すぐテスト可能)

GitHub の Actions タブから手動でトリガーできます：

1. リポジトリをGitHubにプッシュ
2. `https://github.com/aomizuki0307/newsbot/actions` にアクセス
3. 左サイドバーから「newsbot-seo-hatena」を選択
4. 右上の「Run workflow」ボタンをクリック
5. ブランチを選択（通常は `main` または現在のブランチ）
6. 「Run workflow」で実行開始

### 2. **定期実行** (毎日自動)

- 毎日 **10:00 JST** (01:00 UTC) に自動実行されます
- 設定不要（ワークフローファイルに記載済み）

---

## 🔧 必要な設定

### ステップ1: GitHubにプッシュ

まず、ワークフローファイルをGitHubにプッシュする必要があります：

```bash
cd C:\Users\wandt\AI_coding\workspace\projects\newsbot

# 変更をステージング
git add .github/workflows/newsbot-seo-hatena.yml

# コミット
git commit -m "Add GitHub Actions workflow for automated SEO article posting"

# GitHubにプッシュ（現在のブランチ名を指定）
git push origin chore/hardening-mvp
# または main ブランチの場合: git push origin main
```

### ステップ2: GitHub Secrets の設定

リポジトリの **Settings → Secrets and variables → Actions** で以下を設定：

#### 必須のSecrets

| Secret名 | 説明 | 例 |
|---------|------|-----|
| `LLM_PROVIDER` | LLMプロバイダー | `openai` または `anthropic` |
| `OPENAI_API_KEY` | OpenAI APIキー | `sk-...` |
| `ANTHROPIC_API_KEY` | Anthropic APIキー | `sk-ant-...` |
| `HATENA_ID` | はてなID | `your-hatena-id` |
| `HATENA_BLOG_ID` | はてなブログID | `your-blog-id` |
| `HATENA_API_KEY` | はてなAPIキー | `...` |
| `RSS_FEEDS` | RSSフィードURL（カンマ区切り） | `https://example.com/feed1,https://example.com/feed2` |

#### OAuth認証（画像アップロード用）

| Secret名 | 説明 |
|---------|------|
| `HATENA_OAUTH_CONSUMER_KEY` | OAuth Consumer Key |
| `HATENA_OAUTH_CONSUMER_SECRET` | OAuth Consumer Secret |
| `HATENA_OAUTH_ACCESS_TOKEN` | OAuth Access Token |
| `HATENA_OAUTH_ACCESS_TOKEN_SECRET` | OAuth Access Token Secret |

#### Unsplash（画像取得用）

| Secret名 | 説明 |
|---------|------|
| `UNSPLASH_ACCESS_KEY` | Unsplash Access Key |

#### オプションのSecrets

| Secret名 | デフォルト値 | 説明 |
|---------|------------|------|
| `OPENAI_MODEL` | `gpt-4-turbo-preview` | OpenAIモデル |
| `ANTHROPIC_MODEL` | `claude-3-sonnet-20240229` | Anthropicモデル |
| `HATENA_CATEGORIES` | `SEO,副業,集客` | はてなブログカテゴリ（カンマ区切り） |
| `CACHE_DURATION_HOURS` | `24` | キャッシュ保持時間 |
| `MAX_ARTICLES_PER_RUN` | `0` | 1回の実行で処理する最大記事数 |
| `MAX_TOKENS_PER_RUN` | `0` | 1回の実行で使用する最大トークン数 |
| `PROMPT_VARIANT` | `seo` | プロンプトバリアント |
| `IMAGE_SELECTION_MODE` | `llm` | 画像選定モード（`llm` / `random`） |
| `IMAGE_SELECTION_PROVIDER` | `openai` | 画像選定LLMプロバイダー |
| `IMAGE_SELECTION_CANDIDATES` | `5` | 画像候補数 |
| `IMAGE_REVIEW_ENABLED` | `true` | 画像レビュー有効化 |
| `IMAGE_REVIEW_PROVIDER` | `openai` | 画像レビューLLMプロバイダー |
| `HATENA_FORMAT_PARAGRAPHS` | `true` | 段落整形有効化 |
| `HATENA_PARAGRAPH_SENTENCES` | `2` | 段落あたりの文数 |
| `VALIDATION_ENABLED` | `true` | バリデーション有効化 |
| `AUTO_IMPROVE_ITERATIONS` | `3` | 自動改善イテレーション数 |

---

## 🚀 初回実行手順

### 1. ワークフローファイルをプッシュ

```bash
git add .github/workflows/newsbot-seo-hatena.yml GITHUB_ACTIONS_SETUP.md
git commit -m "Add GitHub Actions workflow and setup guide"
git push origin chore/hardening-mvp
# または main ブランチの場合: git push origin main
```

### 2. GitHub Secrets を設定

1. `https://github.com/aomizuki0307/newsbot/settings/secrets/actions` にアクセス
2. 「New repository secret」をクリック
3. 上記の必須Secretsを1つずつ追加

### 3. 手動実行でテスト

1. `https://github.com/aomizuki0307/newsbot/actions` にアクセス
2. 「newsbot-seo-hatena」を選択
3. 「Run workflow」をクリック
4. ブランチを選択
5. 「Run workflow」で実行

### 4. ログとアーティファクトを確認

実行が完了したら：

1. ワークフロー実行ページで「run」ジョブをクリック
2. ログを確認して正常に完了したか確認
3. アーティファクトセクションで以下をダウンロード可能：
   - `seo-hatena-draft-{run_number}`: 生成された記事とログ

---

## 🔍 ワークフローの特徴

### SEOプロファイル専用

- `--profile seo` で自動実行
- `.env.seo` の設定を使用
- SEO系RSSフィードから記事収集

### 環境変数設定

ワークフローは自動的に以下を設定：

- `NEWSBOT_PROFILE=seo`: SEOプロファイル
- `HATENA_DRAFT=false`: 公開投稿
- `AUTO_REPUBLISH=false`: 検証サイクルでの二重投稿防止
- `NEWSBOT_DOTENV_OVERRIDE=false`: スクリプト設定優先
- `PUBLISH_PLATFORM=hatena`: はてなブログ投稿

### キャッシュ管理

- 成功時に `cache.json` を自動コミット
- 24時間以内の重複記事をスキップ
- GitHub Actions bot でコミット

### アーティファクト保存

- **seo-hatena-draft**: 生成された記事とログ（30日間保存）

---

## 📊 実行確認

### Actions タブでの確認

1. `https://github.com/aomizuki0307/newsbot/actions` にアクセス
2. 最新の実行をクリック
3. 各ステップのログを確認：
   - ✅ Checkout code
   - ✅ Set up Python 3.11
   - ✅ Install dependencies
   - ✅ Create .env file
   - ✅ Run newsbot (seo profile)
   - ✅ Upload draft artifact
   - ✅ Commit cache

### はてなブログでの確認

実行が成功すると、はてなブログに記事が公開されます：

1. `https://{HATENA_BLOG_ID}.hatenablog.com/` にアクセス
2. 最新の記事を確認

---

## 🛠️ トラブルシューティング

### 問題1: ワークフローが表示されない

**原因**: ワークフローファイルがGitHubにプッシュされていない

**解決策**:
```bash
git add .github/workflows/newsbot-seo-hatena.yml
git commit -m "Add GitHub Actions workflow for SEO articles"
git push origin chore/hardening-mvp
# または main ブランチの場合: git push origin main
```

### 問題2: Secret not found エラー

**原因**: GitHub Secrets が設定されていない

**解決策**:
1. `https://github.com/aomizuki0307/newsbot/settings/secrets/actions` にアクセス
2. 必要なSecretsを追加

### 問題3: 実行は成功するが記事が生成されない

**確認項目**:

1. **ログを確認**:
   - Actions タブ → 実行 → 「Run newsbot」ステップのログを確認

2. **アーティファクトを確認**:
   - アーティファクトセクションから `logs-{run_number}` をダウンロード
   - `newsbot.log` を確認

3. **Secrets の設定を確認**:
   - `LLM_PROVIDER` が正しく設定されているか
   - APIキーが正しいか
   - `RSS_FEEDS` が設定されているか

### 問題4: 記事は生成されるが投稿されない

**確認項目**:

1. **はてなブログの認証情報**:
   - `HATENA_ID`, `HATENA_BLOG_ID`, `HATENA_API_KEY` が正しいか

2. **ネットワーク接続**:
   - GitHub Actions からはてなブログへの接続が可能か

---

## 📚 関連ドキュメント

- **GitHub Actions ワークフロー**: `.github/workflows/newsbot-seo-hatena.yml`
- **Windows Task Scheduler**: `SETUP_SCHEDULER.md`
- **実装プラン**: `.claude/plans/composed-jingling-moon.md`
- **プロジェクト README**: `README.md`
- **プロジェクトガイド**: `CLAUDE.md`, `AGENTS.md`

---

## 🎯 次のステップ

1. ✅ ワークフローファイル作成（完了）
2. ⬜ GitHubにプッシュ
3. ⬜ GitHub Secrets を設定
4. ⬜ 手動実行でテスト
5. ⬜ ログとアーティファクトを確認
6. ⬜ はてなブログで記事を確認
7. ⬜ 定期実行を待つ（翌日10:00 JST）

---

**作成者**: Claude Code  
**作成日**: 2026-01-04
