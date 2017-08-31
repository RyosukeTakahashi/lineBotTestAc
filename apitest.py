import pprint
import os
from dotenv import load_dotenv
import requests

ENV = load_dotenv('.env')
api_key = os.environ.get('PLACES_APIKEY')
PLACES_APIKEY = os.environ.get('PLACES_APIKEY')

PLACES_API_ENDPOINT = 'https://maps.googleapis.com/maps/api/place/textsearch/json'

s = requests.Session()

params = {
    'query': '筑波大学 大学会館',
    'language': 'ja',
    'key': PLACES_APIKEY
    }

r = s.get(PLACES_API_ENDPOINT, params=params)
json_result = r.json()
pprint.pprint(json_result)