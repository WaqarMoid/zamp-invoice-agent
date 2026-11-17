import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.procurement import router as procurement_router
from app.config import get_settings
from app.db import Base, SessionLocal, engine
from app.seed import seed

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger("kestrel-ap")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Kestrel AP · Invoice desk API backend...")
    # Initialize database tables
    Base.metadata.create_all(bind=engine)
    # Seed data if unseeded
    with SessionLocal() as session:
        seed(session, force=False)
    yield
    logger.info("Shutting down Kestrel AP · Invoice desk API backend...")


app = FastAPI(
    title="Kestrel AP · Invoice desk",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration per docs/08
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Last-Event-ID", "Authorization"],
)

# Include routers
app.include_router(health_router)
app.include_router(procurement_router)


@app.get("/")
def root():
    return {
        "app": "Kestrel AP · Invoice desk",
        "health": "/api/health",
        "docs": "/docs",
    }
