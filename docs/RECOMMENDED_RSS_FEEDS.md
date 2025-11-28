# おすすめRSSフィード一覧

シニア向けサイト（aaover60.com）に適したRSSフィードの一覧です。

## 現在使用中

- **NHK 主要ニュース**: https://www.nhk.or.jp/rss/news/cat0.xml
- **NHK 社会**: https://www.nhk.or.jp/rss/news/cat6.xml
- **ITmedia NEWS**: https://rss.itmedia.co.jp/rss/2.0/news_bursts.xml

## 追加候補

### NHKニュース（カテゴリ別）

- **暮らし・文化**: https://www.nhk.or.jp/rss/news/cat2.xml
- **政治**: https://www.nhk.or.jp/rss/news/cat4.xml
- **経済**: https://www.nhk.or.jp/rss/news/cat5.xml
- **国際**: https://www.nhk.or.jp/rss/news/cat3.xml
- **スポーツ**: https://www.nhk.or.jp/rss/news/cat7.xml
- **科学・医療**: https://www.nhk.or.jp/rss/news/cat1.xml

### 大手メディア

- **朝日新聞デジタル 主要ニュース**: https://www.asahi.com/rss/asahi/newsheadlines.rdf
- **毎日新聞 主要ニュース**: https://mainichi.jp/rss/etc/mainichi-flash.rss
- **読売新聞オンライン**: https://www.yomiuri.co.jp/rss/
- **日本経済新聞 主要ニュース**: https://www.nikkei.com/news/feed/

### IT・テクノロジー

- **CNET Japan**: https://japan.cnet.com/rss/index.rdf
- **Engadget 日本版**: https://japanese.engadget.com/rss.xml
- **ケータイ Watch**: https://k-tai.watch.impress.co.jp/data/rss/1.0/ktw/feed.rdf
- **PC Watch**: https://pc.watch.impress.co.jp/data/rss/1.0/pcw/feed.rdf

### 健康・医療

- **日経Gooday**: https://gooday.nikkei.co.jp/rss/
- **ヨミドクター（読売新聞）**: https://yomidr.yomiuri.co.jp/feed/
- **NHK健康チャンネル**: https://www.nhk.or.jp/kenko/feed/

### 経済・金融（シニア向け）

- **日経マネー**: https://style.nikkei.com/money/rss/
- **東洋経済オンライン**: https://toyokeizai.net/list/feed/rss

### 暮らし・ライフスタイル

- **NHKらいふ**: https://www.nhk.or.jp/lifestyle/rss/
- **All About（総合）**: https://allabout.co.jp/aa/rss/all.xml

## フィード追加の手順

1. `.env`ファイルの`RSS_FEEDS`に追加するフィードURLをカンマ区切りで追記
2. `config/allowlist.txt`に新しいドメインを追加（必要に応じて）
3. `main.py`を実行してテスト

例：
```
RSS_FEEDS=https://www.nhk.or.jp/rss/news/cat0.xml,https://www.nhk.or.jp/rss/news/cat6.xml,https://rss.itmedia.co.jp/rss/2.0/news_bursts.xml,https://www.nhk.or.jp/rss/news/cat2.xml,https://www.nhk.or.jp/rss/news/cat1.xml
```

## フィード選定のポイント

1. **信頼性**: 大手メディアのフィードを優先
2. **更新頻度**: 毎日更新されるフィードを選ぶ
3. **ジャンルのバランス**: 複数ジャンルを組み合わせる
4. **シニア関心度**: 健康、経済、暮らしなど関心の高いトピック
5. **許可リスト**: allowlist.txtにドメインを追加するのを忘れずに

## 注意事項

- フィード数を増やすほど処理時間とコストが増加します
- `MAX_ARTICLES_PER_RUN`と`MAX_TOKENS_PER_RUN`で制御可能
- 一部のフィードはフルテキストを提供していない場合があります
