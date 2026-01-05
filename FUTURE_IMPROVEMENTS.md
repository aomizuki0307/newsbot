# 将来の改善項目

このドキュメントは、newsbot の運用改善と機能拡張のために、個別のGitHub Issuesとして作成すべき項目をリストアップしています。

---

## Issue #2: Native async support

**タイトル:** Migrate to native async LLM clients

**説明:**
現在、要約処理は ThreadPoolExecutor を使用して非同期処理を実現していますが、OpenAI/Anthropic SDKのネイティブasyncサポートに移行することで、よりクリーンで効率的な実装が可能です。

**現状:**
```python
# src/summarize.py
executor = ThreadPoolExecutor(max_workers=SUMMARY_CONCURRENCY)
# ブロッキングAPIをThreadPoolで実行
```

**改善案:**
```python
# OpenAI async client
from openai import AsyncOpenAI
client = AsyncOpenAI()
response = await client.chat.completions.create(...)

# Anthropic async client
from anthropic import AsyncAnthropic
client = AsyncAnthropic()
response = await client.messages.create(...)
```

**メリット:**
- スレッドオーバーヘッド削減
- より正確なキャンセル制御
- メモリ効率の向上
- コードの可読性向上

**作業見積もり:** 2-3時間

**Priority:** Medium

---

## Issue #3: Token estimation accuracy

**タイトル:** Improve token counting accuracy with model-specific tokenizers

**説明:**
現在のトークン見積もりは簡易的な計算（文字数ベース）を使用していますが、`tiktoken` などのモデル固有のトークナイザーを使用することで、より正確なトークン数管理が可能になります。

**現状:**
```python
# 簡易見積もり（文字数 / 4）
estimated_tokens = len(text) // 4
```

**改善案:**
```python
import tiktoken

# OpenAI
encoder = tiktoken.encoding_for_model("gpt-4-turbo-preview")
token_count = len(encoder.encode(text))

# Anthropic
from anthropic import Anthropic
client = Anthropic()
token_count = client.count_tokens(text)
```

**メリット:**
- コスト管理の精度向上
- トークン制限の正確な適用
- バジェット超過リスクの低減

**Dependencies:**
- `tiktoken>=0.5.0`

**作業見積もり:** 2時間

**Priority:** High（コスト管理に直結）

---

## Issue #4: Allowlist automation

**タイトル:** Automate allowlist validation in CI

**説明:**
`config/allowlist.txt` の内容を自動的に検証し、無効なドメインや到達不可能なエンドポイントを検出するGitHub Actionsワークフローを追加します。

**実装内容:**

1. **新しいワークフロー:** `.github/workflows/validate-allowlist.yml`
   ```yaml
   name: Validate Allowlist
   on:
     pull_request:
       paths:
         - 'config/allowlist.txt'
     schedule:
       - cron: '0 0 * * 0'  # Weekly
   ```

2. **検証スクリプト:** `scripts/validate_allowlist.py`
   ```python
   import socket
   import ssl

   def validate_domain(domain):
       # DNS resolution check
       # HTTPS accessibility check
       # Certificate validation
   ```

3. **検証項目:**
   - DNS解決可能性
   - HTTPS接続可能性
   - SSL証明書の有効性
   - 重複エントリの検出

**メリット:**
- 無効なドメインの早期発見
- セキュリティリスクの低減
- メンテナンス作業の軽減

**作業見積もり:** 3-4時間

**Priority:** Medium

---

## Issue #5: User-Agent & Timeout configuration

**タイトル:** Add explicit User-Agent and timeout settings for article extraction

**説明:**
newspaper3k のデフォルト設定に依存せず、明示的にUser-Agentとタイムアウトを設定することで、より制御可能で安定した記事抽出を実現します。

**現状:**
```python
# デフォルト設定に依存
article = Article(url)
article.download()
```

**改善案:**
```python
from newspaper import Config

config = Config()
config.browser_user_agent = os.getenv(
    'ARTICLE_USER_AGENT',
    'Mozilla/5.0 (compatible; newsbot/1.0; +https://github.com/aomizuki0307/newsbot)'
)
config.request_timeout = int(os.getenv('ARTICLE_TIMEOUT', '10'))
config.number_threads = 1  # 明示的にシングルスレッド

article = Article(url, config=config)
article.download()
```

**環境変数:**
- `ARTICLE_USER_AGENT`: User-Agent文字列
- `ARTICLE_TIMEOUT`: タイムアウト秒数（デフォルト: 10）

**メリット:**
- タイムアウトの明示的制御
- User-Agent識別による問題切り分け
- 環境別設定の柔軟性

**作業見積もり:** 1-2時間

**Priority:** Medium-High

---

## Issue #6: Structured logging with correlation IDs

**タイトル:** Add correlation IDs for request tracing

**説明:**
各実行に一意のcorrelation IDを付与し、ログのトレーサビリティを向上させます。

**実装内容:**

1. **Correlation ID生成**
   ```python
   import uuid

   correlation_id = str(uuid.uuid4())
   logger = logging.LoggerAdapter(logger, {'correlation_id': correlation_id})
   ```

2. **全ログに自動付与**
   ```python
   # ログフォーマット
   "%(asctime)s - %(correlation_id)s - %(name)s - %(levelname)s - %(message)s"
   ```

3. **メトリクスにも含める**
   ```json
   {
     "correlation_id": "abc-123-def",
     "run_metrics": {...}
   }
   ```

**メリット:**
- 複数実行の区別が容易
- エラー追跡の効率化
- 監視ツール連携の改善

**作業見積もり:** 2時間

**Priority:** Low-Medium

