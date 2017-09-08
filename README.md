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
    1.1 1. 地域からGeocoding APIを使って、座標を取得
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