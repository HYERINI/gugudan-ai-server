"""OAuth provider factory - Creates OAuth providers by name."""

from typing import Dict, Type

from app.auth.application.port.oauth_provider_port import OAuthProviderPort
from app.common.domain.exceptions import UnsupportedOAuthProviderException
from app.auth.infrastructure.oauth.google import GoogleOAuthProvider
from app.auth.infrastructure.oauth.kakao import KakaoOAuthProvider
from app.auth.infrastructure.oauth.naver import NaverOAuthProvider
from app.auth.infrastructure.oauth.meta import MetaOAuthProvider

class OAuthProviderFactory:
    """Factory for creating OAuth providers.

    Uses a registry pattern for easy addition of new providers.
    """

    # Provider registry: name -> provider class
    _providers: Dict[str, Type[OAuthProviderPort]] = {
        "google": GoogleOAuthProvider,
        "kakao": KakaoOAuthProvider,
        "naver": NaverOAuthProvider,
        "meta": MetaOAuthProvider,
    }

    @classmethod
    def get_provider(cls, provider_name: str) -> OAuthProviderPort:
        """Get an OAuth provider instance by name.

        Args:
            provider_name: Name of the provider (e.g., "google", "kakao", "naver", "meta").

        Returns:
            An instance of the OAuth provider.

        Raises:
            UnsupportedOAuthProviderException: If provider is not supported.
        """
        provider_name = provider_name.lower()
        provider_class = cls._providers.get(provider_name)

        if provider_class is None:
            raise UnsupportedOAuthProviderException(provider_name)

        return provider_class()

    @classmethod
    def register_provider(
        cls,
        name: str,
        provider_class: Type[OAuthProviderPort],
    ) -> None:
        """Register a new OAuth provider.

        Args:
            name: Name to register the provider under.
            provider_class: The provider class to register.
        """
        cls._providers[name.lower()] = provider_class

    @classmethod
    def get_supported_providers(cls) -> list[str]:
        """Get list of supported provider names."""
        return list(cls._providers.keys())

    @classmethod
    def is_supported(cls, provider_name: str) -> bool:
        """Check if a provider is supported."""
        return provider_name.lower() in cls._providers
