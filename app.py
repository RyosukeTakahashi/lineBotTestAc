# -*- coding: utf-8 -*-

#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

from __future__ import unicode_literals

import os
import sys
import pprint
import re
from argparse import ArgumentParser
from dotenv import load_dotenv
import requests
import urllib.parse as urlparse
from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookParser
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    PostbackEvent, JoinEvent, FollowEvent, TemplateSendMessage, CarouselTemplate, CarouselColumn,
    ButtonsTemplate, PostbackTemplateAction, MessageTemplateAction, URITemplateAction

)

# from apiclient.discovery import build

# get CHANNEL_SECRET and CHANNEL_ACCESS_TOKEN from your environment variable
ENV = load_dotenv('.env')
CHANNEL_SECRET = os.environ.get('CHANNEL_SECRET')
CHANNEL_ACCESS_TOKEN = os.environ.get('CHANNEL_ACCESS_TOKEN')
PLACES_APIKEY = os.environ.get('PLACES_APIKEY')

if CHANNEL_SECRET is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if CHANNEL_ACCESS_TOKEN is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(CHANNEL_SECRET)

CHATBOT_ENDPOINT = 'https://chatbot-api.userlocal.jp/api/chat'
SIMPLE_WIKIPEDIA_API = 'http://wikipedia.simpleapi.net/api'
PLACES_API_ENDPOINT = 'https://maps.googleapis.com/maps/api/place/textsearch/json'

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

        print("")
        pprint.pprint(event)
        print("")

        # add event bool if needed

        if isinstance(event, MessageEvent):

            if isinstance(event.message, TextMessage):

                if event.message.text == "hello":
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text="Hi")
                    )
                if event.message.text == "go":
                    line_bot_api.reply_message(
                        event.reply_token,
                        get_budget_buttons_template_message()
                    )
                if event.message.text == "restaurant":
                    places = get_places_by_textsearch('1', 'onfoot')["results"]
                    pprint.pprint(places[:6])
                    messages = [TextSendMessage(text=place['name']) for place in places[:4]]

                    line_bot_api.reply_message(
                        event.reply_token,
                        messages
                    )

        if isinstance(event, PostbackEvent):

            postback_data = event.postback.data

            if "choose_budget" in postback_data:

                budget = event.postback.data[-1] #  last letter is budget level
                line_bot_api.reply_message(
                    event.reply_token,
                    [TextSendMessage(text="budget level is {}.".format(budget)),
                     TextSendMessage(text="移動手段は?"),
                     get_transportation_buttons_template_message(budget)]
                )

            if "choose_transportation" in postback_data:

                postback_data = event.postback.data
                options = dict(urlparse.parse_qsl(postback_data))
                places = get_places_by_textsearch(options['budget'], options['transportation'])["results"]
                pprint.pprint(places[6])
                # リスト内包表記をしたあとだと、異なるクラスのインスタンスは、アペンドできない？

                line_bot_api.reply_message(
                    event.reply_token,
                    get_spot_carousel(places[:5])
                )




    return 'OK'


def get_budget_buttons_template_message():

    buttons_template_message = TemplateSendMessage(
        alt_text='予算を決めるボタンが表示されています',
        template=ButtonsTemplate(
            thumbnail_image_url='https://example.com/image.jpg',
            title='予算はどの程度ですか？',
            text='お選びください',
            actions=[
                PostbackTemplateAction(
                    label='安いbudget level 1',
                    # text='postback text', # it would send a text after postback
                    data='action=choose_budget&budget=1'
                ),
                PostbackTemplateAction(
                    label='普通budget level 2',
                    data='action=choose_budget&budget=2'
                ),
                PostbackTemplateAction(
                    label='高めbudget level 3',
                    data='action=choose_budget&budget=3'
                ),
                # MessageTemplateAction(
                #     label='message',
                #     text='message text'
                # ),
                # URITemplateAction(
                #     label='uri',
                #     uri='http://example.com/'
                # )
            ]
        )
    )

    return buttons_template_message


def get_transportation_buttons_template_message(budget):

    buttons_template_message = TemplateSendMessage(
        alt_text='移動手段を決めるボタンが表示されています',
        template=ButtonsTemplate(
            thumbnail_image_url='https://example.com/image.jpg',
            title='移動手段は？',
            text='お選びください',
            actions=[
                PostbackTemplateAction(
                    label='徒歩',
                    text='budget{}、で徒歩で移動ですね。'.format(budget),  # it would send a text after postback
                    data='action=choose_transportation&transportation=onfoot&budget=' + budget
                ),
                PostbackTemplateAction(
                    label='自転車',
                    text='budget{}、で自転車で移動ですね。'.format(budget),
                    data='action=choose_transportation&transportation=bicycle&budget=' + budget
                ),
                PostbackTemplateAction(
                    label='車',
                    text='budget{}、で車で移動ですね。'.format(budget),
                    data='action=choose_transportation&transportation=car&budget=' + budget
                ),
            ]
        )
    )

    return buttons_template_message


def get_places_by_textsearch(budget, transportation):
    s = requests.Session()

    radius = ''
    if transportation is 'onfoot':
        radius = '700'
    elif transportation is 'bicycle':
        radius = '2000'
    elif transportation is 'car':
        radius = '8000'
    print(radius)

    params = {
        'key': PLACES_APIKEY,
        'location': "36.110277, 140.100987",
        'radius': radius,
        'maxprice': budget,
        'minprice': '1',
        # aquarium cafe art_gallery bar bowling_alley museum movie_theater meal_delivery meal_takeaway
        # zoo spa restaurant
        'type': 'restaurant',
        'opennow': 'true',
        'rankby': 'prominence',
        'language': 'ja'
    }

    r = s.get(PLACES_API_ENDPOINT, params=params)
    json_result = r.json()

    return json_result


def get_spot_carousel(places5):

    columns = [get_carousel_column_template(place) for place in places5]
    # template.py のCarouselTemplate(Base)をCarouselTemplate(Template)に変えないと
    # おそらくできない。Requestがおかしいとエラー表示される. 要検証。少なくともTemplateに変えてもできる。
    carousel_template_message = TemplateSendMessage(
        alt_text='Carousel template',
        template=CarouselTemplate(
            columns=columns
        )
    )

    return carousel_template_message


def get_carousel_column_template(place):

    area = re.sub('日本、[\s\S]?〒\d{3}-\d{4}[\s\S]?茨城県つくば市', '', place['formatted_address'])
    carousel_column = CarouselColumn(
                    thumbnail_image_url=place['icon'],
                    title=place['name'],
                    text='area:{}\nreview:{}\nbudget:{}'.format(area, str(place['rating']), str(place['price_level'])),
                    actions=[
                        PostbackTemplateAction(
                            label="地図を見る",
                            data='action=map&id={}'.format(place['id'])
                        ),
                        PostbackTemplateAction(
                            label="電話をする",
                            data='action=phone&id={}'.format(place['id'])
                        ),
                        PostbackTemplateAction(
                            label="レビューを見る",
                            data='action=review&id={}'.format(place['id'])
                        ),
                    ]
    )

    return carousel_column



if __name__ == "__main__":
    arg_parser = ArgumentParser(
        usage='Usage: python ' + __file__ + ' [--port <port>] [--help]'
    )
    arg_parser.add_argument('-p', '--port', default=8000, help='port')
    arg_parser.add_argument('-d', '--debug', default=False, help='debug')
    options = arg_parser.parse_args()

    app.run(debug=options.debug, port=options.port)
