"""Authentication helpers for AutoDQ Studio.

Production authentication uses Streamlit's native OpenID Connect support.
Local contributors can opt into an explicit development identity without
needing an external identity provider.
"""

from __future__ import annotations

import os
import time
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any


class AuthMode(str, Enum):
    """Supported AutoDQ Studio authentication modes."""

    REQUIRED = "required"
    DEVELOPMENT = "development"


class AuthenticationError(ValueError):
    """Base error for invalid or unusable authentication state."""


class ExpiredIdentityError(AuthenticationError):
    """Raised when an OIDC identity token has expired."""


@dataclass(frozen=True)
class UserIdentity:
    """The small, non-secret identity surface used by AutoDQ Studio."""

    issuer: str
    subject: str
    display_name: str
    email: str | None = None
    picture_url: str | None = None
    is_development: bool = False

    @property
    def identity_key(self) -> str:
        """Return the stable key Phase 2 will persist in the users table."""

        return f"{self.issuer}|{self.subject}"


def resolve_auth_mode(environ: Mapping[str, str] | None = None) -> AuthMode:
    """Resolve the configured mode, defaulting to secure OIDC authentication."""

    values = os.environ if environ is None else environ
    raw = values.get("AUTODQ_AUTH_MODE", AuthMode.REQUIRED.value).strip().lower()
    try:
        return AuthMode(raw)
    except ValueError as error:
        options = ", ".join(mode.value for mode in AuthMode)
        raise AuthenticationError(
            f"Unsupported AUTODQ_AUTH_MODE {raw!r}. Expected one of: {options}."
        ) from error


def configured_provider(environ: Mapping[str, str] | None = None) -> str | None:
    """Return an optional named OIDC provider configured for ``st.login``."""

    values = os.environ if environ is None else environ
    provider = values.get("AUTODQ_AUTH_PROVIDER", "").strip()
    return provider or None


def development_identity(
    environ: Mapping[str, str] | None = None,
) -> UserIdentity:
    """Build the explicit local-development identity."""

    values = os.environ if environ is None else environ
    return UserIdentity(
        issuer="autodq-development",
        subject=values.get("AUTODQ_DEV_USER_ID", "local-developer").strip()
        or "local-developer",
        display_name=values.get("AUTODQ_DEV_USER_NAME", "Local developer").strip()
        or "Local developer",
        email=values.get("AUTODQ_DEV_USER_EMAIL", "developer@localhost").strip()
        or None,
        is_development=True,
    )


def identity_from_claims(
    claims: Mapping[str, Any],
    *,
    now: float | None = None,
) -> UserIdentity:
    """Validate OIDC claims and convert them to AutoDQ's identity model."""

    issuer = str(claims.get("iss") or "").strip()
    subject = str(claims.get("sub") or "").strip()
    if not issuer or not subject:
        raise AuthenticationError(
            "The identity provider did not return iss and sub claims."
        )

    expiration = claims.get("exp")
    if expiration is not None:
        try:
            expired = float(expiration) <= (time.time() if now is None else now)
        except (TypeError, ValueError) as error:
            raise AuthenticationError("The identity token has an invalid exp claim.") from error
        if expired:
            raise ExpiredIdentityError("Your sign-in session has expired.")

    email = str(
        claims.get("email") or claims.get("preferred_username") or ""
    ).strip() or None
    display_name = str(claims.get("name") or "").strip()
    if not display_name:
        display_name = email.split("@", maxsplit=1)[0] if email else "AutoDQ user"

    picture = str(claims.get("picture") or "").strip() or None
    return UserIdentity(
        issuer=issuer,
        subject=subject,
        display_name=display_name,
        email=email,
        picture_url=picture,
    )


def oidc_configuration_present(
    secrets: Mapping[str, Any],
    provider: str | None = None,
) -> bool:
    """Check whether Streamlit secrets contain a complete OIDC definition."""

    auth_value = secrets.get("auth")
    if not isinstance(auth_value, Mapping):
        return False

    shared = {"redirect_uri", "cookie_secret"}
    provider_fields = {"client_id", "client_secret", "server_metadata_url"}
    if not shared.issubset(auth_value):
        return False

    provider_value: Mapping[str, Any] = auth_value
    if provider is not None:
        candidate = auth_value.get(provider)
        if not isinstance(candidate, Mapping):
            return False
        provider_value = candidate
    return provider_fields.issubset(provider_value)


def _streamlit_secrets(st: Any) -> Mapping[str, Any]:
    try:
        return dict(st.secrets)
    except Exception:
        return {}


def _streamlit_user_claims(st: Any) -> Mapping[str, Any]:
    try:
        user = st.user
        if hasattr(user, "to_dict"):
            return user.to_dict()
        return dict(user)
    except Exception:
        return {}


def render_login_page(st: Any, *, provider: str | None, configured: bool) -> None:
    """Render the authenticated entrance to AutoDQ Studio."""

    st.markdown(
        """
        <div class="dq-auth-hero">
          <div class="dq-auth-mark">DQ</div>
          <div class="dq-kicker">AutoDQ Studio</div>
          <h1>Quality intelligence,<br/>inside a secure workspace.</h1>
          <p>Sign in to analyze data, review cleaning decisions, run ADQL, and
          keep every project associated with the correct workspace.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    left, right = st.columns([1.35, 0.65], gap="large")
    with left:
        st.markdown(
            """
            <div class="dq-auth-benefits">
              <div><strong>Verified identity</strong><span>Your account becomes the secure foundation for personal and team workspaces.</span></div>
              <div><strong>Durable history</strong><span>Project persistence and audit history arrive in the next v1.1 phase.</span></div>
              <div><strong>No AutoDQ passwords</strong><span>Your identity provider handles credentials and account recovery.</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.subheader("Welcome back")
        st.caption("Continue through your organization’s secure identity provider.")
        if not configured:
            st.error(
                "Sign-in has not been configured for this deployment. "
                "Ask the administrator to add the OIDC settings."
            )
            return

        label = os.environ.get("AUTODQ_AUTH_BUTTON_LABEL", "Continue to AutoDQ")
        if st.button(label, type="primary", width="stretch"):
            try:
                if provider is None:
                    st.login()
                else:
                    st.login(provider)
            except Exception as error:
                st.error(f"Sign-in could not be started: {error}")


def require_identity() -> UserIdentity | None:
    """Return the active identity or render the login gate and return ``None``."""

    import streamlit as st

    mode = resolve_auth_mode()
    if mode is AuthMode.DEVELOPMENT:
        return development_identity()

    provider = configured_provider()
    claims = _streamlit_user_claims(st)
    if claims.get("is_logged_in"):
        try:
            return identity_from_claims(claims)
        except ExpiredIdentityError:
            st.warning("Your AutoDQ session has expired. Sign in again to continue.")
            if st.button("Sign in again", type="primary"):
                st.logout()
            return None
        except AuthenticationError as error:
            st.error(f"AutoDQ could not verify this identity: {error}")
            if st.button("Return to sign in"):
                st.logout()
            return None

    secrets = _streamlit_secrets(st)
    render_login_page(
        st,
        provider=provider,
        configured=oidc_configuration_present(secrets, provider),
    )
    return None
