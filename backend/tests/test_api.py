from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health_and_snapshot():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["snapshotId"]


def test_actuals_are_opt_in():
    response = client.get("/api/decision?day=2026-01-15&cutoff=10:00")
    assert response.status_code == 200
    data = response.json()
    assert len(data["rows"]) == 48
    assert all(r["actual"] is None for r in data["rows"])
    assert all(r["publishTime"] <= data["cutoff"] for r in data["rows"] if r["publishTime"])


def test_invalid_filters():
    for url in ["/api/decision?day=2026-02-01", "/api/decision?cutoff=25:00", "/api/decision?day=invalid", "/api/accuracy?start=2026-01-20&end=2026-01-01"]:
        assert client.get(url).status_code == 422


def test_month_coverage_and_aggregation():
    response = client.get("/api/accuracy")
    data = response.json()
    assert response.status_code == 200
    assert data["metrics"]["expected"] == 1488
    assert data["days"][-1]["deliveryDate"] == "2026-02-01"
    pairs = [r for r in data["rows"] if r["error"] is not None]
    assert data["metrics"]["mae"] == sum(abs(r["error"]) for r in pairs) / len(pairs)


def test_earliest_cutoff_has_no_future_publications():
    data = client.get("/api/decision?day=2026-01-01&cutoff=00:00").json()
    assert all(r["publishTime"] <= data["cutoff"] for r in data["rows"] if r["publishTime"])


def test_spa_fallback_serves_html():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    deep_link = client.get("/decision")
    assert deep_link.status_code == 200
    assert "text/html" in deep_link.headers.get("content-type", "")


def test_single_day_accuracy():
    response = client.get("/api/accuracy?start=2026-01-15&end=2026-01-15&cutoff=10:00")
    assert response.status_code == 200
    data = response.json()
    assert len(data["days"]) == 1
    assert data["metrics"]["expected"] == 48
