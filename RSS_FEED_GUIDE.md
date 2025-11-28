# aaover60.com向け RSSフィード設定ガイド

このガイドは、aaover60.comのシニア向けニュース自動投稿のための推奨RSSフィードリストです。

## 📋 推奨RSSフィードリスト

### 1️⃣ 健康・ライフスタイル系

#### NHK（信頼性が高く、シニア向け）
- **NHK 主要ニュース**: `https://www.nhk.or.jp/rss/news/cat0.xml`
- **NHK 社会ニュース**: `https://www.nhk.or.jp/rss/news/cat1.xml`
- **NHK 科学・文化**: `https://www.nhk.or.jp/rss/news/cat6.xml`

#### 厚生労働省（医療・健康の公式情報）
- **厚生労働省新着情報**: `https://www.mhlw.go.jp/stf/news.rdf`

#### Yahoo!ニュース（トピックスが豊富）
- **Yahoo! 国内ニュース**: `https://news.yahoo.co.jp/rss/topics/domestic.xml`
- **Yahoo! 科学ニュース**: `https://news.yahoo.co.jp/rss/topics/science.xml`

### 2️⃣ シニア向けテクノロジー・IT系

#### ITmedia（わかりやすい技術解説）
- **ITmedia NEWS**: `https://rss.itmedia.co.jp/rss/2.0/news_bursts.xml`
- **ITmedia PC USER**: `https://rss.itmedia.co.jp/rss/2.0/pcuser.xml`

#### その他
- **CNET Japan**: `https://japan.cnet.com/rss/news/`
- **Impress Watch シニアガイド**: `https://www.watch.impress.co.jp/data/rss/1.0/ip/index.rdf`

### 3️⃣ Canva・デザイン系（日本語コンテンツ）

**注意**: Canva公式の日本語RSSは見つかりませんでした。代替として以下を推奨：

- **デザイン関連ブログ**: 個別に日本語デザインブログのRSSを探す必要があります
- **Web担当者Forum デザイン**: `https://webtan.impress.co.jp/rss`

## 🎯 テーマ別の推奨設定例

### パターンA: 健康・ライフスタイル重視
```env
RSS_FEEDS=https://www.nhk.or.jp/rss/news/cat0.xml,https://www.nhk.or.jp/rss/news/cat1.xml,https://www.mhlw.go.jp/stf/news.rdf,https://news.yahoo.co.jp/rss/topics/domestic.xml
```

### パターンB: テクノロジー重視
```env
RSS_FEEDS=https://rss.itmedia.co.jp/rss/2.0/news_bursts.xml,https://rss.itmedia.co.jp/rss/2.0/pcuser.xml,https://japan.cnet.com/rss/news/,https://www.nhk.or.jp/rss/news/cat6.xml
```

### パターンC: バランス型（推奨）
```env
RSS_FEEDS=https://www.nhk.or.jp/rss/news/cat0.xml,https://www.nhk.or.jp/rss/news/cat6.xml,https://rss.itmedia.co.jp/rss/2.0/news_bursts.xml,https://news.yahoo.co.jp/rss/topics/science.xml
```

## ⚙️ 設定手順

### ステップ1: .envファイルを編集

`workspace/projects/newsbot/.env`ファイルの`RSS_FEEDS`行を上記のいずれかに書き換えます。

例:
```env
RSS_FEEDS=https://www.nhk.or.jp/rss/news/cat0.xml,https://www.nhk.or.jp/rss/news/cat6.xml,https://rss.itmedia.co.jp/rss/2.0/news_bursts.xml
```

### ステップ2: allowlist.txtにドメインを追加

`workspace/projects/newsbot/config/allowlist.txt`に以下のドメインを追加します：

```
nhk.or.jp
www3.nhk.or.jp
mhlw.go.jp
news.yahoo.co.jp
itmedia.co.jp
japan.cnet.com
watch.impress.co.jp
webtan.impress.co.jp
```

### ステップ3: テスト実行

```bash
cd workspace/projects/newsbot
python main.py
```

実行後、`out/draft.md`に記事が生成され、WordPress（aaover60.com）に下書きが投稿されます。

## 🔍 フィードの確認方法

RSSフィードが有効か確認する方法：

1. **ブラウザで開く**: フィードURLをブラウザに貼り付けてXMLが表示されるか確認
2. **RSSリーダーで確認**: FeedlyなどのRSSリーダーで購読できるか確認

## 📌 注意事項

### 著作権について
- RSSフィードは個人利用のみ許可されている場合が多いです
- 生成記事には必ず元記事へのリンクが含まれます（newsbot自動対応）

### フィードの更新頻度
- NHK: 随時更新（1日数十件）
- ITmedia: 随時更新（1日10〜20件）
- Yahoo!ニュース: 随時更新

### キャッシュについて
- newsbotは24時間以内の同じ記事を再処理しません
- `cache.json`を削除すると再処理可能になります

## 🔄 運用時の調整

### フィードを追加する場合
1. 新しいフィードURLを`.env`のRSS_FEEDSに追加（カンマ区切り）
2. フィードのドメインを`config/allowlist.txt`に追加
3. テスト実行して動作確認

### フィードを減らす場合
記事が多すぎる場合は、`.env`で以下を設定：
```env
MAX_ARTICLES_PER_RUN=5
```

## 参考リンク

- [NHK RSS情報](https://wpguide.info/rssfeeds/rss-nhk)
- [Yahoo!ニュース RSS一覧](https://news.yahoo.co.jp/rss)
- [ITmedia RSS一覧](https://corp.itmedia.co.jp/media/rss_list/)
