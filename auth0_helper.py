"""
auth0_helper.py — Auth0 Social Login Integration for MedDigit AI
=================================================================
Adds Auth0 OAuth2 as an ADDITIONAL login option.
The existing email + OTP login is completely unchanged.

Requires environment variables:
    AUTH0_DOMAIN         e.g.  your-tenant.auth0.com
    AUTH0_CLIENT_ID      from Auth0 dashboard
    AUTH0_CLIENT_SECRET  from Auth0 dashboard
    AUTH0_CALLBACK_URL   e.g.  http://localhost:8080/auth/auth0/callback

If any of these are missing, Auth0 login is quietly disabled.
"""

import os
from authlib.integrations.flask_client import OAuth

# Global OAuth instance — registered once at app startup
oauth = OAuth()
_auth0 = None


def register_auth0(app):
    """
    Call this once inside create_app() after the Flask app is created.
    Registers Auth0 with the OAuth client. Safe to call even if env vars
    are missing — it simply skips registration.
    """
    global _auth0

    domain = os.environ.get("AUTH0_DOMAIN", "").strip()
    client_id = os.environ.get("AUTH0_CLIENT_ID", "").strip()
    client_secret = os.environ.get("AUTH0_CLIENT_SECRET", "").strip()

    if not all([domain, client_id, client_secret]):
        print("ℹ️  Auth0 env vars not set — social login disabled (app works normally)")
        return

    oauth.init_app(app)

    _auth0 = oauth.register(
        "auth0",
        client_id=client_id,
        client_secret=client_secret,
        client_kwargs={"scope": "openid profile email"},
        server_metadata_url=f"https://{domain}/.well-known/openid-configuration",
    )
    print(f"✅ Auth0 registered → https://{domain}")


def get_auth0():
    """Returns the Auth0 OAuth client, or None if not configured."""
    return _auth0
