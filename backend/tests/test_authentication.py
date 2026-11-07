import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()

@pytest.mark.django_db
class TestAuthentication:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = APIClient()

    def test_public_registration_cannot_elevate_privileges(self):
        payload = {
            "email": "newuser@digitalequb.et",
            "phone_number": "+251911000001",
            "full_name": "Test Candidate",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
            "is_platform_admin": True # Attacker attempts to self-grant super admin
        }
        res = self.client.post("/api/v1/auth/register/", payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        user = User.objects.get(email="newuser@digitalequb.et")
        assert user.is_platform_admin is False
        assert user.is_staff is False
        assert user.is_superuser is False
        assert user.check_password("StrongPassword123!")

    def test_login_success_and_session(self):
        user = User.objects.create_user(
            email="regular@digitalequb.et",
            password="ValidPass123!",
            full_name="Regular Member"
        )
        res = self.client.post("/api/v1/auth/login/", {
            "email": "regular@digitalequb.et",
            "password": "ValidPass123!"
        }, format="json")
        assert res.status_code == status.HTTP_200_OK
        assert "user" in res.data
        assert res.data["user"]["email"] == "regular@digitalequb.et"

    def test_suspended_user_cannot_login(self):
        user = User.objects.create_user(
            email="suspended@digitalequb.et",
            password="ValidPass123!",
            full_name="Suspended Person",
            account_status=User.AccountStatus.SUSPENDED
        )
        res = self.client.post("/api/v1/auth/login/", {
            "email": "suspended@digitalequb.et",
            "password": "ValidPass123!"
        }, format="json")
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_anonymous_user_blocked_from_protected_endpoints(self):
        res = self.client.get("/api/v1/auth/me/")
        assert res.status_code == status.HTTP_403_FORBIDDEN or res.status_code == status.HTTP_401_UNAUTHORIZED
