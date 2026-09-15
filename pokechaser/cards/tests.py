from unittest.mock import MagicMock, patch

import requests
from django.test import TestCase
from rest_framework.test import APIClient

from pokechaser.cards.models import Card, CardSet
from pokechaser.cards.utils import CardApi
from pokechaser.core.models import User


def mock_response(status_code, json_data=None):
    response = MagicMock()
    response.status_code = status_code
    if json_data is not None:
        response.json.return_value = json_data
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(response=response)
    return response


def api_set(set_id, name="Test Set"):
    return {
        "id": set_id,
        "name": name,
        "series": "Test Series",
        "printedTotal": 1,
        "total": 1,
    }


def api_card(card_id, set_id, name="Test Card"):
    return {
        "id": card_id,
        "name": name,
        "supertype": "Pokémon",
        "number": "1",
        "set": {"id": set_id},
    }


def make_card_set(set_id="test-set"):
    return CardSet.objects.create(
        id=set_id,
        name="Test Set",
        series="Test Series",
        printed_total=100,
        total=100,
    )


def make_card(card_id, name, card_set, number="1", price=None):
    tcgplayer = None
    if price is not None:
        tcgplayer = {"prices": {"normal": {"market": price}}}
    return Card.objects.create(
        id=card_id,
        name=name,
        set=card_set,
        supertype="Pokémon",
        number=number,
        tcgplayer=tcgplayer,
    )


class CardSortTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.card_set = make_card_set()
        make_card("c1", "Charizard", self.card_set, number="1", price=100.0)
        make_card("c2", "Pikachu", self.card_set, number="2", price=10.0)
        make_card("c3", "Bulbasaur", self.card_set, number="3", price=50.0)
        make_card("c4", "Mewtwo", self.card_set, number="4")  # no price

    def test_sort_name_asc(self):
        resp = self.client.get("/cards/card/?sort=name_asc")
        names = [r["name"] for r in resp.data["results"]]
        self.assertEqual(names, sorted(names))

    def test_sort_name_desc(self):
        resp = self.client.get("/cards/card/?sort=name_desc")
        names = [r["name"] for r in resp.data["results"]]
        self.assertEqual(names, sorted(names, reverse=True))

    def test_sort_price_desc(self):
        resp = self.client.get("/cards/card/?sort=price_desc")
        results = resp.data["results"]
        names = [r["name"] for r in results]
        # Charizard ($100) first, then Bulbasaur ($50), then Pikachu ($10), Mewtwo (null) last
        self.assertEqual(names[0], "Charizard")
        self.assertEqual(names[1], "Bulbasaur")
        self.assertEqual(names[2], "Pikachu")
        self.assertEqual(names[-1], "Mewtwo")

    def test_sort_price_asc(self):
        resp = self.client.get("/cards/card/?sort=price_asc")
        results = resp.data["results"]
        names = [r["name"] for r in results]
        # Pikachu ($10) first, then Bulbasaur ($50), then Charizard ($100), Mewtwo (null) last
        self.assertEqual(names[0], "Pikachu")
        self.assertEqual(names[1], "Bulbasaur")
        self.assertEqual(names[2], "Charizard")
        self.assertEqual(names[-1], "Mewtwo")

    def test_unknown_sort_falls_back_to_number_order(self):
        resp = self.client.get("/cards/card/?sort=invalid_sort")
        results = resp.data["results"]
        numbers = [r["number"] for r in results]
        self.assertEqual(numbers, ["1", "2", "3", "4"])


class CardSetSortTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        CardSet.objects.create(
            id="set-a", name="Alpha Set", series="A", printed_total=50, total=50,
            release_date="2023-01-01",
        )
        CardSet.objects.create(
            id="set-b", name="Beta Set", series="B", printed_total=50, total=50,
            release_date="2022-01-01",
        )
        CardSet.objects.create(
            id="set-c", name="Gamma Set", series="C", printed_total=50, total=50,
            release_date="2024-01-01",
        )

    def test_default_sort_release_date_desc(self):
        resp = self.client.get("/cards/cardSet/")
        names = [r["name"] for r in resp.data["results"]]
        # Gamma (2024) first, then Alpha (2023), then Beta (2022)
        self.assertEqual(names, ["Gamma Set", "Alpha Set", "Beta Set"])

    def test_sort_name_asc(self):
        resp = self.client.get("/cards/cardSet/?sort=name_asc")
        names = [r["name"] for r in resp.data["results"]]
        self.assertEqual(names, sorted(names))


class CardSuggestTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.card_set = make_card_set()
        make_card("c1", "Charizard", self.card_set, number="1")
        make_card("c2", "Charizard", self.card_set, number="2")   # duplicate name
        make_card("c3", "Charizard ex", self.card_set, number="3")
        make_card("c4", "Charmander", self.card_set, number="4")
        make_card("c5", "Pikachu", self.card_set, number="5")
        make_card("c6", "Bravery Charm", self.card_set, number="6")  # contains "char" mid-word

    def test_too_short_returns_empty(self):
        resp = self.client.get("/cards/card/suggest/?q=ch")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["results"], [])

    def test_spaces_do_not_count_toward_minimum(self):
        resp = self.client.get("/cards/card/suggest/?q=ch+")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["results"], [])

    def test_prefix_match_returns_results(self):
        resp = self.client.get("/cards/card/suggest/?q=Char")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Charizard", resp.data["results"])
        self.assertIn("Charizard ex", resp.data["results"])
        self.assertIn("Charmander", resp.data["results"])

    def test_istartswith_excludes_mid_word_matches(self):
        resp = self.client.get("/cards/card/suggest/?q=Char")
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("Bravery Charm", resp.data["results"])

    def test_deduplicates_names(self):
        resp = self.client.get("/cards/card/suggest/?q=Char")
        self.assertEqual(resp.status_code, 200)
        names = resp.data["results"]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(names.count("Charizard"), 1)

    def test_results_are_alphabetical(self):
        resp = self.client.get("/cards/card/suggest/?q=Char")
        self.assertEqual(resp.status_code, 200)
        names = resp.data["results"]
        self.assertEqual(names, sorted(names))

    def test_limit_param_is_respected(self):
        resp = self.client.get("/cards/card/suggest/?q=Char&limit=2")
        self.assertEqual(resp.status_code, 200)
        self.assertLessEqual(len(resp.data["results"]), 2)

    def test_limit_is_capped_at_15(self):
        # create 20 cards with names that all start with "Poke"
        for i in range(20):
            make_card(f"pk{i}", f"Pokemon{i:02d}", self.card_set, number=str(100 + i))
        resp = self.client.get("/cards/card/suggest/?q=Poke&limit=99")
        self.assertEqual(resp.status_code, 200)
        self.assertLessEqual(len(resp.data["results"]), 15)

    def test_case_insensitive(self):
        resp = self.client.get("/cards/card/suggest/?q=char")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Charizard", resp.data["results"])

    def test_no_match_returns_empty_list(self):
        resp = self.client.get("/cards/card/suggest/?q=Zzz")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["results"], [])


class SyncTestCase(TestCase):
    def setUp(self):
        self.api = CardApi()
        self.api.page_delay_seconds = 0
        self.api.set_delay_seconds = 0

    @patch("pokechaser.cards.utils.time.sleep")
    @patch("pokechaser.cards.utils.requests.get")
    def test_request_retries_on_404(self, mock_get, _mock_sleep):
        mock_get.side_effect = [
            mock_response(404),
            mock_response(404),
            mock_response(200, {"data": []}),
        ]

        result = self.api._request("https://api.pokemontcg.io/v2/cards", params={"page": 1})

        self.assertEqual(result, {"data": []})
        self.assertEqual(mock_get.call_count, 3)

    @patch.object(CardApi, "_request")
    def test_paginate_sends_order_by_id(self, mock_request):
        mock_request.return_value = {"data": [{"id": "x1"}], "totalCount": 1}

        self.api._paginate("cards", extra_params={"q": "set.id:sv8"})

        params = mock_request.call_args.kwargs["params"]
        self.assertEqual(params["orderBy"], "id")
        self.assertEqual(params["q"], "set.id:sv8")

    @patch.object(CardApi, "_request")
    def test_paginate_deduplicates_ids(self, mock_request):
        self.api.page_size = 2
        mock_request.side_effect = [
            {"data": [{"id": "c1"}, {"id": "c2"}], "totalCount": 3},
            {"data": [{"id": "c1"}, {"id": "c3"}], "totalCount": 3},
        ]

        results = self.api._paginate("cards", extra_params={"q": "set.id:sv8"})

        self.assertEqual([item["id"] for item in results], ["c1", "c2", "c3"])

    @patch.object(CardApi, "_fetch_sets")
    @patch.object(CardApi, "_fetch_cards_for_set")
    @patch("pokechaser.cards.utils.time.sleep")
    def test_run_saves_first_set_when_second_fails(self, _mock_sleep, mock_fetch_cards, mock_fetch_sets):
        self.api.set_max_retries = 1
        mock_fetch_sets.return_value = [api_set("set-a", "A"), api_set("set-b", "B")]

        def fetch_side_effect(set_id):
            if set_id == "set-a":
                return [api_card("c1", "set-a")]
            raise RuntimeError("API down")

        mock_fetch_cards.side_effect = fetch_side_effect

        with self.assertRaises(RuntimeError) as ctx:
            self.api.run()

        self.assertIn("set-b", str(ctx.exception))
        self.assertTrue(CardSet.objects.filter(id="set-a").exists())
        self.assertTrue(Card.objects.filter(id="c1").exists())
        self.assertFalse(Card.objects.filter(set_id="set-b").exists())

    @patch.object(CardApi, "_fetch_sets")
    @patch.object(CardApi, "_fetch_cards_for_set")
    def test_run_completes_when_all_sets_succeed(self, mock_fetch_cards, mock_fetch_sets):
        mock_fetch_sets.return_value = [api_set("set-a")]
        mock_fetch_cards.return_value = [api_card("c1", "set-a")]

        stats = self.api.run()

        self.assertEqual(stats["sets_created"], 1)
        self.assertEqual(stats["cards_created"], 1)
        mock_fetch_cards.assert_called_once_with("set-a")

