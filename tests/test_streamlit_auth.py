import unittest

from app.autodq_web.auth import (
    AuthMode,
    AuthenticationError,
    ExpiredIdentityError,
    configured_provider,
    development_identity,
    identity_from_claims,
    oidc_configuration_present,
    resolve_auth_mode,
)


class StreamlitAuthenticationTests(unittest.TestCase):
    def test_authentication_is_secure_by_default(self):
        self.assertEqual(resolve_auth_mode({}), AuthMode.REQUIRED)
        self.assertEqual(
            resolve_auth_mode({"AUTODQ_AUTH_MODE": "DEVELOPMENT"}),
            AuthMode.DEVELOPMENT,
        )
        with self.assertRaises(AuthenticationError):
            resolve_auth_mode({"AUTODQ_AUTH_MODE": "disabled"})

    def test_development_identity_is_explicit_and_stable(self):
        identity = development_identity(
            {
                "AUTODQ_DEV_USER_ID": "joseph-local",
                "AUTODQ_DEV_USER_NAME": "Joseph",
                "AUTODQ_DEV_USER_EMAIL": "joseph@example.test",
            }
        )
        self.assertTrue(identity.is_development)
        self.assertEqual(identity.identity_key, "autodq-development|joseph-local")
        self.assertEqual(identity.display_name, "Joseph")

    def test_oidc_claims_become_a_non_secret_identity(self):
        identity = identity_from_claims(
            {
                "iss": "https://identity.example/",
                "sub": "auth0|123",
                "name": "Ada Analyst",
                "email": "ada@example.test",
                "picture": "https://example.test/ada.png",
                "exp": 2_000,
            },
            now=1_000,
        )
        self.assertEqual(
            identity.identity_key,
            "https://identity.example/|auth0|123",
        )
        self.assertEqual(identity.email, "ada@example.test")
        self.assertFalse(identity.is_development)

    def test_expired_and_incomplete_claims_are_rejected(self):
        with self.assertRaises(ExpiredIdentityError):
            identity_from_claims(
                {"iss": "https://identity.example/", "sub": "123", "exp": 99},
                now=100,
            )
        with self.assertRaises(AuthenticationError):
            identity_from_claims({"sub": "123"})

    def test_named_oidc_configuration_must_be_complete(self):
        secrets = {
            "auth": {
                "redirect_uri": "http://localhost:8501/oauth2callback",
                "cookie_secret": "secret",
                "auth0": {
                    "client_id": "client",
                    "client_secret": "client-secret",
                    "server_metadata_url": "https://example.test/.well-known/openid-configuration",
                },
            }
        }
        self.assertTrue(oidc_configuration_present(secrets, "auth0"))
        self.assertFalse(oidc_configuration_present(secrets, "microsoft"))
        self.assertEqual(
            configured_provider({"AUTODQ_AUTH_PROVIDER": "auth0"}),
            "auth0",
        )


if __name__ == "__main__":
    unittest.main()
