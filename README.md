# newsbot

AI駆動型のRSS記事収集・要約・統合ツール。複数のRSSフィードから記事を収集し、LLMで要約・統合して1つの記事を生成し、WordPress に下書き投稿します。

## 特徴

- **自動収集**: RSSフィードから記事URLを収集し、本文を抽出
- **AI要約**: OpenAI/AnthropicのLLMで各記事を5要点に要約
- **記事生成**: 複数の要約を統合し、1200-1600字のMarkdown記事を生成
- **WordPress連携**: WordPress REST APIで下書き投稿
- **重複排除**: 24時間以内に処理した記事はスキップ（キャッシュ機能）
- **エラーハンドリング**: 失敗時は`out/draft.md`にエラー情報を保存
- **セキュリティ/堅牢性**: HTTPS + allowlist による許可ドメイン制御、SSRF防止、LLM/WordPress API のリトライとコスト上限ガード
- **可観測性**: JSONログをオプションで有効化し、処理件数・失敗件数・推定トークン・処理時間をメトリクスとして出力

## 必要要件

- Python 3.11以上
- OpenAI APIキーまたはAnthropic APIキー
- WordPress サイト（REST API有効、アプリケーションパスワード設定済み）

## セットアップ

### 1. リポジトリをクローン

```bash
git clone <repository-url>
cd newsbot
```

### 2. 依存関係をインストール

```bash
make setup
```

または手動で：

```bash
pip install -r requirements.txt
```

### 3. 環境変数を設定

`.env.sample`を`.env`にコピーして編集：

```bash
cp .env.sample .env
```

`.env`の設定項目：

```env
# LLM Provider: openai or anthropic
LLM_PROVIDER=openai

# OpenAI Settings
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4-turbo-preview

# Anthropic Settings
ANTHROPIC_API_KEY=your-anthropic-api-key-here
ANTHROPIC_MODEL=claude-3-sonnet-20240229

# WordPress Settings
WORDPRESS_URL=https://your-site.com
WORDPRESS_USERNAME=your-username
WORDPRESS_APP_PASSWORD=your-app-password

# RSS Feeds (comma-separated)
RSS_FEEDS=https://example.com/feed1.xml,https://example.com/feed2.xml

# Cache duration in hours (default: 24)
CACHE_DURATION_HOURS=24

# Optional guardrails / observability
MAX_ARTICLES_PER_RUN=0        # 0 = no limit
MAX_TOKENS_PER_RUN=0          # 0 = no limit
ALLOWLIST_PATH=config/allowlist.txt
PROMPT_VARIANT=default
JSON_LOGS=false
DRAFT_PATH=out/draft.md
```

#### WordPress アプリケーションパスワードの取得方法

1. WordPressダッシュボードにログイン
2. ユーザー → プロフィール
3. 「アプリケーションパスワード」セクションで新しいパスワードを生成
4. 生成されたパスワードを`.env`の`WORDPRESS_APP_PASSWORD`に設定

## 実行方法

### ローカルで実行

```bash
make run
```

または：

```bash
python main.py
```

実行すると：
1. RSSフィードから記事を収集
2. 各記事を要約
3. 統合記事を生成
4. `out/draft.md`に保存
5. WordPress に下書き投稿（設定されている場合）

### テスト実行

```bash
make test
```

### リント実行

```bash
make lint
```

### クリーンアップ

```bash
make clean
```

## GitHub Actions での自動実行

このプロジェクトは GitHub Actions で自動実行できます：

- **定期実行**: 毎日09:00 JST（00:00 UTC）に自動実行
- **手動実行**: GitHub の Actions タブから手動でトリガー可能

### GitHub Secrets の設定

リポジトリの Settings → Secrets and variables → Actions で以下を設定：

- `LLM_PROVIDER`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `ANTHROPIC_API_KEY`
- `ANTHROPIC_MODEL`
- `WORDPRESS_URL`
- `WORDPRESS_USERNAME`
- `WORDPRESS_APP_PASSWORD`
- `RSS_FEEDS`
- `CACHE_DURATION_HOURS`
- `MAX_ARTICLES_PER_RUN`
- `MAX_TOKENS_PER_RUN`
- `ALLOWLIST_PATH`
- `PROMPT_VARIANT`
- `JSON_LOGS`
- `DRAFT_PATH`

