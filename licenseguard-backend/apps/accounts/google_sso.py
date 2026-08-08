"""
Verifies a Google ID token and maps it to a LicenseGuard user.

Flow, end to end:
  1. Browser loads Google Identity Services and the user clicks "Sign in with Google".
  2. Google hands the browser a signed JWT ("credential").
  3. Browser POSTs it to /api/auth/google/.
  4. This module verifies the signature against Google's public keys and checks
     that the token was minted for OUR client ID. Never trust an unverified token.
  5. We find-or-create the user, joining them to the org that owns their email domain.
"""
from __future__ import annotations

from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from rest_framework.exceptions import AuthenticationFailed

from apps.tenants.models import Organization

from .models import User


def verify_google_credential(credential: str) -> dict:
    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        raise AuthenticationFailed("GOOGLE_OAUTH_CLIENT_ID is not configured on the server.")
    try:
        claims = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            settings.GOOGLE_OAUTH_CLIENT_ID,
        )
    except ValueError as exc:
        raise AuthenticationFailed(f"Invalid Google token: {exc}") from exc

    if claims.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
        raise AuthenticationFailed("Unexpected token issuer.")
    if not claims.get("email_verified"):
        raise AuthenticationFailed("Google account email is not verified.")
    return claims


def get_or_create_user_from_google(claims: dict) -> User:
    email = claims["email"].lower()
    domain = claims.get("hd") or email.split("@")[-1]

    user = User.objects.filter(email=email).first()
    if user:
        if not user.organization:
            user.organization = _resolve_org(domain, claims)
        user.auth_provider = "google"
        user.avatar_url = claims.get("picture", user.avatar_url)
        user.full_name = user.full_name or claims.get("name", "")
        user.save(update_fields=["organization", "auth_provider", "avatar_url", "full_name"])
        return user

    if settings.SIGNUP_ALLOWED_EMAILS and email not in settings.SIGNUP_ALLOWED_EMAILS:
        raise AuthenticationFailed("Signups are currently invite-only.")

    org = _resolve_org(domain, claims)
    # First user of a brand new org owns it; everyone after is a viewer by default.
    role = User.Role.OWNER if not org.users.exists() else User.Role.VIEWER
    user = User.objects.create_user(
        email=email,
        password=None,
        full_name=claims.get("name", ""),
        organization=org,
        role=role,
        auth_provider="google",
        avatar_url=claims.get("picture", ""),
    )
    user.set_unusable_password()
    user.save(update_fields=["password"])
    return user


def _resolve_org(domain: str, claims: dict) -> Organization:
    org = Organization.objects.filter(primary_domain__iexact=domain).first()
    if org:
        return org
    return Organization.objects.create(
        name=claims.get("hd") or domain,
        primary_domain=domain,
    )
