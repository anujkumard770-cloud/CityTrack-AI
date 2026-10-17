"""
Backend tests for CityTrack AI.
Run with: pytest tests/ -v
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.database.session import Base, get_db
from app.core.config import settings

# ── Use in-memory SQLite for tests ────────────────────────────────────
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ── Health ────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ── Camera CRUD ───────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_create_camera(client):
    payload = {
        "camera_code": "TEST-CAM-01",
        "name": "Test Camera One",
        "location_name": "Test Road, Test City",
        "latitude": 28.61,
        "longitude": 77.20,
    }
    r = await client.post("/api/cameras", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["camera_code"] == "TEST-CAM-01"
    assert data["id"] > 0
    return data["id"]


@pytest.mark.asyncio
async def test_duplicate_camera_code(client):
    payload = {
        "camera_code": "TEST-DUP-01",
        "name": "Dup Camera",
        "location_name": "Somewhere",
        "latitude": 28.0,
        "longitude": 77.0,
    }
    r1 = await client.post("/api/cameras", json=payload)
    assert r1.status_code == 201
    r2 = await client.post("/api/cameras", json=payload)
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_list_cameras(client):
    r = await client.get("/api/cameras")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_get_camera_not_found(client):
    r = await client.get("/api/cameras/999999")
    assert r.status_code == 404


# ── Video Upload Validation ───────────────────────────────────────────
@pytest.mark.asyncio
async def test_upload_bad_extension(client):
    # First create a camera to reference
    cam_r = await client.post("/api/cameras", json={
        "camera_code": "TEST-CAM-UP",
        "name": "Upload Test Cam",
        "location_name": "Test",
        "latitude": 28.0,
        "longitude": 77.0,
    })
    cam_id = cam_r.json()["id"]
    files = {"file": ("bad_file.txt", b"fake content", "text/plain")}
    r = await client.post("/api/videos/upload", data={"camera_id": cam_id}, files=files)
    assert r.status_code == 422


# ── Vehicle Search ────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_search_returns_empty_without_data(client):
    r = await client.get("/api/vehicles/search?plate_query=DL01AB9999")
    assert r.status_code == 200
    body = r.json()
    assert "results" in body
    assert isinstance(body["results"], list)


# ── Analytics ─────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_analytics_summary(client):
    r = await client.get("/api/analytics/summary")
    assert r.status_code == 200
    data = r.json()
    assert "total_detections" in data
    assert "unique_tracked_vehicles" in data
    assert "cross_camera_journeys" in data


@pytest.mark.asyncio
async def test_analytics_traffic(client):
    r = await client.get("/api/analytics/traffic?hours=24")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_analytics_cameras(client):
    r = await client.get("/api/analytics/cameras")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ── Trajectory not found ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_trajectory_not_found(client):
    r = await client.get("/api/vehicles/999999/trajectory")
    assert r.status_code == 404


# ── Plate normalization/validation ───────────────────────────────────
def test_plate_normalize_validate():
    from app.vision.processor import normalize_plate, validate_plate
    assert normalize_plate("DL 01 AB 1234") == "DL01AB1234"
    assert normalize_plate("mh-12-xy-9010") == "MH12XY9010"
    valid, state = validate_plate("DL01AB1234")
    assert valid is True
    assert state == "DL"
    valid2, _ = validate_plate("ZZZZZZZ")
    assert valid2 is False
    valid3, _ = validate_plate("")
    assert valid3 is False
