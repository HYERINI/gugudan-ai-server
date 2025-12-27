"""SSO Login Type enumeration."""

from enum import Enum


class SSOLoginType(str, Enum):
    """Enumeration of supported SSO login providers.

    Each value represents a valid OAuth provider that can be used
    for authentication in the application.
    """

    GOOGLE = "google"
    KAKAO = "kakao"
    NAVER = "naver"
    META = "meta"

    @classmethod
    def from_string(cls, provider: str) -> "SSOLoginType":
        """Convert a string to SSOLoginType.

        Args:
            provider: The provider name string.

        Returns:
            The corresponding SSOLoginType.

        Raises:
            ValueError: If provider is not supported.
        """
        provider_lower = provider.lower()
        for login_type in cls:
            if login_type.value == provider_lower:
                return login_type
        raise ValueError(f"Unsupported SSO provider: {provider}")

    @classmethod
    def get_supported_providers(cls) -> list[str]:
        """Get list of supported provider names."""
        return [provider.value for provider in cls]

    def __str__(self) -> str:
        """Return the string value of the enum."""
        return self.value
