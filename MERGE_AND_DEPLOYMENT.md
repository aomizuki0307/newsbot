# マージ＆デプロイメントガイド

## 3. マージ & スケジュール確認

### マージ方法

**推奨: Squash and merge**

理由：
- コミット履歴が整理される
- 1つのPRが1つのコミットになる
- mainブランチがクリーンに保たれる

### 手順

#### GitHub Web UI でマージ

1. https://github.com/aomizuki0307/newsbot/pull/1 を開く

2. 「**Merge pull request**」の横のドロップダウンをクリック

3. 「**Squash and merge**」を選択

4. コミットメッセージを確認：
   ```
   chore: hardening MVP (retries, async, SSRF, prompts, e2e, CI, observability) (#1)

   Hardeningレポート（HARDENING_REPORT.md）に詳細あり。主な変更点:
   リトライ/バックオフ(≤5回・30s上限)、要約の同時5件処理、
   HTTPS+allowlist+private IP拒否、プロンプト外出し、E2Eスモーク、
   CI(3.10/3.11)とアーティファクト、検証コマンド、JSONメトリクス。
   ```

5. 「**Confirm squash and merge**」をクリック

6. ブランチ削除（オプション）：「**Delete branch**」をクリック

#### GitHub CLI でマージ（代替手段）

```bash
# Squash merge
gh pr merge 1 --repo aomizuki0307/newsbot --squash --delete-branch

# または通常のマージ
gh pr merge 1 --repo aomizuki0307/newsbot --merge
```

---

## スケジュール確認

### Cron設定の確認

マージ後、`.github/workflows/newsbot.yml` がmainブランチに存在することを確認：

```yaml
on:
  schedule:
    # Run daily at 09:00 JST (00:00 UTC)
    - cron: '0 0 * * *'
  workflow_dispatch:
    # Allow manual trigger
```

**重要:** GitHub Actions のスケジュールは **default branch（main）の定義**が実行されます。

### 実行タイミング

- **自動実行**: 毎日 00:00 UTC = 09:00 JST
- **初回実行**: マージ翌日の 09:00 JST
- **手動実行**: いつでも可能（workflow_dispatch）

### スケジュール動作確認

```bash
# 次回実行予定を確認（GitHub UIで）
# https://github.com/aomizuki0307/newsbot/actions

# 手動でテスト実行
gh workflow run newsbot.yml --repo aomizuki0307/newsbot
```

### タイムゾーンについて

- GitHub Actions は **UTC基準**
- JST（日本標準時）は UTC+9
- `0 0 * * *` = 00:00 UTC = **09:00 JST**

他の時刻に変更したい場合：
- 00:00 JST (15:00 UTC前日) → `0 15 * * *`
- 12:00 JST (03:00 UTC) → `0 3 * * *`
- 18:00 JST (09:00 UTC) → `0 9 * * *`

---

## 4. 本番スモーク実行

### Phase 1: DRY_RUN=true（推奨）

**目的:** WordPressへの投稿なしで、全フロー確認

#### 手順

1. **Secretsを確認**
   - https://github.com/aomizuki0307/newsbot/settings/secrets/actions
   - `DRY_RUN=true` が設定されているか確認

2. **手動実行**
   ```bash
   # GitHub CLI
   gh workflow run newsbot.yml --repo aomizuki0307/newsbot --ref main

   # または GitHub Web UI
   # https://github.com/aomizuki0307/newsbot/actions
   # → newsbot → Run workflow
   ```

3. **実行状況を確認**
   ```bash
   # 最新の実行を確認
   gh run list --repo aomizuki0307/newsbot --limit 5

   # 特定の実行を監視
   gh run watch <run-id> --repo aomizuki0307/newsbot
   ```

4. **成果物を確認**
   - **Artifacts**: `out/draft.md` がダウンロード可能か
   - **ログ**: 最後の行に `run_metrics={...}` JSON が出力されているか

#### 確認ポイント

