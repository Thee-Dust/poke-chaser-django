from django.db import IntegrityError
from django.test import TestCase
from rest_framework.test import APIClient

from pokechaser.binders.models import Binder, BinderPage, BinderSlot
from pokechaser.cards.models import Card, CardSet
from pokechaser.core.models import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(username="testuser", email="test@example.com"):
    return User.objects.create_user(username=username, email=email, password="testpass123")


def make_card_set(set_id="test-set"):
    return CardSet.objects.create(
        id=set_id, name="Test Set", series="Test Series",
        printed_total=100, total=100,
    )


def make_card(card_id, card_set, number="1"):
    return Card.objects.create(
        id=card_id, name=f"Card {card_id}", set=card_set,
        supertype="Pokémon", number=number,
    )


def make_binder(user, name="My Binder", rows=3, cols=3):
    return Binder.objects.create(user=user, name=name, rows=rows, cols=cols)


def make_page(binder, order=0, name=""):
    return BinderPage.objects.create(binder=binder, name=name, order=order)


def fill_page(page, cards):
    """Place cards at positions 0..n-1 on page."""
    slots = [BinderSlot(page=page, card=card, position=i) for i, card in enumerate(cards)]
    BinderSlot.objects.bulk_create(slots)


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class BinderModelTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.card_set = make_card_set()
        self.binder = make_binder(self.user, rows=3, cols=3)
        self.page = make_page(self.binder)
        self.card = make_card("c1", self.card_set)

    def test_binder_capacity_property(self):
        self.assertEqual(self.binder.capacity, 9)
        binder_2x2 = make_binder(self.user, name="Small", rows=2, cols=2)
        self.assertEqual(binder_2x2.capacity, 4)

    def test_page_capacity_reads_from_binder(self):
        self.assertEqual(self.page.capacity, 9)
        binder_3x4 = make_binder(self.user, name="3x4", rows=3, cols=4)
        page = make_page(binder_3x4, order=0)
        self.assertEqual(page.capacity, 12)

    def test_duplicate_position_on_same_page_raises(self):
        BinderSlot.objects.create(page=self.page, card=self.card, position=0)
        card2 = make_card("c2", self.card_set)
        with self.assertRaises(IntegrityError):
            BinderSlot.objects.create(page=self.page, card=card2, position=0)

    def test_same_position_on_different_pages_is_allowed(self):
        page2 = make_page(self.binder, order=1)
        BinderSlot.objects.create(page=self.page, card=self.card, position=0)
        BinderSlot.objects.create(page=page2, card=self.card, position=0)
        self.assertEqual(BinderSlot.objects.count(), 2)

    def test_deleting_binder_cascades_to_pages_and_slots(self):
        BinderSlot.objects.create(page=self.page, card=self.card, position=0)
        self.binder.delete()
        self.assertEqual(BinderPage.objects.count(), 0)
        self.assertEqual(BinderSlot.objects.count(), 0)


# ---------------------------------------------------------------------------
# Binder CRUD
# ---------------------------------------------------------------------------

class BinderCRUDTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.binder = make_binder(self.user)

    def test_list_returns_only_own_binders(self):
        other = make_user("other", "other@example.com")
        make_binder(other, "Their Binder")
        resp = self.client.get("/binders/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["name"], self.binder.name)

    def test_list_includes_page_count_and_grid(self):
        make_page(self.binder, order=0)
        make_page(self.binder, order=1)
        resp = self.client.get("/binders/")
        self.assertEqual(resp.data[0]["page_count"], 2)
        self.assertEqual(resp.data[0]["rows"], 3)
        self.assertEqual(resp.data[0]["cols"], 3)
        self.assertEqual(resp.data[0]["capacity"], 9)

    def test_create_binder_default_grid(self):
        resp = self.client.post("/binders/", {"name": "New Binder"}, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["rows"], 3)
        self.assertEqual(resp.data["cols"], 3)

    def test_create_binder_with_custom_grid(self):
        resp = self.client.post(
            "/binders/", {"name": "Small", "rows": 2, "cols": 2}, format="json"
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["rows"], 2)
        self.assertEqual(resp.data["cols"], 2)
        self.assertEqual(resp.data["capacity"], 4)

    def test_create_binder_invalid_grid_returns_400(self):
        resp = self.client.post(
            "/binders/", {"name": "Bad", "rows": 5, "cols": 5}, format="json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_retrieve_includes_pages_and_slots(self):
        card_set = make_card_set()
        card = make_card("c1", card_set)
        page = make_page(self.binder, order=0)
        BinderSlot.objects.create(page=page, card=card, position=0)

        resp = self.client.get(f"/binders/{self.binder.id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["pages"]), 1)
        self.assertEqual(len(resp.data["pages"][0]["slots"]), 1)
        self.assertEqual(resp.data["pages"][0]["slots"][0]["position"], 0)

    def test_patch_updates_name(self):
        resp = self.client.patch(f"/binders/{self.binder.id}/", {"name": "Renamed"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.binder.refresh_from_db()
        self.assertEqual(self.binder.name, "Renamed")

    def test_patch_binder_invalid_grid_returns_400(self):
        resp = self.client.patch(
            f"/binders/{self.binder.id}/", {"rows": 1, "cols": 1}, format="json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_delete_binder(self):
        resp = self.client.delete(f"/binders/{self.binder.id}/")
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(Binder.objects.filter(pk=self.binder.pk).exists())

    def test_cannot_access_other_users_binder(self):
        other = make_user("other", "other@example.com")
        other_binder = make_binder(other, "Theirs")
        resp = self.client.get(f"/binders/{other_binder.id}/")
        self.assertEqual(resp.status_code, 404)

    def test_unauthenticated_returns_403(self):
        client = APIClient()
        resp = client.get("/binders/")
        self.assertEqual(resp.status_code, 403)


# ---------------------------------------------------------------------------
# Page CRUD
# ---------------------------------------------------------------------------

class BinderPageCRUDTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.binder = make_binder(self.user, rows=3, cols=3)

    def test_list_pages_ordered_by_order(self):
        make_page(self.binder, order=1, name="B")
        make_page(self.binder, order=0, name="A")
        resp = self.client.get(f"/binders/{self.binder.id}/pages/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data[0]["name"], "A")
        self.assertEqual(resp.data[1]["name"], "B")

    def test_create_page_auto_assigns_order(self):
        make_page(self.binder, order=0)
        make_page(self.binder, order=1)
        resp = self.client.post(
            f"/binders/{self.binder.id}/pages/", {}, format="json"
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["order"], 2)

    def test_create_page_first_page_gets_order_zero(self):
        resp = self.client.post(
            f"/binders/{self.binder.id}/pages/", {"name": "First"}, format="json"
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["order"], 0)

    def test_create_page_capacity_comes_from_binder(self):
        binder = make_binder(self.user, name="3x4 Binder", rows=3, cols=4)
        resp = self.client.post(
            f"/binders/{binder.id}/pages/", {"name": "P"}, format="json"
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["capacity"], 12)

    def test_retrieve_page_includes_slots(self):
        card_set = make_card_set()
        card = make_card("c1", card_set)
        page = make_page(self.binder, order=0)
        BinderSlot.objects.create(page=page, card=card, position=2)
        resp = self.client.get(f"/binders/{self.binder.id}/pages/{page.id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["slots"]), 1)
        self.assertEqual(resp.data["slots"][0]["position"], 2)

    def test_patch_page_name(self):
        page = make_page(self.binder, order=0, name="Old Name")
        resp = self.client.patch(
            f"/binders/{self.binder.id}/pages/{page.id}/",
            {"name": "New Name"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        page.refresh_from_db()
        self.assertEqual(page.name, "New Name")

    def test_delete_page_removes_slots(self):
        card_set = make_card_set()
        card = make_card("c1", card_set)
        page = make_page(self.binder, order=0)
        BinderSlot.objects.create(page=page, card=card, position=0)
        resp = self.client.delete(f"/binders/{self.binder.id}/pages/{page.id}/")
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(BinderPage.objects.filter(pk=page.pk).exists())
        self.assertFalse(BinderSlot.objects.filter(page=page).exists())


# ---------------------------------------------------------------------------
# Slot placement
# ---------------------------------------------------------------------------

class BinderSlotTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.binder = make_binder(self.user, rows=3, cols=3)
        self.page = make_page(self.binder)
        self.card_set = make_card_set()
        self.card = make_card("c1", self.card_set)

    def _slot_url(self, position):
        return f"/binders/{self.binder.id}/pages/{self.page.id}/slots/{position}/"

    def test_put_places_card_returns_201(self):
        resp = self.client.put(self._slot_url(0), {"card_id": "c1"}, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["position"], 0)
        self.assertEqual(resp.data["card"]["id"], "c1")

    def test_put_replaces_existing_card_returns_200(self):
        self.client.put(self._slot_url(0), {"card_id": "c1"}, format="json")
        card2 = make_card("c2", self.card_set, number="2")
        resp = self.client.put(self._slot_url(0), {"card_id": "c2"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["card"]["id"], "c2")
        self.assertEqual(BinderSlot.objects.filter(page=self.page, position=0).count(), 1)

    def test_put_out_of_bounds_returns_400(self):
        resp = self.client.put(self._slot_url(9), {"card_id": "c1"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("position", resp.data)

    def test_put_missing_card_id_returns_400(self):
        resp = self.client.put(self._slot_url(0), {}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("card_id", resp.data)

    def test_put_nonexistent_card_returns_404(self):
        resp = self.client.put(self._slot_url(0), {"card_id": "does-not-exist"}, format="json")
        self.assertEqual(resp.status_code, 404)

    def test_delete_slot_returns_204(self):
        BinderSlot.objects.create(page=self.page, card=self.card, position=0)
        resp = self.client.delete(self._slot_url(0))
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(BinderSlot.objects.filter(page=self.page, position=0).exists())

    def test_delete_empty_slot_returns_404(self):
        resp = self.client.delete(self._slot_url(0))
        self.assertEqual(resp.status_code, 404)

    def test_same_card_allowed_in_multiple_slots(self):
        self.client.put(self._slot_url(0), {"card_id": "c1"}, format="json")
        resp = self.client.put(self._slot_url(1), {"card_id": "c1"}, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(BinderSlot.objects.filter(page=self.page, card=self.card).count(), 2)


# ---------------------------------------------------------------------------
# Sizes endpoint
# ---------------------------------------------------------------------------

class BinderSizesTest(TestCase):
    def test_sizes_returns_all_allowed_sizes(self):
        resp = self.client.get("/binders/sizes/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 4)
        labels = {item["label"] for item in resp.data}
        self.assertEqual(labels, {"2x2", "3x3", "3x4", "4x4"})

    def test_sizes_includes_capacity(self):
        resp = self.client.get("/binders/sizes/")
        by_label = {item["label"]: item for item in resp.data}
        self.assertEqual(by_label["2x2"]["capacity"], 4)
        self.assertEqual(by_label["3x3"]["capacity"], 9)
        self.assertEqual(by_label["3x4"]["capacity"], 12)
        self.assertEqual(by_label["4x4"]["capacity"], 16)

    def test_sizes_requires_no_authentication(self):
        client = APIClient()
        resp = client.get("/binders/sizes/")
        self.assertEqual(resp.status_code, 200)


# ---------------------------------------------------------------------------
# Resize + overflow (binder-level)
# ---------------------------------------------------------------------------

class BinderResizeTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.binder = make_binder(self.user, rows=3, cols=3)
        self.card_set = make_card_set()
        self.cards = [make_card(f"c{i}", self.card_set, number=str(i)) for i in range(16)]

    def _binder_url(self):
        return f"/binders/{self.binder.id}/"

    def test_resize_down_no_overflow_when_slots_fit(self):
        page = make_page(self.binder, order=0)
        fill_page(page, self.cards[:3])

        resp = self.client.patch(self._binder_url(), {"rows": 2, "cols": 2}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.binder.pages.count(), 1)
        self.assertEqual(page.slots.count(), 3)

    def test_resize_3x3_full_to_2x2_creates_two_overflow_pages(self):
        page = make_page(self.binder, order=0)
        fill_page(page, self.cards[:9])

        resp = self.client.patch(self._binder_url(), {"rows": 2, "cols": 2}, format="json")
        self.assertEqual(resp.status_code, 200)

        pages = list(self.binder.pages.order_by("order"))
        self.assertEqual(len(pages), 3)
        self.assertEqual(pages[0].slots.count(), 4)
        self.assertEqual(pages[1].slots.count(), 4)
        self.assertEqual(pages[2].slots.count(), 1)

    def test_binder_grid_updated_after_resize(self):
        make_page(self.binder, order=0)
        self.client.patch(self._binder_url(), {"rows": 2, "cols": 2}, format="json")
        self.binder.refresh_from_db()
        self.assertEqual(self.binder.rows, 2)
        self.assertEqual(self.binder.cols, 2)

    def test_all_pages_capacity_reflects_new_binder_size(self):
        page0 = make_page(self.binder, order=0)
        page1 = make_page(self.binder, order=1)
        fill_page(page0, self.cards[:9])

        self.client.patch(self._binder_url(), {"rows": 2, "cols": 2}, format="json")
        self.binder.refresh_from_db()

        for page in self.binder.pages.all():
            self.assertEqual(page.capacity, 4)

    def test_overflow_slots_get_sequential_positions_from_zero(self):
        page = make_page(self.binder, order=0)
        fill_page(page, self.cards[:9])

        self.client.patch(self._binder_url(), {"rows": 2, "cols": 2}, format="json")

        for pg in self.binder.pages.order_by("order"):
            positions = list(pg.slots.order_by("position").values_list("position", flat=True))
            self.assertEqual(positions, list(range(len(positions))))

    def test_overflow_preserves_card_order(self):
        page = make_page(self.binder, order=0)
        fill_page(page, self.cards[:9])
        original_ids = [c.id for c in self.cards[:9]]

        self.client.patch(self._binder_url(), {"rows": 2, "cols": 2}, format="json")

        result_ids = []
        for pg in self.binder.pages.order_by("order"):
            result_ids.extend(pg.slots.order_by("position").values_list("card_id", flat=True))
        self.assertEqual(result_ids, original_ids)

    def test_existing_later_pages_shift_order_correctly(self):
        page0 = make_page(self.binder, order=0)
        page1 = make_page(self.binder, order=1, name="Later A")
        page2 = make_page(self.binder, order=2, name="Later B")
        fill_page(page0, self.cards[:9])

        self.client.patch(self._binder_url(), {"rows": 2, "cols": 2}, format="json")

        page1.refresh_from_db()
        page2.refresh_from_db()
        self.assertEqual(page1.order, 3)
        self.assertEqual(page2.order, 4)

    def test_resize_up_keeps_all_slots_on_original_page(self):
        self.binder.rows = 2
        self.binder.cols = 2
        self.binder.save()
        page = make_page(self.binder, order=0)
        fill_page(page, self.cards[:4])

        resp = self.client.patch(self._binder_url(), {"rows": 4, "cols": 4}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.binder.pages.count(), 1)
        self.assertEqual(page.slots.count(), 4)

    def test_resize_to_same_size_is_a_no_op(self):
        page = make_page(self.binder, order=0)
        fill_page(page, self.cards[:5])

        resp = self.client.patch(self._binder_url(), {"rows": 3, "cols": 3}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.binder.pages.count(), 1)
        self.assertEqual(page.slots.count(), 5)

    def test_resize_name_and_grid_together_updates_both(self):
        page = make_page(self.binder, order=0)
        fill_page(page, self.cards[:5])

        resp = self.client.patch(
            self._binder_url(), {"name": "Renamed", "rows": 2, "cols": 2}, format="json"
        )
        self.assertEqual(resp.status_code, 200)
        self.binder.refresh_from_db()
        self.assertEqual(self.binder.name, "Renamed")
        self.assertEqual(self.binder.rows, 2)

    def test_multiple_pages_all_overflow_on_binder_resize(self):
        page0 = make_page(self.binder, order=0)
        page1 = make_page(self.binder, order=1)
        fill_page(page0, self.cards[:9])
        fill_page(page1, self.cards[:9])

        self.client.patch(self._binder_url(), {"rows": 2, "cols": 2}, format="json")

        # 2 original pages × 3 result pages each = 6 total
        self.assertEqual(self.binder.pages.count(), 6)
