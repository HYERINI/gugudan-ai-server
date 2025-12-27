from app.auth.application.port.oauth_provider_port import OAuthUserInfo
from app.auth.infrastructure.oauth.base import BaseOAuthProvider
from app.config.settings import settings


class MetaOAuthProvider(BaseOAuthProvider):
    # Facebook Login endpoints
    AUTHORIZE_URL = "https://www.facebook.com/v20.0/dialog/oauth"
    TOKEN_URL = "https://graph.facebook.com/v20.0/oauth/access_token"
    USERINFO_URL = "https://graph.facebook.com/me"

    # 보통 email은 퍼미션 필요 (승인/상태에 따라 빈 값 가능)
    SCOPES = ["email", "public_profile"]

    def __init__(self):
        super().__init__(
            client_id=settings.META_CLIENT_ID,
            client_secret=settings.META_CLIENT_SECRET,
            redirect_uri=settings.META_REDIRECT_URI,
        )

    @property
    def provider_name(self) -> str:
        return "meta"

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        # Facebook은 fields 쿼리 파라미터로 요청
        data = await self._fetch_user_info(
            access_token,
            params={"fields": "id,name,email,picture.width(256).height(256)"},
        )

        picture_url = None
        try:
            picture_url = (
                data.get("picture", {})
                    .get("data", {})
                    .get("url")
            )
        except Exception:
            picture_url = None

        email = data.get("email", "")  # 없을 수 있음

        return OAuthUserInfo(
            email=email,
            name=data.get("name", "") or (email.split("@")[0] if email else ""),
            picture=picture_url,
            provider=self.provider_name,
        )
