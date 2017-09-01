# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import sys
from dotenv import load_dotenv
import pprint
import re
import requests
import urllib.parse as urlparse
from argparse import ArgumentParser
from flask import Flask, request, abort
from linebot import (LineBotApi, WebhookParser)
from linebot.exceptions import (InvalidSignatureError)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, LocationMessage,
    PostbackEvent, JoinEvent, FollowEvent, TemplateSendMessage, CarouselTemplate, CarouselColumn,
    ButtonsTemplate, PostbackTemplateAction, MessageTemplateAction, URITemplateAction
)

CHATBOT_ENDPOINT = 'https://chatbot-api.userlocal.jp/api/chat'
SIMPLE_WIKIPEDIA_API = 'http://wikipedia.simpleapi.net/api'
PLACES_TEXTSEARCH_ENDPOINT = 'https://maps.googleapis.com/maps/api/place/textsearch/json'
PLACES_NEARBYSEARCH_ENDPOINT = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json'
PLACES_DETAIL_ENDPOINT = 'https://maps.googleapis.com/maps/api/place/details/json'
PLACES_PHOTO_ENDPOINT = 'https://maps.googleapis.com/maps/api/place/photo'
GEOCODING_ENDPOINT = 'https://maps.googleapis.com/maps/api/geocode/json'

# get CHANNEL_SECRET and CHANNEL_ACCESS_TOKEN from your environment variable
ENV = load_dotenv('.env')
CHANNEL_SECRET = os.environ.get('CHANNEL_SECRET')
CHANNEL_ACCESS_TOKEN = os.environ.get('CHANNEL_ACCESS_TOKEN')
PLACES_APIKEY = os.environ.get('PLACES_APIKEY')
GEOCODING_APIKEY = os.environ.get('GEOCODING_APIKEY')

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

@app.route("/callback", methods=['POST'])
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

            if isinstance(event.message, LocationMessage):

                latitude = event.message.latitude
                longtitude = event.message.longitude

                # line_bot_api.reply_message(
                #     event.reply_token,
                #     get_budget_buttons_template_message()
                # )

        if isinstance(event, PostbackEvent):

            data = event.postback.data
            postback_data_dict = get_postback_data_dict(data)
            try:
                next = postback_data_dict['next']
            except:
                next = ''

            if 'budget' in next:

                line_bot_api.reply_message(
                    event.reply_token,
                    get_budget_buttons_template_message(data)
                )

            elif "transportation" in next:

                line_bot_api.reply_message(
                    event.reply_token,
                    get_transportation_buttons_template_message(data)
                )

            elif "showresult" in next:

                location_geometry = get_geocode(postback_data_dict['area'])

                places = get_places_by_textsearch(
                    postback_data_dict['budget'],
                    postback_data_dict['transportation'],
                    location_geometry
                )["results"]

                line_bot_api.reply_message(
                    event.reply_token,
                    get_spot_carousels(places[:5])
                )

            if "detail" in data:

                place_id = dict(urlparse.parse_qsl(data))['id'] # id in postback_data. Not the result json.
                place_detail = get_place_detail(place_id)['result']

                if 'map' in data:
                    messages = [TextSendMessage(text=place_detail['url'])]
                if 'phone' in data:
                    messages = [TextSendMessage(text=place_detail['formatted_phone_number'])]

                line_bot_api.reply_message(
                    event.reply_token,
                    messages
                )

    return 'OK'


#######################################

# Below are templates functions

def get_area_buttons_template_message(area):

    chou_count = AREA_COUNT[area]

    actions = [PostbackTemplateAction(
                    label='{}丁目'.format(str(i)),
                    text='{}の{}丁目'.format(area, str(i)), # it would send a text after postback
                    data='area={}{}&next=budget'.format(area, str(i))
                ) for i in range(1, chou_count+1)]

    buttons_template_message = TemplateSendMessage(
        alt_text='{}の何丁目にいますか？'.format(area),
        template=ButtonsTemplate(
            title='{}の何丁目にいますか？'.format(area),
            text='お選びください',
            actions=actions
        )
    )

    return buttons_template_message


