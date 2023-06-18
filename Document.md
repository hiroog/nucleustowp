# Nucleus から Wordpress への移行手順のメモ


  * item, media, category, comment のみ変換しました。
  * Nucleus の blog id は 1 固定なので注意してください。
  * 複数の書き込みユーザーに対応していません。


## 0. 準備

Python 3.x が必要です。必要なモジュールは requests だけです。

```
pip3 install requests
```



## 1. 旧 blog のデータの準備

phpMyAdmin で旧 Nucleus blog のデータベースをバックアップしてください
sql ファイルに UTF-8 で保存します。


## 2. 旧 blog のメディアファイルの準備

予め旧 Nucleus blog の media ファイルをすべてダウンロードして、特定のフォルダに入れておいてください。



## 3. settings.json の作成

settings.sample.json をコピーして settings.json を作成します。


## 4. 通常ユーザーアカウントの設定

通常の書き込みをアップロードするためのアカウントです。
Wordpress 上で APP PASSWORD を発行し、settings.json の default 欄に書き込みます。

  * settings.json の "default" の内容は以下の通り
    * url は新しい blog の URL です
    * user はユーザー名
    * pass は発行した APP PASSWD を入れます

注意: 新しいサーバーは必ず https (ssl) を有効にしておいてください。REST API を使った記事の投稿に失敗します。


## 5. Comment Import 専用の guest account を作成

Wordpress 上で guest 用のアカウントを追加します。

例

1. 新たに guest comment 用のユーザーを作ります。名前は任意です。
2. 権限グループを最初は「管理者」に設定しておいてください
    * 管理者権限がないと、アップロード時に書き込み制限でエラーになります。
    * アップロードが完了したら「購読者」に切り替えることができます。
3. APP PASSWORD も発行します
4. 作成したアカウント情報を settings.json の "defaultguest" 欄に書き込んでください
    * url は一般ユーザー "default" と同じものになります。
    * user は作成した guest用ユーザー名 です
    * pass は発行した APP PASSWD を入れます


## 6. config の設定

settings.json の config に nucleus 旧 blog のサーバーを設定してください。
この情報は記事内のパスの置き換えに使用します。

  * base\_host に古いサーバーのアドレスを入れます
  * local\_media\_path は 2. でダウンロードした画像フォルダを設定します。フルパスでも構いません。
  * media\_path, archive\_path は旧サーバーのパスになります。特に問題なければそのままで構いません。


例

```Json
{
    "default": {
        "url": "https://newhost.jp/blog",
        "user": "myname",
        "pass": "MY APP PASS"
    },
    "defaultguest": {
        "url": "https://newhost.jp/blog",
        "user": "guest_user",
        "pass": "GUEST APP PASS"
    },
    "config": {
        "blog_id" : 1,
    	"base_host": "oldhost.jp",
    	"media_path": "media/1",
    	"archive_path": "archive/1",
        "local_media_path": "downloads/mediafiles"
    }
}
```



## 7. sql ファイルのデコード

以下のコマンドを実行します。

```
python dbdecoder.py --sql DBBACKUPFILE.sql  --all
```

フォルダ item, category, comment が作られ、その中に切り出したファイルが json 形式で格納されます。


## 8. リンクの置き換え

以下のコマンドを実行します

```
python replacelink.py  --all
```

item の中にある画像と自分自身へのリンクを新しい URL に置き換えます。
item2 フォルダに格納します。

画像へのリンクは、作業している現在の日付のフォルダに格納されているとみなすので注意してください。
例えば 2023年 5月に作業している場合 wp-content/uploads/2023/05 になります。

また自分自身へのリンクは以下の形式に対応しています

   * ～/item/番号
   * ～/archive/1/年-月-日
   * ～/archive/1/年-月


## 9. カテゴリのアップロード

最初に記事のカテゴリを作ります。

```
python wdpost.py --upload_categories
python wdpost.py --save_category_map
```

## 10. 記事本体のアップロード

記事本体 (item) をアップロードします。
同時に参照している画像もアップロードします。

```
python wdpost.py --post_all --update
```

リンクの置き換えと記事本体のアップロードは、必ず同じ月のうちに行ってください。
もし作業日が異なり月が変わってしまった場合はもう一度 8. の replacelink.py -all コマンドを実行しておいてください。


## 11. コメントのアップロード

```
python wdpost.py --comment_all
```



## 12. guest アカウントの権限の変更

コメントのアップロードが完了したら、5. で作成した guest account の権限グループを「購読者」に変更してください。
また APP PASSWORD も削除できます。




## 13. rewrite Rule の設定

もし必要なら 新しい blog の .htaccess の先頭に以下の設定を追加します。
外部のサイトからリンクされている場合にある程度旧 blog との互換性を保つことができます。
この設定は必須ではありません。

RewriteBase の「/blog/」は必要に応じて書き換えてください。

```
<IfModule mod_rewrite.c>
RewriteEngine On
RewriteBase /blog/
RewriteCond %{QUERY_STRING} ^virtualpath=(.*)$
RewriteRule ^(.*)$  %1/? [QSD,R=301,L]
RewriteCond %{QUERY_STRING} ^itemid=(.*)$
RewriteRule ^(.*)$  n%1/? [QSD,R=301,L]
RewriteRule ^item/(\d+)  n$1 [R=301,L]
RewriteRule ^archive/1/(\d+)-(\d+)-(\d+)  $1/$2/$3 [R=301,L]
RewriteRule ^archive/1/(\d+)-(\d+)  $1/$2 [R=301,L]
RewriteRule ^category/(\d+)  category/cat$1 [R=301,L]
</IfModule>
```

旧 Nucleus blog と同じ以下のフォーマットでもアクセスできるようになります。

   * ～/item/番号
   * ～/archive/1/年-月-日
   * ～/archive/1/年-月
   * ～/category/番号
   * ～/?itemid=番号
   * ～/?virtualpath=～


## 注意点


投稿内容によっては予め WAF を無効化しておく必要があります。
blog 記事にプログラムコードが含まれている場合 WAF で弾かれて 403 error が返る場合があります。




