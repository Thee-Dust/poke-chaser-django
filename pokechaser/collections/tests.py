from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from pokechaser.cards.models import Card, CardSet
from pokechaser.collections.models import Collection, CollectionItem, CollectionItemPurchase
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


class CollectionSignalTest(TestCase):
    def test_creating_user_creates_default_collection(self):
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        collection = Collection.objects.filter(user=user).first()
        self.assertIsNotNone(collection)
        self.assertTrue(collection.is_default)
        self.assertEqual(collection.name, "My Collection")

    def test_default_collection_is_only_one_created(self):
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.assertEqual(Collection.objects.filter(user=user).count(), 1)


class CollectionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.default_collection = Collection.objects.get(user=self.user, is_default=True)

    def test_delete_default_collection_returns_400(self):
        resp = self.client.delete(f"/collections/{self.default_collection.id}/")
        self.assertEqual(resp.status_code, 400)
        self.assertTrue(Collection.objects.filter(pk=self.default_collection.pk).exists())

    def test_delete_non_default_collection_returns_204(self):
        other = Collection.objects.create(user=self.user, name="Extra")
        resp = self.client.delete(f"/collections/{other.id}/")
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(Collection.objects.filter(pk=other.pk).exists())

    def test_cannot_see_another_users_collection(self):
        other_user = User.objects.create_user(
            username="other", email="other@example.com", password="testpass123"
        )
        other_collection = Collection.objects.get(user=other_user, is_default=True)
        resp = self.client.get(f"/collections/{other_collection.id}/")
        self.assertEqual(resp.status_code, 404)


class CollectionCalculationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.collection = Collection.objects.get(user=self.user, is_default=True)
        self.card_set = make_card_set()

    def test_card_count_sums_quantity(self):
        card1 = make_card("c1", "Pikachu", self.card_set, number="1")
        card2 = make_card("c2", "Charizard", self.card_set, number="2")
        CollectionItem.objects.create(collection=self.collection, card=card1, quantity=1)
        CollectionItem.objects.create(collection=self.collection, card=card2, quantity=3)

        resp = self.client.get(f"/collections/{self.collection.id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["card_count"], 4)

    def test_total_market_value_uses_quantity(self):
        card = make_card("c1", "Charizard", self.card_set, number="1", price=100.0)
        CollectionItem.objects.create(collection=self.collection, card=card, quantity=3)

        resp = self.client.get(f"/collections/{self.collection.id}/")
        self.assertEqual(Decimal(resp.data["total_market_value"]), Decimal("300.00"))

    def test_item_gain_loss_is_null_with_no_purchases(self):
        card = make_card("c1", "Pikachu", self.card_set, number="1", price=50.0)
        CollectionItem.objects.create(collection=self.collection, card=card, quantity=2)

        resp = self.client.get(f"/collections/{self.collection.id}/")
        item = resp.data["items"][0]
        self.assertIsNone(item["gain_loss"])

    def test_item_gain_loss_uses_purchase_count_not_quantity(self):
        card = make_card("c1", "Pikachu", self.card_set, number="1", price=100.0)
        item = CollectionItem.objects.create(collection=self.collection, card=card, quantity=3)
        CollectionItemPurchase.objects.create(item=item, purchase_price=Decimal("60.00"))

        resp = self.client.get(f"/collections/{self.collection.id}/")
        result = resp.data["items"][0]
        # market for gain_loss = 100 * 1 purchase = 100, spent = 60, gain = 40
        self.assertEqual(Decimal(result["gain_loss"]), Decimal("40.00"))
        # market_value should still use quantity=3
        self.assertEqual(Decimal(result["market_value"]), Decimal("300.00"))

    def test_purchased_market_value_excludes_items_without_purchases(self):
        card1 = make_card("c1", "Pikachu", self.card_set, number="1", price=100.0)
        card2 = make_card("c2", "Charizard", self.card_set, number="2", price=80.0)
        item1 = CollectionItem.objects.create(collection=self.collection, card=card1, quantity=1)
        CollectionItem.objects.create(collection=self.collection, card=card2, quantity=1)
        CollectionItemPurchase.objects.create(item=item1, purchase_price=Decimal("50.00"))

        resp = self.client.get(f"/collections/{self.collection.id}/")
        # purchased_market_value only counts card1 (has purchase), not card2
        self.assertEqual(Decimal(resp.data["purchased_market_value"]), Decimal("100.00"))
        # total_market_value counts both
        self.assertEqual(Decimal(resp.data["total_market_value"]), Decimal("180.00"))

    def test_collection_gain_loss_equals_purchased_market_minus_spent(self):
        card = make_card("c1", "Pikachu", self.card_set, number="1", price=100.0)
        item = CollectionItem.objects.create(collection=self.collection, card=card, quantity=1)
        CollectionItemPurchase.objects.create(item=item, purchase_price=Decimal("60.00"))

        resp = self.client.get(f"/collections/{self.collection.id}/")
        self.assertEqual(Decimal(resp.data["gain_loss"]), Decimal("40.00"))


class CollectionItemWriteTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.collection = Collection.objects.get(user=self.user, is_default=True)
        self.card_set = make_card_set()
        self.card = make_card("c1", "Pikachu", self.card_set, number="1", price=50.0)

    def test_post_item_without_card_id_returns_400(self):
        resp = self.client.post(
            f"/collections/{self.collection.id}/items/",
            {"quantity": 1},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("card_id", resp.data)

    def test_post_item_with_zero_quantity_returns_400(self):
        resp = self.client.post(
            f"/collections/{self.collection.id}/items/",
            {"card_id": self.card.id, "quantity": 0},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("quantity", resp.data)

    def test_post_item_with_invalid_quantity_returns_400(self):
        resp = self.client.post(
            f"/collections/{self.collection.id}/items/",
            {"card_id": self.card.id, "quantity": "abc"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("quantity", resp.data)

    def test_post_item_with_more_purchases_than_quantity_returns_400(self):
        resp = self.client.post(
            f"/collections/{self.collection.id}/items/",
            {
                "card_id": self.card.id,
                "quantity": 2,
                "purchases": [
                    {"purchase_price": "10.00"},
                    {"purchase_price": "20.00"},
                    {"purchase_price": "30.00"},
                ],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("purchases", resp.data)

    def test_post_item_creates_with_quantity_and_purchases(self):
        resp = self.client.post(
            f"/collections/{self.collection.id}/items/",
            {
                "card_id": self.card.id,
                "quantity": 2,
                "purchases": [
                    {"purchase_price": "10.00"},
                    {"purchase_price": "20.00"},
                ],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["quantity"], 2)
        self.assertEqual(len(resp.data["purchases"]), 2)

    def test_post_same_card_twice_increments_quantity(self):
        self.client.post(
            f"/collections/{self.collection.id}/items/",
            {"card_id": self.card.id, "quantity": 2},
            format="json",
        )
        resp = self.client.post(
            f"/collections/{self.collection.id}/items/",
            {"card_id": self.card.id, "quantity": 1},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["quantity"], 3)
        self.assertEqual(CollectionItem.objects.filter(collection=self.collection).count(), 1)

    def test_patch_item_quantity_below_purchase_count_returns_400(self):
        post_resp = self.client.post(
            f"/collections/{self.collection.id}/items/",
            {
                "card_id": self.card.id,
                "quantity": 2,
                "purchases": [{"purchase_price": "10.00"}, {"purchase_price": "20.00"}],
            },
            format="json",
        )
        item_id = post_resp.data["id"]
        resp = self.client.patch(
            f"/collections/{self.collection.id}/items/{item_id}/",
            {"quantity": 1},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("quantity", resp.data)

    def test_patch_item_quantity_up_returns_200(self):
        post_resp = self.client.post(
            f"/collections/{self.collection.id}/items/",
            {"card_id": self.card.id, "quantity": 1},
            format="json",
        )
        item_id = post_resp.data["id"]
        resp = self.client.patch(
            f"/collections/{self.collection.id}/items/{item_id}/",
            {"quantity": 5},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["quantity"], 5)


class CollectionItemPurchaseTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.collection = Collection.objects.get(user=self.user, is_default=True)
        self.card_set = make_card_set()
        self.card = make_card("c1", "Pikachu", self.card_set, number="1")
        post_resp = self.client.post(
            f"/collections/{self.collection.id}/items/",
            {"card_id": self.card.id, "quantity": 2},
            format="json",
        )
        self.item_id = post_resp.data["id"]

    def test_post_purchase_at_capacity_returns_400(self):
        # Fill to capacity (quantity=2)
        self.client.post(
            f"/collections/{self.collection.id}/items/{self.item_id}/purchases/",
            {},
            format="json",
        )
        self.client.post(
            f"/collections/{self.collection.id}/items/{self.item_id}/purchases/",
            {},
            format="json",
        )
        resp = self.client.post(
            f"/collections/{self.collection.id}/items/{self.item_id}/purchases/",
            {},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("purchases", resp.data)

    def test_deleting_last_purchase_deletes_item(self):
        purchase_resp = self.client.post(
            f"/collections/{self.collection.id}/items/{self.item_id}/purchases/",
            {},
            format="json",
        )
        purchase_id = purchase_resp.data["id"]
        self.client.delete(
            f"/collections/{self.collection.id}/items/{self.item_id}/purchases/{purchase_id}/"
        )
        self.assertFalse(CollectionItem.objects.filter(pk=self.item_id).exists())

    def test_deleting_one_of_multiple_purchases_keeps_item(self):
        p1_resp = self.client.post(
            f"/collections/{self.collection.id}/items/{self.item_id}/purchases/",
            {},
            format="json",
        )
        self.client.post(
            f"/collections/{self.collection.id}/items/{self.item_id}/purchases/",
            {},
            format="json",
        )
        purchase_id = p1_resp.data["id"]
        self.client.delete(
            f"/collections/{self.collection.id}/items/{self.item_id}/purchases/{purchase_id}/"
        )
        self.assertTrue(CollectionItem.objects.filter(pk=self.item_id).exists())
