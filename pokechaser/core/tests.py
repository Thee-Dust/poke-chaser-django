from django.test import TestCase
from rest_framework.test import APIClient

from pokechaser.collections.models import Collection
from pokechaser.core.models import User


class AuthTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_creates_user_and_default_collection(self):
        resp = self.client.post(
            "/auth/register/",
            {"username": "newuser", "email": "new@example.com", "password": "Str0ngPass!"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(User.objects.filter(username="newuser").exists())
        user = User.objects.get(username="newuser")
        self.assertTrue(Collection.objects.filter(user=user, is_default=True).exists())

    def test_register_duplicate_email_returns_400(self):
        User.objects.create_user(username="existing", email="taken@example.com", password="pass")
        resp = self.client.post(
            "/auth/register/",
            {"username": "newuser", "email": "taken@example.com", "password": "Str0ngPass!"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_register_duplicate_username_returns_400(self):
        User.objects.create_user(username="taken", email="a@example.com", password="pass")
        resp = self.client.post(
            "/auth/register/",
            {"username": "taken", "email": "b@example.com", "password": "Str0ngPass!"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_login_with_valid_credentials_returns_200(self):
        User.objects.create_user(username="testuser", email="test@example.com", password="Str0ngPass!")
        resp = self.client.post(
            "/auth/login/",
            {"identifier": "testuser", "password": "Str0ngPass!"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("username", resp.data)

    def test_login_with_email_identifier_returns_200(self):
        User.objects.create_user(username="testuser", email="test@example.com", password="Str0ngPass!")
        resp = self.client.post(
            "/auth/login/",
            {"identifier": "test@example.com", "password": "Str0ngPass!"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)

    def test_login_with_wrong_password_returns_400(self):
        User.objects.create_user(username="testuser", email="test@example.com", password="Str0ngPass!")
        resp = self.client.post(
            "/auth/login/",
            {"identifier": "testuser", "password": "wrongpassword"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_me_without_auth_returns_403(self):
        resp = self.client.get("/auth/me/")
        self.assertEqual(resp.status_code, 403)

    def test_me_with_auth_returns_user_data(self):
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="Str0ngPass!"
        )
        self.client.force_authenticate(user=user)
        resp = self.client.get("/auth/me/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["username"], "testuser")
        self.assertEqual(resp.data["email"], "test@example.com")
