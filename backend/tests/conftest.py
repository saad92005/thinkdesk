import os

# Must happen before any `app.*` import, since app.core.config.get_settings()
# is cached and app.database builds its engine at import time from it.
os.environ["DATABASE_URL"] = "postgresql+asyncpg://thinkdesk:thinkdesk@localhost:5432/thinkdesk_test"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.database import Base, engine, get_db
from app.main import app

TestSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# asyncpg connections are bound to the event loop that created them; with
# pytest-asyncio's default per-test loop, the session-scoped engine below
# would get reused across loops and break on Windows. pytest.ini pins both
# fixtures and tests to one session-scoped loop to match.


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_tables(setup_database):
    """Truncate everything between tests so they don't see each other's data."""
    yield
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


async def _override_get_db():
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client():
    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def second_client():
    """A second, independent cookie jar -- for tests simulating a
    different logged-in user against the same running app."""
    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


def _has_real_groq_key() -> bool:
    from app.core.config import get_settings

    key = get_settings().groq_api_key or ""
    return bool(key) and not key.startswith("test-")


def pytest_collection_modifyitems(config, items):
    # Tests marked live_llm make real Groq calls (they check that answers are
    # grounded in the uploaded documents). Without a real key -- e.g. in CI
    # when the GROQ_API_KEY secret isn't set -- skip them instead of failing.
    if _has_real_groq_key():
        return
    skip = pytest.mark.skip(reason="needs a real GROQ_API_KEY (live LLM test)")
    for item in items:
        if "live_llm" in item.keywords:
            item.add_marker(skip)
