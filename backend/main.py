import json
import re
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.domain import decision, index_records, metrics

ROOT = Path(__file__).resolve().parents[1]
app = FastAPI(title="Gridbricks API", version="1.0.0")


@lru_cache(maxsize=1)
def snapshot():
    path = ROOT / "data/snapshot.json"
    if not path.exists():
        raise HTTPException(503, "Pilot data is unavailable. Run python -m backend.ingest and restart the server.")
    try:
        data = json.loads(path.read_text())
        return data["metadata"], index_records(data["forecasts"]), index_records(data["actuals"])
    except Exception as exc:
        raise HTTPException(503, f"Pilot data could not be loaded: {exc}")



def validate(day, cutoff):
    if not date(2026, 1, 1) <= day <= date(2026, 1, 31):
        raise HTTPException(422, "Decision dates must be within January 2026.")
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", cutoff):
        raise HTTPException(422, "Cutoff must be HH:MM in Europe/London.")


@app.get("/api/health")
def health():
    metadata, _, _ = snapshot()
    return {"status": "ok", "snapshotId": metadata["snapshotId"]}


@app.get("/api/metadata")
def metadata():
    return snapshot()[0]


@app.get("/api/decision")
def get_decision(day: date = Query(date(2026, 1, 15)), cutoff: str = "10:00", actuals: bool = False):
    validate(day, cutoff)
    meta, forecasts, observations = snapshot()
    return {**decision(day, cutoff, forecasts, observations, actuals), "snapshotId": meta["snapshotId"]}


@app.get("/api/accuracy")
def accuracy(start: date = Query(date(2026, 1, 1)), end: date = Query(date(2026, 1, 31)), cutoff: str = "10:00"):
    validate(start, cutoff)
    validate(end, cutoff)
    if start > end:
        raise HTTPException(422, "Start date must be on or before end date.")
    meta, forecasts, observations = snapshot()
    days, rows = [], []
    current = start
    while current <= end:
        result = decision(current, cutoff, forecasts, observations, True)
        days.append({"decisionDate": str(current), "deliveryDate": result["deliveryDate"], **result["metrics"]})
        rows.extend(result["rows"])
        current += timedelta(days=1)
    pairs = [r for r in rows if r["error"] is not None]
    return {"start": str(start), "end": str(end), "cutoff": cutoff, "snapshotId": meta["snapshotId"],
            "metrics": metrics(rows), "days": days, "rows": rows,
            "largestErrors": sorted(pairs, key=lambda r: abs(r["error"]), reverse=True)[:8]}


# The same Python process serves the production React build in Docker/Heroku.
DIST = ROOT / "frontend/dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str = ""):
        file_path = DIST / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(DIST / "index.html")

