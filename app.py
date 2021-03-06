# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cloudant import Cloudant
import os
import sys
from dotenv import load_dotenv
import atexit
import pprint
import re
import json
import requests
import urllib.parse as urlparse
import cf_deployment_tracker
from flask import Flask, request, abort, render_template, jsonify
from linebot import (LineBotApi, WebhookParser)
from linebot.exceptions import (InvalidSignatureError)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, LocationMessage, ConfirmTemplate,
    PostbackEvent, JoinEvent, TemplateSendMessage, CarouselTemplate, CarouselColumn,
    ButtonsTemplate, PostbackTemplateAction, MessageTemplateAction, URITemplateAction
)
# https://ryo-murakami-apis.mybluemix.net/line/callback
cf_deployment_tracker.track()

# tested in
# ngrok http 8000

CHATBOT_ENDPOINT = 'https://chatbot-api.userlocal.jp/api/chat'
SIMPLE_WIKIPEDIA_API = 'http://wikipedia.simpleapi.net/api'
PLACES_TEXTSEARCH_ENDPOINT = 'https://maps.googleapis.com/maps/api/place/textsearch/json'
PLACES_NEARBYSEARCH_ENDPOINT = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json'
PLACES_DETAIL_ENDPOINT = 'https://maps.googleapis.com/maps/api/place/details/json'
PLACES_PHOTO_ENDPOINT = 'https://maps.googleapis.com/maps/api/place/photo'
GEOCODING_ENDPOINT = 'https://maps.googleapis.com/maps/api/geocode/json'

# get CHANNEL_SECRET and CHANNEL_ACCESS_TOKEN from your environment variable
if os.path.isfile('.env') or os.path.isfile('env'):
    print('found .env. So it should be a local environment.')
    ENV = load_dotenv('.env')
    if ENV is None:
        ENV = load_dotenv('env')
    CHANNEL_SECRET = os.environ.get('CHANNEL_SECRET')
    CHANNEL_ACCESS_TOKEN = os.environ.get('CHANNEL_ACCESS_TOKEN')
    PLACES_APIKEY = os.environ.get('PLACES_APIKEY')
    GEOCODING_APIKEY = os.environ.get('GEOCODING_APIKEY')
    PORT = int(os.environ.get("PORT"))

# envの記述方法を書いておくべきかな
else:
    print('Cannot find .env. So it should be on the cloud.')
    CHANNEL_SECRET = os.getenv('CHANNEL_SECRET')
    CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')
    PLACES_APIKEY = os.getenv('PLACES_APIKEY')
    GEOCODING_APIKEY = os.getenv('GEOCODING_APIKEY')
    PORT = int(os.getenv('PORT'))
    print(CHANNEL_SECRET)


db_name = 'mydb'
client = None
db = None

if 'VCAP_SERVICES' in os.environ:
    vcap = json.loads(os.getenv('VCAP_SERVICES'))
    print('Found VCAP_SERVICES')
    if 'cloudantNoSQLDB' in vcap:
        creds = vcap['cloudantNoSQLDB'][0]['credentials']
        user = creds['username']
        password = creds['password']
        url = 'https://' + creds['host']
        client = Cloudant(user, password, url=url, connect=True)
        db = client.create_database(db_name, throw_on_exists=False)
elif os.path.isfile('vcap-local.json'):
    with open('vcap-local.json') as f:
        vcap = json.load(f)
        print('Found local VCAP_SERVICES')
        creds = vcap['services']['cloudantNoSQLDB'][0]['credentials']
        user = creds['username']
        password = creds['password']
        url = 'https://' + creds['host']
        client = Cloudant(user, password, url=url, connect=True)
        db = client.create_database(db_name, throw_on_exists=False)


AREA_COUNT = {
  '天久保': 4,
  '桜': 3,
  '春日': 4,
  '吾妻': 4,
  '竹園': 4,
}


if CHANNEL_SECRET is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if CHANNEL_ACCESS_TOKEN is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(CHANNEL_SECRET)