ログの最後に以下のようなJSONが出力されること：
```json
{
  "run_metrics": {
    "articles_collected": 2,
    "articles_after_limit": 2,
    "summaries_generated": 2,
    "summaries_failed": 0,
    "tokens_estimated": 1200,
    "token_limit_reached": false,
    "wordpress_published": false,  ← DRY_RUN=trueの場合
    "duration_seconds": 8.42
  }
}
```

**Artifacts確認:**
```bash
# CLIでダウンロード
gh run download <run-id> --repo aomizuki0307/newsbot

# Web UIで確認
# Actionsの実行ページ → Artifacts セクション
```

---

### Phase 2: DRY_RUN=false（本番）

**目的:** WordPressへの下書き投稿を実行

#### 前提条件

✅ Phase 1が成功
✅ WordPress設定（URL, Username, App Password）が正しい
✅ `out/draft.md` の内容が適切

#### 手順

1. **DRY_RUNを無効化**
   - Secretsで `DRY_RUN` を削除、または `false` に変更
   - https://github.com/aomizuki0307/newsbot/settings/secrets/actions

2. **手動実行**
   ```bash
   gh workflow run newsbot.yml --repo aomizuki0307/newsbot --ref main
   ```

3. **WordPressを確認**
   - ダッシュボード → **投稿** → **下書き**
   - 新しい下書き記事が作成されているか確認

4. **ログで確認**
   ```json
   {
     "run_metrics": {
       ...
       "wordpress_published": true,  ← trueになっていること
       ...
     }
   }
   ```

#### トラブルシューティング

**WordPress投稿が失敗する場合:**

1. **認証エラー**
   - アプリケーションパスワードが正しいか確認
   - WordPressのREST APIが有効か確認（通常はデフォルトで有効）

2. **権限エラー**
   - ユーザーに「投稿」権限があるか確認
   - 「管理者」または「編集者」ロールが必要

3. **接続エラー**
   - `WORDPRESS_URL` が正しいか確認（末尾のスラッシュなし）
   - HTTPSで接続可能か確認

---

## 5. 後続タスク（運用改善）

### Allowlist運用

**README に追記推奨:**

```markdown
## Allowlist更新手順

1. `config/allowlist.txt` を編集
2. 追加したいドメインを1行ずつ記載（HTTPS必須）
3. コミット＆プッシュ
4. mainにマージされると次回実行から有効
```

### ブランチ保護

**Settings → Branches → main**

- ✅ Require a pull request before merging
- ✅ Require status checks to pass: `test`
- ✅ Require conversation resolution before merging

### 監視（任意・次PR）

環境変数で制御できるように：

- `SENTRY_DSN` - Sentryエラートラッキング
- `DATADOG_API_KEY` - Datadog APM
- `SLACK_WEBHOOK` - Slack通知

### GitHub Issues化

以下を個別Issueに分解：

1. **Native async support** (#2)
   - OpenAI/Anthropic SDKの非同期版を使用
   - ThreadPoolExecutor を削除

2. **Token estimation accuracy** (#3)
   - `tiktoken` または model-specific tokenizer を使用
   - より正確なトークン数見積もり

3. **Allowlist automation** (#4)
   - GitHub Actionsで定期的にallowlistを検証
   - 無効なドメインを自動検出

4. **User-Agent & Timeout settings** (#5)
   - newspaper3k の明示的な設定
   - 環境変数化

---

## チェックリスト

マージ前：
- [ ] PR #1 レビュー完了
- [ ] CIグリーン（マージ後に実行）
- [ ] Secrets設定完了

マージ後：
- [ ] mainブランチに反映確認
- [ ] Cron設定確認（.github/workflows/newsbot.yml）

本番前：
- [ ] DRY_RUN=true で手動実行
- [ ] Artifacts（draft.md）確認
- [ ] メトリクスJSON確認

本番：
- [ ] DRY_RUN=false に変更
- [ ] 手動実行
- [ ] WordPress下書き確認

運用：
- [ ] Allowlist更新手順をREADMEに追記
- [ ] ブランチ保護設定
- [ ] 残課題をIssues化
