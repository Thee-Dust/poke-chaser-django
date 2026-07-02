from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase, override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient

from pokechaser.collections.models import Collection
from pokechaser.core.models import User


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PasswordResetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="Str0ngPass!"
        )

    def test_request_reset_with_known_email_sends_mail(self):
        resp = self.client.post(
            "/auth/password-reset/",
            {"email": "test@example.com"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("reset-password?uid=", mail.outbox[0].body)
        self.assertIn("token=", mail.outbox[0].body)
        self.assertEqual(len(mail.outbox[0].alternatives), 1)
        html_body, content_type = mail.outbox[0].alternatives[0]
        self.assertEqual(content_type, "text/html")
        self.assertIn("reset-password?uid=", html_body)
        self.assertIn("token=", html_body)

    def test_request_reset_with_unknown_email_returns_200_no_mail(self):
        resp = self.client.post(
            "/auth/password-reset/",
            {"email": "nobody@example.com"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        self.assertIn("reset link has been sent", resp.data["detail"])

    def test_confirm_with_valid_token_resets_password(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        resp = self.client.post(
            "/auth/password-reset/confirm/",
            {"uid": uid, "token": token, "password": "NewStr0ngPass!"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        login_resp = self.client.post(
            "/auth/login/",
            {"identifier": "testuser", "password": "NewStr0ngPass!"},
            format="json",
        )
        self.assertEqual(login_resp.status_code, 200)

    def test_confirm_with_invalid_token_returns_400(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        resp = self.client.post(
            "/auth/password-reset/confirm/",
            {"uid": uid, "token": "invalid-token", "password": "NewStr0ngPass!"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_confirm_with_weak_password_returns_400(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        resp = self.client.post(
            "/auth/password-reset/confirm/",
            {"uid": uid, "token": token, "password": "123"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("password", resp.data)


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