app = Flask(__name__)

# 8080 on bluemix
print(PORT)


@app.route('/')
def home():
    return render_template('index.html')


# @app.route('/api/visitors', methods=['GET'])
# def get_visitor():
#     if client:
#         return jsonify(list(map(lambda doc: doc['name'], db)))
#     else:
#         print('No database')
#         return jsonify([])


@app.route('/api/visitors', methods=['POST'])
def put_visitor():
    user = request.json['name']
    if client:
        data = {'name': user}
        db.create_document(data)
        return 'Hello %s! I added you to the database.' % user
    else:
        print('No database')
        return 'Hello %s!' % user


@atexit.register
def shutdown():
    if client:
        client.disconnect()


@app.route("/line/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # parse webhook body
    events = []
    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        abort(400)

    for event in events:

        print("showing event")
        pprint.pprint(event)
        print("")

        if isinstance(event, MessageEvent):

            if isinstance(event.message, TextMessage):

                text = event.message.text

                if text in AREA_COUNT.keys():
                    line_bot_api.reply_message(
                        event.reply_token,
                        get_area_buttons_template_message(text)
                    )

                post_text_to_db(event)

            # if isinstance(event.message, LocationMessage):

                # latitude = event.message.latitude
                # longtitude = event.message.longitude

                # line_bot_api.reply_message(
                #     event.reply_token,
                #     get_budget_buttons_template_message()
                # )

        if isinstance(event, PostbackEvent):

            data_str = event.postback.data
            data_dict = dict(urlparse.parse_qsl(data_str))
            try:
                next = data_dict['next']
            except:
                next = ''

            if next == 'budget':

                line_bot_api.reply_message(
                    event.reply_token,
                    get_budget_buttons_template_message(data_dict)
                )

            elif next == 'transportation':

                line_bot_api.reply_message(
                    event.reply_token,
                    get_transportation_buttons_template_message(data_dict)
                )

            elif next == "show-result":

                places = get_places_by_nearby_search(
                    data_dict['budget'],
                    data_dict['transportation'],
                    get_geocode(data_dict['area'])
                )["results"]

                result_count = len(places)

                nth_result = data_dict['nth-result']

                start_index = int(nth_result) * 5
                end_index = 5 + int(nth_result) * 5

                second_message = get_additional_search_confirm_template(data_dict)

                if end_index >= result_count:
                    end_index = result_count
                    second_message = TextSendMessage(
                        text='指定された条件でこれ以上の候補は見つかりませんでした。\n条件を変えて検索する場合は、下のボタンから現在地を入力してください。'
                    )
                    if end_index % 5 is not 0:
                        start_index = end_index - (end_index % 5)

                line_bot_api.reply_message(
                    event.reply_token,
                    [get_spot_carousels(places[start_index:end_index]),
                     second_message]
                )

            if "detail" in data_str:
                place_id = dict(urlparse.parse_qsl(data_str))['id']
                place_detail = get_place_detail(place_id)['result']

                messages = []
                if 'phone' in data_str:
                    messages = [TextSendMessage(text=place_detail['formatted_phone_number'])]

                line_bot_api.reply_message(
                    event.reply_token,
                    messages
                )
            post_postback_to_db(event)

    return 'OK'


#######################################

# Below are templates functions

def get_area_buttons_template_message(area):

    chou_count = AREA_COUNT[area]

    actions = [get_area_postback_template_action(area, i) for i in range(1, chou_count+1)]

    buttons_template_message = TemplateSendMessage(
        alt_text='{}の何丁目にいますか？'.format(area),
        template=ButtonsTemplate(
            title='{}の何丁目にいますか？'.format(area),
            text='お選びください',
            actions=actions
        )
    )

    return buttons_template_message


def get_area_postback_template_action(area, i):

    data_dict = {
        'area': area + str(i),
        'next': 'budget'
    }

    return PostbackTemplateAction(
                    label='{}丁目'.format(str(i)),
                    text='今は{}の{}丁目'.format(area, str(i)),
                    data=urlparse.urlencode(data_dict)
            )


def get_budget_buttons_template_message(data_dict):

    actions = [get_budget_postback_template_action(data_dict, i, budget_range)
               for i, budget_range in enumerate(['多分、~1200未満', '2000円近く覚悟', '3000円かそれ以上'])]

    buttons_template_message = TemplateSendMessage(
        alt_text='予算を決めるボタンが表示されています',
        template=ButtonsTemplate(
            title='予算はどの程度ですか？',
            text='お選びください',
            actions=actions
        )
    )

    return buttons_template_message


def get_budget_postback_template_action(data_dict, i, budget_range):

    data_dict['budget'] = i + 1
    data_dict['next'] = 'transportation'
    data = urlparse.urlencode(data_dict)

    return PostbackTemplateAction(
               label=budget_range,
               text="{}なところですね。".format(budget_range),
               data=data
           )


def get_transportation_buttons_template_message(data_dict):

    actions = [get_transportation_postback_template_action(data_dict, transportation)
               for transportation in ['徒歩', '自転車', '車']]

    buttons_template_message = TemplateSendMessage(
        alt_text='移動手段を決めるボタンが表示されています',
        template=ButtonsTemplate(
            title='移動手段は？',
            text='お選びください',
            actions=actions
        )
    )

    return buttons_template_message


def get_transportation_postback_template_action(data_dict, transportation):

    data_dict['next'] = 'show-result'
    data_dict['transportation'] = transportation
    data_dict['nth-result'] = 0
    data = urlparse.urlencode(data_dict)

    return PostbackTemplateAction(
               label=transportation,
               text='{}で行ける範囲で。\n指定された条件で、今現在営業中の店をお探しします。\n検索にちょっとだけ時間を頂きます。'.format(transportation),
               data=data
           )


def get_spot_carousels(places5):

    columns = [get_carousel_column_template(place) for place in places5]
    # template.py のCarouselTemplate(Base)をCarouselTemplate(Template)に変えたほうがいいような
    carousel_template_message = TemplateSendMessage(
        alt_text='候補地が表示されています。',
        template=CarouselTemplate(columns=columns)
    )

    return carousel_template_message


def get_carousel_column_template(place):

    # area = re.sub('日本、[\s\S]?(〒\d{3}-\d{4}[\s\S]?)?茨城県つくば市', '', place['formatted_address'])
    area = re.sub('つくば市', '', place['vicinity'])

    gmap_url = get_place_detail(place['place_id'])['result']['url']

    try:
        photo_url = get_place_photo_url(place['photos'][0]['photo_reference'])
    except:
        photo_url = 'https://developers.google.com/maps/documentation/static-maps/images/quota.png'

    # 住所が長すぎると予算を表示するスペースが無くなる問題の対処。
    line_change = '\n'
    if len(area) > 17:
        line_change = ''

    price = ''
    address_template = ''
    if 'price_level' in place.keys():
        if place['price_level'] is 1:
            price = '~1200円'
        if place['price_level'] is 2:
            price = '1200円~'
        if place['price_level'] is 3:
            price = '3000円~'
        address_template = '住所: {}\nレビュー: {} {}予算: {}'

    else:
        price = 0
        address_template = '住所: {}\nレビュー: {}'



    if 'rating' not in place.keys():
        rating = 'なし'
    else:
        rating = str(place['rating'])


    address = address_template.format(
        area, rating,
        line_change, price
    )

    carousel_column = CarouselColumn(
                    thumbnail_image_url=photo_url,
                    title=place['name'],
                    text=address,
                    actions=[
                        URITemplateAction(
                            label='地図とレビューを見る',
                            uri=gmap_url
                        ),
                        PostbackTemplateAction(
                            label='電話番号を表示する',
                            data='action=detail_phone&id={}'.format(place['place_id'])
                        )
                    ]
    )

    return carousel_column


def get_additional_search_confirm_template(data_dict):

    data_dict['nth-result'] = int(data_dict['nth-result']) + 1

    confirm_template_message = TemplateSendMessage(
        alt_text='追加の5件を表示しますか？',
        template=ConfirmTemplate(
            text='追加の5件を表示しますか？',
            actions=[
                PostbackTemplateAction(
                    label='表示する',
                    text='表示する',
                    data=urlparse.urlencode(data_dict)
                ),
                MessageTemplateAction(
                    label='終了する',
                    text='終了する'
                )
            ]
        )
    )

    return confirm_template_message


# get template function end

###############################################

# Below are api using function


def get_geocode(address):

    params = {
        'address': 'つくば市 ' + address,
        'key': GEOCODING_APIKEY
    }
    s = requests.Session()
    r = s.get(GEOCODING_ENDPOINT, params=params)
    json_res = r.json()
    location = json_res['results'][0]['geometry']['location']

    location_str = str(location['lat']) + ',' + str(location['lng'])

    return location_str


def get_places_by_nearby_search(budget, transportation, location_geometry):

    radius = ''
    print(transportation)
    if transportation == '徒歩':
        radius = '700'
    elif transportation == '自転車':
        radius = '2000'
    elif transportation == '車':
        radius = '8000'

    params = {
        'key': PLACES_APIKEY,
        'keyword': 'レストラン OR カフェ OR 定食 OR バー',
        'location': location_geometry,
        'radius': radius,
        # 'maxprice': budget,
        # 'minprice': str(int(budget)-1),
        'opennow': 'true',
        'rankby': 'prominence',
        'language': 'ja'
    }
    s = requests.Session()
    print(s.get(PLACES_NEARBYSEARCH_ENDPOINT, params=params).url)
    r = s.get(PLACES_NEARBYSEARCH_ENDPOINT, params=params)
    r.encoding = r.apparent_encoding
    json_result = r.json()
    # pprint.pprint(json_result)
    with open('place.json', mode='w', encoding='utf-8') as f:
        f.write(json.dumps(json_result, sort_keys=True, ensure_ascii=False, indent=2))
        print(json.dumps(json_result, sort_keys=True, ensure_ascii=False, indent=2))  # .encode('utf-8'))

    return json_result


def get_place_detail(place_id):

    params = {
        'key': PLACES_APIKEY,
        'placeid': place_id,
        'language': 'ja'
    }

    s = requests.Session()
    r = s.get(PLACES_DETAIL_ENDPOINT, params=params)
    json_result = r.json()

    return json_result


def get_place_photo_url(photo_ref):

    params = {
        'key': PLACES_APIKEY,
        'photoreference': photo_ref,
        'maxwidth': '400'
    }
    url = PLACES_PHOTO_ENDPOINT + '?' + urlparse.urlencode(params)

    return url


def post_text_to_db(event):

    data_to_send = {
        "text": event.message.text,
        "text_id": event.message.id,
        "user_id": event.source.user_id,
        "type": event.type,
        "timestamp": event.timestamp
    }

    if client:
        db.create_document(data_to_send)
        print('data added to db')
        return 'done'

    else:
        print('No database')


def post_postback_to_db(event):

    data_to_send = {
        "postback_data": event.postback.data,
        "user_id": event.source.user_id,
        "type": event.type,
        "timestamp": event.timestamp
    }

    if client:
        db.create_document(data_to_send)
        print('data added to db')
        return 'done'

    else:
        print('No database')


# api using function end.

#####################################


def get_postback_data_dict(data):
    return dict(urlparse.parse_qsl(data))


#####################################
if __name__ == "__main__":

    # arg_parser = ArgumentParser(
    #     usage='Usage: python ' + __file__ + ' [--port <port>] [--help]'
    # )
    # arg_parser.add_argument('-p', '--port', default=port, help='port')
    # arg_parser.add_argument('-d', '--debug', default=False, help='debug')
    # options = arg_parser.parse_args()

    app.run(debug=True, port=PORT, host='0.0.0.0')