---

## Issue #7: Webhook notifications

**タイトル:** Add Slack/Discord webhook notifications

**説明:**
実行結果を Slack または Discord に通知する機能を追加します。

**実装内容:**

1. **環境変数**
   - `SLACK_WEBHOOK_URL`
   - `DISCORD_WEBHOOK_URL`
   - `NOTIFY_ON_SUCCESS`: 成功時も通知するか（デフォルト: false）
   - `NOTIFY_ON_FAILURE`: 失敗時に通知するか（デフォルト: true）

2. **通知内容**
   ```json
   {
     "title": "newsbot 実行完了",
     "status": "success",
     "metrics": {
       "articles": 5,
       "wordpress": true
     },
     "draft_url": "https://github.com/.../artifacts/..."
   }
   ```

3. **エラー通知**
   ```json
   {
     "title": "newsbot 実行失敗",
     "status": "error",
     "error": "Failed to fetch RSS feed...",
     "logs_url": "https://github.com/.../runs/..."
   }
   ```

**作業見積もり:** 2-3時間

**Priority:** Low（Nice-to-have）

---

## Issue #8: Allowlist update automation

**タイトル:** README: Add allowlist update procedure

**説明:**
現在、`config/allowlist.txt` の更新手順がREADMEに明記されていません。運用者が迷わないように、明確な手順を追記します。

**追記内容:**

```markdown
## Allowlist管理

### ドメインの追加方法

1. `config/allowlist.txt` を編集
2. 追加したいドメインを1行ずつ記載（HTTPS必須）
   ```
   example.com
   tech.example.jp
   blog.example.org
   ```
3. コメント行（`#` で開始）でメモを残せます
   ```
   # Tech news sites
   example.com

   # Blog aggregator
   blog.example.org
   ```
4. コミット＆プッシュ
5. PRを作成してレビュー
6. mainにマージされると次回実行から有効

### 注意事項

- **HTTPS必須**: HTTPSでアクセスできないドメインは追加不可
- **Private IP拒否**: 内部ネットワークやローカルホストは自動的に拒否されます
- **定期チェック**: 週次で到達可能性が自動検証されます（Issue #4実装後）
```

**作業見積もり:** 15分

**Priority:** High（ドキュメント不足）

---

## Issue #9: Branch protection rules

**タイトル:** Configure branch protection for main

**説明:**
main ブランチに保護ルールを設定し、CI通過とレビュー承認を必須化します。

**設定内容:**

Settings → Branches → Branch protection rules → main

- ✅ **Require a pull request before merging**
  - Require approvals: 1（個人プロジェクトの場合は0でも可）
  - Dismiss stale approvals when new commits are pushed

- ✅ **Require status checks to pass before merging**
  - Status checks: `test` (Python 3.10 / 3.11)

- ✅ **Require conversation resolution before merging**

- ✅ **Require linear history** (Squash mergeを強制)

- ✅ **Do not allow bypassing** (管理者も従う)

**作業見積もり:** 5分（設定のみ）

**Priority:** High（コード品質保護）

---

## Issue #10: Monitoring integration

**タイトル:** Add optional Sentry/Datadog integration

**説明:**
エラートラッキングとパフォーマンス監視のためのオプショナル統合を追加します。

**実装内容:**

1. **Sentry統合**
   ```python
   import sentry_sdk

   if os.getenv('SENTRY_DSN'):
       sentry_sdk.init(
           dsn=os.getenv('SENTRY_DSN'),
           traces_sample_rate=0.1,
           profiles_sample_rate=0.1,
       )
   ```

2. **Datadog統合**
   ```python
   from ddtrace import tracer

   if os.getenv('DATADOG_API_KEY'):
       # APM tracing
       @tracer.wrap()
       def summarize_articles(...):
   ```

3. **環境変数**
   - `SENTRY_DSN`: Sentry DSN（オプション）
   - `DATADOG_API_KEY`: Datadog API key（オプション）
   - `ENABLE_PROFILING`: プロファイリング有効化

**Dependencies:**
- `sentry-sdk>=1.40.0`（オプション）
- `ddtrace>=2.0.0`（オプション）

**作業見積もり:** 3-4時間

**Priority:** Low（本番運用後に検討）

---

## 優先順位まとめ

### High Priority
1. **Issue #3**: Token estimation accuracy（コスト管理）
2. **Issue #5**: User-Agent & Timeout（安定性）
3. **Issue #8**: README allowlist procedure（ドキュメント）
4. **Issue #9**: Branch protection（品質管理）

### Medium Priority
5. **Issue #2**: Native async support（パフォーマンス）
6. **Issue #4**: Allowlist automation（運用効率）
7. **Issue #6**: Correlation IDs（可観測性）

### Low Priority
8. **Issue #7**: Webhook notifications（Nice-to-have）
9. **Issue #10**: Monitoring integration（本番運用後）

---

## 次のアクション

1. 各Issueを個別にGitHubで作成
2. ラベルを付与（enhancement, documentation, etc.）
3. Milestoneを設定（v1.1, v1.2, etc.）
4. プロジェクトボードで管理

### Issue作成コマンド例

```bash
# Issue #3: Token estimation
gh issue create --repo aomizuki0307/newsbot \
  --title "Improve token counting accuracy with model-specific tokenizers" \
  --body-file .github/issues/token-estimation.md \
  --label enhancement,priority-high

# Issue #8: README update
gh issue create --repo aomizuki0307/newsbot \
  --title "README: Add allowlist update procedure" \
  --body "現在、allowlistの更新手順が明記されていません..." \
  --label documentation,priority-high
```
