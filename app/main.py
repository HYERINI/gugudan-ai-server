"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.conversation.adapter.input.web.conversation_router import conversation_router
from app.simulation.adapter.input.web.simulation_router import simulation_router

# Load environment variables first
load_dotenv()

from app.auth.adapter.input.web.router import router as auth_router
from app.account.adapter.input.web.account_router import router as account_router
from app.ml.adapter.input.web.ml_router import ml_router
from app.inquiry.adapter.input.web.inquiry_router import router as inquiry_router
from app.faq.adapter.input.web.faq_router import router as faq_router

from app.account.infrastructure.orm.account_model import AccountModel  # noqa: F401
from app.inquiry.infrastructure.orm.inquiry_model import InquiryModel  # noqa: F401
from app.inquiry.infrastructure.orm.inquiry_reply_model import InquiryReplyModel  # noqa: F401
from app.faq.infrastructure.orm.faq_model import FAQModel  # noqa: F401
from app.config.database.session import Base, engine
from app.config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler.

    Startup: Initialize database tables.
    Shutdown: Cleanup resources if needed.
    """
    # Startup
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown (cleanup if needed)


app = FastAPI(
    title="Gugudan AI Server",
    description="AI Counselor for emotional problems between couples",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.CORS_ALLOWED_FRONTEND_URL],
    allow_credentials=True,  # Required for cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(conversation_router, prefix="/conversation")
app.include_router(simulation_router, prefix="/simulation")
app.include_router(account_router, prefix="/api/v1")
app.include_router(ml_router, prefix="/ml")
app.include_router(inquiry_router, prefix="/api/v1")
app.include_router(faq_router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.APP_HOST,
        port=settings.APP_PORT,
    )
