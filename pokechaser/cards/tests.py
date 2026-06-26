from django.test import TestCase
from rest_framework.test import APIClient

from pokechaser.cards.models import Card, CardSet
from pokechaser.core.models import User


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
