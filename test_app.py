import unittest
import app
import json
import pprint


class TestLineBot(unittest.TestCase):

    def test_get_places_by_nearby_search(self):

        budget = 2
        transportation = "自転車"
        location_geometry = "36.1096719,140.1113418"

        output = app.get_places_by_nearby_search(budget, transportation, location_geometry)
        expected = []

        self.assertIsNot(output, expected)

    def test_get_index(self):

        with open('place.json', encoding='utf-8') as f:
            places = json.load(f)["results"]

        result_count = len(places)

        nth_result = 2 # data_dict['nth-result']

        start_index = int(nth_result) * 5
        end_index = 5 + int(nth_result) * 5

        if end_index > result_count:
            end_index = result_count
            start_index = end_index - (end_index % 5)

        pprint.pprint(places[start_index:end_index])

        self.assertEqual(start_index, 0)
        self.assertEqual(end_index, 3)