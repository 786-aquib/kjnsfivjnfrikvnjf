"""Build the immutable January pilot snapshot from the two required Elexon APIs.

Run from the repository root: python -m backend.ingest
Raw responses are retained compressed; the published snapshot is replaced atomically.
"""
import gzip
import hashlib
import json
import math
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
BASE = "https://data.elexon.co.uk/bmrs/api/v1/datasets"


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timestamp has no timezone")
    return result.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def normalize(rows, dataset):
    """Preserve conflicting versions for conservative selection; remove exact duplicates."""
    output, seen = [], set()
    quality = Counter()
    for row in rows:
        if dataset == "FUELHH" and row.get("fuelType") != "WIND":
            quality["excluded_other_fuel"] += 1
            continue
        try:
            start, published = timestamp(row["startTime"]), timestamp(row["publishTime"])
            generation = row["generation"]
            dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            if isinstance(generation, bool) or not isinstance(generation, (int, float)):
                raise ValueError("Non-numeric generation")
            if not math.isfinite(generation) or generation < 0 or dt.minute not in (0, 30) or dt.second or dt.microsecond:
                raise ValueError("Invalid generation or interval")
            key = (start, published, generation)
            if key in seen:
                quality["exact_duplicates"] += 1
                continue
            seen.add(key)
            output.append({"startTime": start, "publishTime": published, "generation": generation})
        except (KeyError, TypeError, ValueError, AttributeError):
            quality["invalid_records"] += 1
    quality["accepted_records"] = len(output)
    return sorted(output, key=lambda r: (r["startTime"], r["publishTime"], r["generation"])), dict(quality)


def fetch(job):
    dataset, day = job
    if dataset == "WINDFOR":
        params = {"publishDateTimeFrom": f"{day}T00:00:00Z", "publishDateTimeTo": f"{day + timedelta(days=1)}T00:00:00Z"}
    else:
        params = {"settlementDateFrom": str(day), "settlementDateTo": str(day), "fuelType": "WIND"}
    for attempt in range(4):
        try:
            response = httpx.get(f"{BASE}/{dataset}/stream", params=params, timeout=60)
            response.raise_for_status()
            rows = response.json()
            if not isinstance(rows, list):
                raise ValueError("Expected a JSON array from Elexon")
            raw = response.content
            filename = f"{dataset}-{day}.json.gz"
            (DATA / "raw" / filename).write_bytes(gzip.compress(raw, mtime=0))
            return dataset, rows, {"file": f"raw/{filename}", "url": str(response.url), "retrievedAt": datetime.now(timezone.utc).isoformat(), "sha256": hashlib.sha256(raw).hexdigest(), "records": len(rows)}
        except (httpx.HTTPError, ValueError):
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def main():
    (DATA / "raw").mkdir(parents=True, exist_ok=True)
    jobs = [("WINDFOR", date(2025, 12, 29) + timedelta(days=i)) for i in range(34)]
    jobs += [("FUELHH", date(2026, 1, 2) + timedelta(days=i)) for i in range(31)]
    records = {"WINDFOR": [], "FUELHH": []}
    requests = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for dataset, rows, provenance in pool.map(fetch, jobs):
            records[dataset].extend(rows)
            requests.append(provenance)
            print(f"{provenance['file']}: {len(rows)} records", flush=True)
    forecasts, forecast_quality = normalize(records["WINDFOR"], "WINDFOR")
    actuals, actual_quality = normalize(records["FUELHH"], "FUELHH")
    # Publications outside January decisions cannot be selected; retain useful lookback.
    forecasts = [r for r in forecasts if "2026-01-02" <= r["startTime"] < "2026-02-02" and r["publishTime"] < "2026-02-01"]
    metadata = {
        "retrievedAt": datetime.now(timezone.utc).isoformat(),
        "sources": [f"{BASE}/FUELHH/stream", f"{BASE}/WINDFOR/stream"],
        "decisionFrom": "2026-01-01", "decisionTo": "2026-01-31",
        "deliveryFrom": "2026-01-02", "deliveryTo": "2026-02-01",
        "forecastRecords": len(forecasts), "actualRecords": len(actuals),
        "forecastMinuteCounts": dict(Counter(r["startTime"][14:16] for r in forecasts)),
        "quality": {"WINDFOR": forecast_quality, "FUELHH": actual_quality},
        "alignment": "Exact startTime only. Hourly WINDFOR leaves half-hour slots unmatched; no interpolation.",
        "actualPolicy": "Latest retrieved publication per startTime; conflicting values at that publication are excluded.",
    }
    payload = {"metadata": metadata, "forecasts": forecasts, "actuals": actuals}
    encoded = json.dumps(payload, separators=(",", ":")).encode()
    metadata["snapshotId"] = hashlib.sha256(encoded).hexdigest()[:12]
    temporary = DATA / "snapshot.tmp"
    temporary.write_text(json.dumps(payload, separators=(",", ":")))
    temporary.replace(DATA / "snapshot.json")
    (DATA / "manifest.json").write_text(json.dumps({"snapshotId": metadata["snapshotId"], "requests": requests}, indent=2))
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
