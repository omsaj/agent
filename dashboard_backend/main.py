from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.dashboard_routes import router as dashboard_router
from .config.settings import get_settings
from .services.llm_analyzer import LLMAnalyzer
from .services.threat_collector import ThreatCollector
from .utils.database import get_session_factory, init_db, shutdown

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("cyberscope.app")

settings = get_settings()
analyzer = LLMAnalyzer(settings)
collector = ThreatCollector(settings, analyzer)
_collection_task: asyncio.Task | None = None


@asynccontextmanager
def lifespan(app: FastAPI):
    global _collection_task
    await init_db()
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            await collector.run_collection(session)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Initial data collection failed: %s", exc)
    _collection_task = asyncio.create_task(collector.schedule_collection(session_factory))
    try:
        yield
    finally:
        if _collection_task:
            _collection_task.cancel()
            with suppress(asyncio.CancelledError):
                await _collection_task
        await shutdown()


app = FastAPI(title="CyberScope Dashboard API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def include_routes(application: FastAPI) -> None:
    application.include_router(dashboard_router)


include_routes(app)
