"""Auth API router - OAuth endpoints with JWT support."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse

from app.auth.adapter.input.web.dependencies import (
    get_account_usecase,
    get_auth_usecase,
    get_current_session,
    get_current_jwt_payload,
    get_optional_session,
    get_optional_jwt_payload,
)
from app.auth.adapter.input.web.response import (
    AuthStatusResponse,
    LogoutResponse,
    OAuthProvidersResponse,
    UserResponse,
)
from app.account.application.usecase.account_usecase import AccountUseCase
from app.auth.application.port.jwt_token_port import TokenPayload
from app.auth.application.usecase.auth_usecase import AuthUseCase
from app.auth.domain.entity.session import Session
from app.common.domain.exceptions import UnsupportedOAuthProviderException
from app.config.settings import settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/providers", response_model=OAuthProvidersResponse)
async def get_providers(
    auth_usecase: AuthUseCase = Depends(get_auth_usecase),
) -> OAuthProvidersResponse:
    """Get list of supported OAuth providers."""
    providers = auth_usecase.get_supported_providers()
    return OAuthProvidersResponse(providers=providers)


@router.get("/status", response_model=AuthStatusResponse)
async def get_auth_status(
    jwt_payload: TokenPayload | None = Depends(get_optional_jwt_payload),
    session: Session | None = Depends(get_optional_session),
    account_usecase: AccountUseCase = Depends(get_account_usecase),
) -> AuthStatusResponse:
    """Check authentication status.

    Returns authentication status and user info if authenticated.
    Supports both JWT and session-based authentication.
    """
    # Try JWT first, then fall back to session
    account_id = None

    if jwt_payload:
        account_id = jwt_payload.account_id
    elif session:
        account_id = session.account_id

    if not account_id:
        return AuthStatusResponse(is_authenticated=False)

    account = account_usecase.get_account_by_id(account_id)

    if not account:
        return AuthStatusResponse(is_authenticated=False)

    return AuthStatusResponse(
        is_authenticated=True,
        user=UserResponse.from_entity(account),
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    jwt_payload: TokenPayload = Depends(get_current_jwt_payload),
    auth_usecase: AuthUseCase = Depends(get_auth_usecase),
) -> UserResponse:
    """Get current authenticated user (JWT-based)."""
    account = auth_usecase.get_account_by_id(jwt_payload.account_id)

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    return UserResponse.from_entity(account)


@router.get("/me/session", response_model=UserResponse)
async def get_current_user_session(
    session: Session = Depends(get_current_session),
    account_usecase: AccountUseCase = Depends(get_account_usecase),
) -> UserResponse:
    """Get current authenticated user (session-based, legacy)."""
    account = account_usecase.get_account_by_id(session.account_id)

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    return UserResponse.from_entity(account)


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    response: Response,
    jwt_payload: TokenPayload | None = Depends(get_optional_jwt_payload),
    session: Session | None = Depends(get_optional_session),
    auth_usecase: AuthUseCase = Depends(get_auth_usecase),
) -> LogoutResponse:
    """Logout - blacklist JWT and clear cookies.

    Supports both JWT and session-based authentication.
    Blacklists JWT token to prevent reuse until expiration.
    """
    # Blacklist JWT token if exists
    token = request.cookies.get("access_token")
    if token:
        auth_usecase.blacklist_jwt(token)

    # Destroy session if exists
    if session:
        auth_usecase.logout(session.session_id)

    # Clear all auth cookies
    response.delete_cookie("access_token")
    response.delete_cookie("csrf_token")
    response.delete_cookie("session_id")

    return LogoutResponse()


# Dynamic provider routes must come AFTER specific routes
@router.get("/{provider}")
async def oauth_login(
    provider: str,
    auth_usecase: AuthUseCase = Depends(get_auth_usecase),
) -> RedirectResponse:
    """Initiate OAuth login flow.

    Redirects user to OAuth provider's authorization page.
    """
    try:
        url, state = auth_usecase.initiate_oauth(provider)

        # Create redirect response
        response = RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)

        # Store state in cookie for CSRF protection on callback
        response.set_cookie(
            key="oauth_state",
            value=state,
            httponly=True,
            secure=settings.effective_cookie_secure,
            samesite=settings.COOKIE_SAMESITE,
            max_age=600,  # 10 minutes
        )

        return response

    except (UnsupportedOAuthProviderException, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e.message if hasattr(e, 'message') else e),
        )


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str,
    state: str,
    request: Request,
    auth_usecase: AuthUseCase = Depends(get_auth_usecase),
) -> RedirectResponse:
    """Handle OAuth callback.

    Validates state, exchanges code for token, creates JWT.
    Returns JWT token in HttpOnly cookie with CSRF token.
    """
    # Verify state matches cookie (CSRF protection)
    cookie_state = request.cookies.get("oauth_state")

    if not cookie_state or cookie_state != state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter",
        )

    try:
        # Handle OAuth callback and get JWT token pair
        token_pair = await auth_usecase.handle_callback_jwt(provider, code)

        # Redirect to frontend
        response = RedirectResponse(
            url=settings.FRONTEND_URL,
            status_code=status.HTTP_302_FOUND,
        )

        # Calculate max_age from expiry (12 hours in seconds)
        max_age = settings.JWT_EXPIRY_HOURS * 3600

        # Set JWT access token cookie (HttpOnly - not accessible by JS)
        response.set_cookie(
            key="access_token",
            value=token_pair.access_token,
            httponly=settings.JWT_HTTPONLY,
            secure=settings.effective_cookie_secure,
            samesite=settings.COOKIE_SAMESITE,
            max_age=max_age,
        )

        # Set CSRF token cookie (readable by JS for header)
        response.set_cookie(
            key="csrf_token",
            value=token_pair.csrf_token,
            httponly=False,  # Must be readable by JavaScript
            secure=settings.effective_cookie_secure,
            samesite="strict",
            max_age=max_age,
        )

        # Delete oauth_state cookie
        response.delete_cookie("oauth_state")

        return response

    except (UnsupportedOAuthProviderException, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e.message if hasattr(e, 'message') else e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth callback failed: {str(e)}",
        )


@router.get("/{provider}/callback/session")
async def oauth_callback_session(
    provider: str,
    code: str,
    state: str,
    request: Request,
    auth_usecase: AuthUseCase = Depends(get_auth_usecase),
) -> RedirectResponse:
    """Handle OAuth callback (legacy session-based).

    Validates state, exchanges code for token, creates JWT.
    Returns JWT token in HttpOnly cookie with CSRF token.
    """
    # Verify state matches cookie (CSRF protection)
    cookie_state = request.cookies.get("oauth_state")

    if not cookie_state or cookie_state != state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter",
        )

    try:
        # Handle OAuth callback (legacy session method)
        session, csrf_token = await auth_usecase.handle_callback(provider, code)

        # Redirect to frontend
        response = RedirectResponse(
            url=settings.FRONTEND_URL,
            status_code=status.HTTP_302_FOUND,
        )

        # Set session cookie (HttpOnly - not accessible by JS)
        response.set_cookie(
            key="session_id",
            value=session.session_id,
            httponly=True,
            secure=settings.effective_cookie_secure,
            samesite=settings.COOKIE_SAMESITE,
            max_age=settings.SESSION_TTL_SECONDS,
        )

        # Set CSRF token cookie (readable by JS for header)
        response.set_cookie(
            key="csrf_token",
            value=csrf_token,
            httponly=False,  # Must be readable by JavaScript
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            max_age=settings.SESSION_TTL_SECONDS,
        )

        # Delete oauth_state cookie
        response.delete_cookie("oauth_state")

        return response

    except UnsupportedOAuthProviderException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e.message),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth callback failed: {str(e)}",
        )


@router.post("/refresh")
async def refresh_token(
    response: Response,
    auth_usecase: AuthUseCase = Depends(get_auth_usecase),
    jwt_payload: TokenPayload = Depends(get_current_jwt_payload),
    request: Request = None,
) -> dict:
    """Refresh the JWT access token.

    Returns a new token pair if the current token is still valid.
    """
    # Get current token from cookie or header
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No token provided",
        )

    # Refresh the token
    new_token_pair = auth_usecase.refresh_jwt(token)

    if not new_token_pair:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed",
        )

    # Calculate max_age from expiry (12 hours in seconds)
    max_age = settings.JWT_EXPIRY_HOURS * 3600

    # Set new JWT access token cookie
    response.set_cookie(
        key="access_token",
        value=new_token_pair.access_token,
        httponly=settings.JWT_HTTPONLY,
        secure=settings.effective_cookie_secure,
        samesite=settings.COOKIE_SAMESITE,
        max_age=max_age,
    )

    # Set new CSRF token cookie
    response.set_cookie(
        key="csrf_token",
        value=new_token_pair.csrf_token,
        httponly=False,
        secure=settings.effective_cookie_secure,
        samesite="strict",
        max_age=max_age,
    )

    return {
        "message": "Token refreshed successfully",
        "expires_at": new_token_pair.expires_at.isoformat(),
    }
