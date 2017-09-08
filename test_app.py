import unittest
import app


class TestLineBot(unittest.TestCase):

    def test_get_places_by_nearby_search(self):

        budget = 2
        transportation = "自転車"
        location_geometry = "36.1096719,140.1113418"

        output = app.get_places_by_nearby_search(budget, transportation, location_geometry)

        expected = []

        self.assertIsNot(output, expected)