## プロジェクト構成

```
newsbot/
├── .github/
│   └── workflows/
│       └── newsbot.yml        # GitHub Actions workflow
├── src/
│   ├── __init__.py
│   ├── collect.py             # RSS収集・記事抽出
│   ├── summarize.py           # LLM要約
│   ├── compose.py             # 記事統合
│   └── publish_wordpress.py   # WordPress投稿
├── tests/
│   ├── test_collect.py
│   ├── test_summarize.py
│   └── test_publish_wordpress.py
├── main.py                    # メインエントリーポイント
├── requirements.txt           # Python依存関係
├── .env.sample                # 環境変数サンプル
├── .gitignore
├── Makefile                   # 便利コマンド
├── pytest.ini                 # pytest設定
└── README.md
```

## 拡張ポイント

### 1. RSS フィードの追加

`.env`の`RSS_FEEDS`にカンマ区切りで追加：

```env
RSS_FEEDS=https://feed1.xml,https://feed2.xml,https://feed3.xml
```

### 2. LLM プロバイダーの変更

`.env`の`LLM_PROVIDER`を変更：

```env
LLM_PROVIDER=anthropic  # openai または anthropic
```

### 3. プロンプトのカスタマイズ

`prompts/` ディレクトリ内の `summarize/`・`compose/` 配下テキストを編集して出力スタイルを変更できます。`PROMPT_VARIANT` を切り替えることでA/Bテストも可能です。

### 4. 記事抽出ロジックの改善

`src/collect.py`の`extract_article_content()`を拡張して、特定のサイトに対応したカスタム抽出ロジックを追加できます。

### 5. 投稿先の追加

`src/publish_wordpress.py`を参考に、他のCMS（はてなブログ、note等）への投稿機能を追加できます。

## 運用メモ

- 成功/失敗にかかわらず `out/draft.md` に最新のドラフトを保存します（CIではアーティファクトとして収集）。
- `config/allowlist.txt` に許可ドメインを記述することで、HTTPSかつ許可済みドメインの記事のみ収集します。プライベート/ループバックIPへ解決されるURLは自動的に拒否されます。
- `MAX_ARTICLES_PER_RUN` / `MAX_TOKENS_PER_RUN` で処理件数や推定トークン量に上限を設け、超過前に安全に停止します。
- `JSON_LOGS=true` を設定すると構造化ログになり、実行終了時に処理件数・失敗件数・推定トークン・処理時間などのメトリクスを1行で確認できます。

## 注意事項

### 著作権と出典

- このツールは記事を要約・統合しますが、**必ず元記事へのリンクを含めます**
- 生成された記事には参考リンクセクションが含まれます
- 商用利用の際は、各RSSフィードの利用規約を確認してください

### レート制限

- LLM APIには使用量制限があります。大量の記事を処理する場合は注意してください
- キャッシュ機能により、同じ記事は24時間以内に再処理されません

### エラー処理

- 記事抽出に失敗した場合、その記事はスキップされます
- 致命的なエラーが発生した場合、`draft.md`にエラー情報が保存されます
- ログは`newsbot.log`に出力されます

## トラブルシューティング

### newspaper3k のインストールエラー

newspaper3k は一部の環境でインストールに失敗する場合があります：

```bash
# 依存関係を個別にインストール
pip install lxml_html_clean
pip install newspaper3k
```

### WordPress 認証エラー

- アプリケーションパスワードが正しく設定されているか確認
- WordPress REST API が有効になっているか確認（通常はデフォルトで有効）
- HTTPS接続を推奨（一部のホスティングではHTTPでは認証が失敗）

### RSS フィードが取得できない

- フィードURLが正しいか確認
- ネットワーク接続を確認
- フィードが有効なXML形式か確認

## ライセンス

MIT License

## 開発

### テストの追加

`tests/`ディレクトリにテストファイルを追加：

```python
# tests/test_new_feature.py
def test_new_feature():
    assert True
```

### コントリビューション

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## サポート

問題や質問がある場合は、GitHubのIssuesで報告してください。