def get_budget_buttons_template_message(postback_data):

    postback_data_without_next = re.sub('&next=.*', '', postback_data)

    actions = [PostbackTemplateAction(
                    label=budget_range,
                    text="{}なところですね。".format(budget_range),
                    data=postback_data_without_next + '&budget=' + str(i+1) + '&next=transportation'
                )for i, budget_range in enumerate(['安め', '普通', '高め'])]

    buttons_template_message = TemplateSendMessage(
        alt_text='予算を決めるボタンが表示されています',
        template=ButtonsTemplate(
            title='予算はどの程度ですか？',
            text='お選びください',
            actions=actions
        )
    )

    return buttons_template_message


def get_transportation_buttons_template_message(postback_data):

    postback_data_without_next = re.sub('&next=.*', '', postback_data)

    actions = [PostbackTemplateAction(
                    label=transportation,
                    text='{}で移動します。'.format(transportation),
                    data=postback_data_without_next + '&transportation=' + transportation + '&next=showresult'
                )for transportation in ['徒歩', '自転車', '車']]

    buttons_template_message = TemplateSendMessage(
        alt_text='移動手段を決めるボタンが表示されています',
        template=ButtonsTemplate(
            title='移動手段は？',
            text='お選びください',
            actions=actions
        )
    )

    return buttons_template_message


def get_spot_carousels(places5):

    columns = [get_carousel_column_template(place) for place in places5]
    # todo template.py のCarouselTemplate(Base)をCarouselTemplate(Template)に変えたほうがいいような
    carousel_template_message = TemplateSendMessage(
        alt_text='候補地が表示されています。',
        template=CarouselTemplate(columns=columns)
    )

    return carousel_template_message


def get_carousel_column_template(place):

    area = re.sub('日本、[\s\S]?(〒\d{3}-\d{4}[\s\S]?)?茨城県つくば市', '', place['formatted_address'])

    gmap_url = get_place_detail(place['place_id'])['result']['url']

    try:
        photo_url = get_place_photo_url(place['photos'][0]['photo_reference'])
    except:
        photo_url = 'https://developers.google.com/maps/documentation/static-maps/images/quota.png'

    # 住所が長すぎると予算を表示するスペースが無くなる問題。
    line_change = '\n'
    if len(area) > 17:
        line_change = ''

    if place['price_level'] is 1:
        price = '~1200円'
    if place['price_level'] is 2:
        price = '1200円~'
    if place['price_level'] is 3:
        price = '3000円~'

    address = '住所: {}\nレビュー: {} {}予算: {}'.format(
        area, str(place['rating']),
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
                            label='電話をする',
                            data='action=detail_phone&id={}'.format(place['place_id'])
                        )
                    ]
    )

    return carousel_column

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
    json = r.json()
    pprint.pprint(json)
    location = json['results'][0]['geometry']['location']

    location_str = str(location['lat']) + ',' + str(location['lng'])

    return location_str


def get_places_by_textsearch(budget, transportation, location_geometry):

    radius = ''
    if transportation is 'onfoot':
        radius = '700'
    elif transportation is 'bicycle':
        radius = '2000'
    elif transportation is 'car':
        radius = '8000'

    params = {
        'key': PLACES_APIKEY,
        'location': location_geometry,
        'radius': radius,
        'maxprice': budget,
        'minprice': str(int(budget)-1),
        # aquarium cafe art_gallery bar bowling_alley museum movie_theater meal_delivery meal_takeaway
        # zoo spa restaurant
        'type': 'restaurant',
        'opennow': 'true',
        'rankby': 'prominence',
        'language': 'ja'
    }
    s = requests.Session()
    r = s.get(PLACES_TEXTSEARCH_ENDPOINT, params=params)
    json_result = r.json()

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

    # pprint.pprint(json_result)  # encode error

    return json_result


def get_place_photo_url(photo_ref):

    params = {
        'key': PLACES_APIKEY,
        'photoreference': photo_ref,
        'maxwidth': '400'
    }
    url = PLACES_PHOTO_ENDPOINT + '?' + urlparse.urlencode(params)

    return url

# api using function end.

#####################################


def get_postback_data_dict(data):
    return dict(urlparse.parse_qsl(data))


#####################################
if __name__ == "__main__":

    arg_parser = ArgumentParser(
        usage='Usage: python ' + __file__ + ' [--port <port>] [--help]'
    )
    arg_parser.add_argument('-p', '--port', default=8000, help='port')
    arg_parser.add_argument('-d', '--debug', default=False, help='debug')
    options = arg_parser.parse_args()

    app.run(debug=options.debug, port=options.port)
