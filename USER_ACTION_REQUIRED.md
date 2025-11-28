# 【重要】ユーザー作業が必要な項目リスト

このファイルは、**あなた（ユーザー）が実際に行う必要がある作業**をリストアップしたものです。
Claude Codeが自動的に実行できない作業のみを記載しています。

---

## ✅ 今すぐ実行すべき作業

### 1. .envファイルのRSS_FEEDSを設定 ⭐️最優先

**ファイル**: `workspace/projects/newsbot/.env` の18行目

**現在の設定**:
```env
RSS_FEEDS=https://example.com/feed1.xml,https://example.com/feed2.xml
```

**変更後（推奨）**:
```env
RSS_FEEDS=https://www.nhk.or.jp/rss/news/cat0.xml,https://www.nhk.or.jp/rss/news/cat6.xml,https://rss.itmedia.co.jp/rss/2.0/news_bursts.xml
```

**参考**: 他の選択肢は `RSS_FEED_GUIDE.md` を参照してください。

---

### 2. WordPressのアプリケーションパスワード確認

**確認方法**:
1. https://aaover60.com/wp-admin/ にログイン
2. `ユーザー` → `newsbot` ユーザーを探す
   - 存在しない場合: 新規作成（権限: 投稿者 または 編集者）
3. `アプリケーションパスワード` セクションを確認
   - 現在の.envのパスワード `QjgR KWKW 1nBb aL5y DjrR 36SA` が有効か確認
   - 無効な場合: 新しいパスワードを生成し、`.env`の15行目を更新

**WordPress REST APIの動作確認**:
- ブラウザで https://aaover60.com/wp-json/wp/v2/posts を開く
- JSONデータが表示されればOK

---

### 3. OpenAI APIキーの確認

**.envファイル**: 5行目のAPIキーが有効か確認

**確認方法**:
1. https://platform.openai.com/account/api-keys にアクセス
2. APIキーが有効か確認
3. アカウントに残高があるか確認（https://platform.openai.com/usage）

**無効な場合**: 新しいAPIキーを生成し、`.env`を更新

---

## 🧪 初回テスト実行

### 4. ローカルでテスト実行

**コマンド**:
```powershell
cd C:\Users\wandt\AI_coding\workspace\projects\newsbot

# 仮想環境の作成（初回のみ）
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 依存関係のインストール（初回のみ）
pip install -r requirements.txt

# テスト実行
python main.py
```

**確認項目**:
- [ ] `newsbot.log` にエラーがないか
- [ ] `out/draft.md` に記事が生成されているか
- [ ] WordPress（https://aaover60.com/wp-admin/）に下書きが投稿されているか

**エラーが出た場合**: `TEST_RUN_GUIDE.md` のトラブルシューティングを参照

---

## 🔄 GitHub Actionsの設定（オプション：自動実行したい場合）

### 5. GitHubリポジトリの確認

**確認項目**:
- [ ] newsbotプロジェクトがGitHubにプッシュされているか
- [ ] `.github/workflows/newsbot.yml` が存在するか

**プッシュ方法**:
```bash
cd C:\Users\wandt\AI_coding\workspace\projects\newsbot
git add .
git commit -m "Configure newsbot for aaover60.com"
git push origin main
```

---

### 6. GitHub Secretsの設定

**設定場所**: GitHubリポジトリの Settings → Secrets and variables → Actions

**設定すべきSecrets**:

| Secret名 | 値 | 重要度 |
|---------|---|-------|
| `LLM_PROVIDER` | `openai` | ⭐️⭐️⭐️ |
| `OPENAI_API_KEY` | （.envの5行目の値） | ⭐️⭐️⭐️ |
| `OPENAI_MODEL` | `gpt-5-mini` | ⭐️⭐️⭐️ |
| `WORDPRESS_URL` | `https://aaover60.com` | ⭐️⭐️⭐️ |
| `WORDPRESS_USERNAME` | `newsbot` | ⭐️⭐️⭐️ |
| `WORDPRESS_APP_PASSWORD` | （.envの15行目・スペース含む） | ⭐️⭐️⭐️ |
| `RSS_FEEDS` | （.envの18行目・変更後の値） | ⭐️⭐️⭐️ |
| `CACHE_DURATION_HOURS` | `24` | ⭐️⭐️ |
| `MAX_ARTICLES_PER_RUN` | `5` | ⭐️⭐️ |
| `MAX_TOKENS_PER_RUN` | `10000` | ⭐️⭐️ |
| `ALLOWLIST_PATH` | `config/allowlist.txt` | ⭐️ |
| `PROMPT_VARIANT` | `default` | ⭐️ |
| `JSON_LOGS` | `false` | ⭐️ |
| `DRAFT_PATH` | `out/draft.md` | ⭐️ |

**重要**: `WORDPRESS_APP_PASSWORD` はスペース付きでそのままコピーしてください。

---

### 7. GitHub Actionsの手動実行テスト

**手順**:
1. GitHubリポジトリの `Actions` タブを開く
2. `newsbot` ワークフローを選択
3. `Run workflow` ボタンをクリック
4. 実行結果を確認（緑のチェックマーク = 成功）

**確認項目**:
- [ ] ワークフローが正常に完了したか
- [ ] WordPress（aaover60.com）に下書きが投稿されたか

---

## 📊 運用開始後の日次作業

### 8. 毎日の確認作業

**確認項目** (所要時間: 5〜10分):
- [ ] GitHub Actionsが正常に実行されたか
- [ ] WordPressに新しい下書きが投稿されたか
- [ ] 記事の内容が適切か（編集が必要な場合は編集）
- [ ] 必要に応じて記事を公開

**WordPress下書きの確認**:
1. https://aaover60.com/wp-admin/ にログイン
2. `投稿` → `投稿一覧` → `下書き` を選択
3. 最新の記事を確認
4. 内容が良ければ `公開` ボタンをクリック

---

## ❓ わからないことがあれば

### サポート用の情報収集

問題が発生した場合、以下の情報を確認してください：

1. **ログファイル**: `workspace/projects/newsbot/newsbot.log`
2. **生成記事**: `workspace/projects/newsbot/out/draft.md`
3. **エラーメッセージ**: コンソールに表示されたエラー

### 参考ドキュメント

- **RSS_FEED_GUIDE.md**: RSSフィードの選び方と設定方法
- **TEST_RUN_GUIDE.md**: 詳細なテスト実行手順とトラブルシューティング
- **README.md**: プロジェクト全体の説明
- **aaover60_setup_checklist.txt**: Codex CLIが作成した元のチェックリスト

---

## 🎉 完了チェックリスト

以下のすべてにチェックが入れば、セットアップ完了です！

- [ ] 1. .envのRSS_FEEDSを設定した
- [ ] 2. WordPressのnewsbotユーザーとアプリケーションパスワードを確認した
- [ ] 3. OpenAI APIキーが有効であることを確認した
- [ ] 4. ローカルでテスト実行して成功した
- [ ] 5. GitHubリポジトリにプッシュした（自動実行する場合）
- [ ] 6. GitHub Secretsを設定した（自動実行する場合）
- [ ] 7. GitHub Actionsで手動実行テストして成功した（自動実行する場合）

---

**次のステップ**: 上記の作業を順番に実行してください。問題が発生したら `TEST_RUN_GUIDE.md` のトラブルシューティングを参照してください。
