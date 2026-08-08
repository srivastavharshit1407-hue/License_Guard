from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from apps.tenants.models import Organization

from .models import User


class UserSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = User
        fields = (
            "id", "email", "full_name", "role", "avatar_url",
            "organization", "organization_name", "auth_provider", "date_joined",
        )
        read_only_fields = fields


class SignupSerializer(serializers.Serializer):
    """
    Signing up creates BOTH a user and the organization they own.
    The first person from a company to sign up becomes its Owner.
    """

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=10)
    full_name = serializers.CharField(max_length=200, allow_blank=True, required=False)
    company_name = serializers.CharField(max_length=200)

    def validate_email(self, value: str) -> str:
        value = value.lower().strip()
        if settings.SIGNUP_ALLOWED_EMAILS and value not in settings.SIGNUP_ALLOWED_EMAILS:
            raise serializers.ValidationError("Signups are currently invite-only.")
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value

    @transaction.atomic
    def create(self, validated_data):
        email = validated_data["email"]
        domain = email.split("@")[-1]
        org = Organization.objects.create(
            name=validated_data["company_name"],
            primary_domain=domain,
        )
        return User.objects.create_user(
            email=email,
            password=validated_data["password"],
            full_name=validated_data.get("full_name", ""),
            organization=org,
            role=User.Role.OWNER,
        )


class GoogleAuthSerializer(serializers.Serializer):
    """Accepts the ID token that Google Identity Services returns in the browser."""

    credential = serializers.CharField()
