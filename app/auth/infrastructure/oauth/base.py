"""Base OAuth provider - Abstract base for OAuth implementations."""

from abc import abstractmethod
from typing import Optional
from urllib.parse import urlencode

import httpx

from app.auth.application.port.oauth_provider_port import OAuthProviderPort, OAuthUserInfo
from app.common.domain.exceptions import OAuthException


class BaseOAuthProvider(OAuthProviderPort):
    """Base class for OAuth providers.

    Provides common functionality for OAuth 2.0 authorization code flow.
    Subclasses must implement provider-specific details.
    """

    # Override these in subclasses
    AUTHORIZE_URL: str = ""
    TOKEN_URL: str = ""
    USERINFO_URL: str = ""
    SCOPES: list[str] = []

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ):
        """Initialize OAuth provider.

        Args:
            client_id: OAuth client ID.
            client_secret: OAuth client secret.
            redirect_uri: Callback URL after authorization.
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_authorization_url(self, state: str) -> str:
        """Get the OAuth authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "state": state,
            "scope": " ".join(self.SCOPES),
        }
        # Add any extra params from subclass
        params.update(self._get_extra_auth_params())
        return f"{self.AUTHORIZE_URL}?{urlencode(params)}"

    def _get_extra_auth_params(self) -> dict:
        """Get extra authorization parameters. Override in subclasses if needed."""
        return {}

    async def exchange_code_for_token(self, code: str) -> str:
        """Exchange authorization code for access token."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.TOKEN_URL,
                    data=data,
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                token_data = response.json()
                return token_data.get("access_token", "")
            except httpx.HTTPStatusError as e:
                raise OAuthException(
                    self.provider_name,
                    f"Token exchange failed: {e.response.status_code}",
                )
            except Exception as e:
                raise OAuthException(
                    self.provider_name,
                    f"Token exchange failed: {str(e)}",
                )

    @abstractmethod
    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """Get user info from OAuth provider. Must be implemented by subclasses."""
        pass

    async def _fetch_user_info(
        self,
        access_token: str,
        url: Optional[str] = None,
        params: Optional[dict] = None,
    ) -> dict:
        """Fetch user info from provider's userinfo endpoint."""
        url = url or self.USERINFO_URL

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {access_token}"},
                    params=params,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise OAuthException(
                    self.provider_name,
                    f"Failed to fetch user info: {e.response.status_code}",
                )
            except Exception as e:
                raise OAuthException(
                    self.provider_name,
                    f"Failed to fetch user info: {str(e)}",
                )
