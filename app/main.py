import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.config import async_session, init_db
from app.store.sqlite import SQLiteTransferStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB and store on startup."""
    logger.info("Initializing database...")
    await init_db()
    app.state.store = SQLiteTransferStore(async_session)
    logger.info("Application ready")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Station Transfer Service",
    description="Ingests station transfer events and provides per-station reconciliation summaries.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)