# 筑波飯Bot

## 入力
- おおよその現在地
- おおよその予算
- 移動手段

## 出力
- おすすめの店（Google Place APIによる）をカルーセル表示


## 具体的処理

1. メニューボタンから地域を選択させる
1. 丁目を選択ボタン表示
    1.1 地域からGeocoding APIを使って、座標を取得
1. 予算選択ボタン表示
1. 交通手段選択ボタン表示
1. 得られた入力を引数にGoogle Place APIのnearbysearchを使って検索
1. 結果を5件ずつカルーセルで表示


## 環境
Anaconda python3

`pip install line-bot-sdk`

あと適宜足りなかったら pip でインストール


## 実行方法
`python app.py`


## Bluemix へのPush

1. [cloudfoundry cli](https://github.com/cloudfoundry/cli#downloads "cloudfoundry/cli: The official command line client for Cloud Foundry")をインストール
1. bluemix アカウントを作成
1. [IBMが公開しているリポジトリ](https://github.com/IBM-Bluemix/get-started-python#3-prepare-the-app-for-deployment "IBM-Bluemix/get-started-python: A Python application and tutorial that use Flask framework to provide a REST API to receive requests from the UI. The API then persists the data to a Cloudant database.")のREADME.mdの3.以降を参照。

- Cloudfoundry CLI にバグがあるかもわからない。
    - 筆者環境ではインタラクティブにログインできなかった。その場合は以下参照。
    - http://cli.cloudfoundry.org/ja-JP/cf/login.html

## その他必要なこと。

- LINE Messaging APIを使うための諸準備。ググるべし。
- Google Place API, Google Map Geocoding APIを使うための準備。
    - Google Developer Consoleからプロジェクト作ったり、API有効化したり。

## 理解するのに必要であろう知識やスキル
- PCの基礎
- Python (+ Flask)
- エディタをそれなりに使える
- Webアプリケーションの基礎知識
    - post, get, port, html, css
        - 少しでいい。
- API, JSONの概念と、それを利用するスキル
- Git, Github, Continuos Integration の概念
- Bluemix, PaaSの概念。マニュアル読みながら使う。
- NoSQLの概念