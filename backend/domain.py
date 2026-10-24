"""Pure decision-time selection and accuracy logic. All power values are MW."""
import math
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

LONDON = ZoneInfo("Europe/London")


def parse(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("Timezone required")
    return dt.astimezone(timezone.utc)


def iso(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def select_latest(records, cutoff=None):
    eligible = [r for r in records if cutoff is None or parse(r["publishTime"]) <= cutoff]
    if not eligible:
        return None, "missing"
    latest = max(parse(r["publishTime"]) for r in eligible)
    selected = [r for r in eligible if parse(r["publishTime"]) == latest]
    if len({r["generation"] for r in selected}) > 1:
        return None, "conflict"
    return selected[0], "available"


def index_records(records):
    index = {}
    for row in records:
        index.setdefault(iso(parse(row["startTime"])), []).append(row)
    return index


def metrics(rows):
    pairs = [r for r in rows if r["forecast"] is not None and r["actual"] is not None]
    errors = [r["forecast"] - r["actual"] for r in pairs]
    n = len(pairs)
    return {
        "expected": len(rows), "forecastCount": sum(r["forecast"] is not None for r in rows),
        "actualCount": sum(r["actual"] is not None for r in rows), "matchedCount": n,
        "coverage": 100 * n / len(rows) if rows else 0,
        "mae": sum(abs(e) for e in errors) / n if n else None,
        "rmse": math.sqrt(sum(e * e for e in errors) / n) if n else None,
        "bias": sum(errors) / n if n else None,
        "overforecastFrequency": 100 * sum(e > 0 for e in errors) / n if n else None,
        "matchedForecastEnergy": sum(r["forecast"] * .5 for r in pairs) if n else None,
        "matchedActualEnergy": sum(r["actual"] * .5 for r in pairs) if n else None,
        "shortfallEnergy": sum(max(e, 0) * .5 for e in errors) if n else None,
    }


def decision(day, cutoff, forecasts, actuals, include_actuals=False):
    cutoff_at = datetime.combine(day, time.fromisoformat(cutoff), LONDON).astimezone(timezone.utc)
    delivery = day + timedelta(days=1)
    start = datetime.combine(delivery, time.min, LONDON).astimezone(timezone.utc)
    end = datetime.combine(delivery + timedelta(days=1), time.min, LONDON).astimezone(timezone.utc)
    rows = []
    target = start
    while target < end:
        key = iso(target)
        forecast, status = select_latest(forecasts.get(key, []), cutoff_at)
        actual, actual_status = select_latest(actuals.get(key, [])) if include_actuals else (None, "hidden")
        f = forecast["generation"] if forecast else None
        a = actual["generation"] if actual else None
        rows.append({"startTime": key, "forecast": f, "actual": a,
                     "publishTime": forecast["publishTime"] if forecast else None,
                     "actualPublishTime": actual["publishTime"] if actual else None,
                     "forecastStatus": status, "actualStatus": actual_status,
                     "error": f - a if f is not None and a is not None else None})
        target += timedelta(minutes=30)
    available = [r for r in rows if r["forecast"] is not None]
    publications = sorted({r["publishTime"] for r in available})
    return {"decisionDate": str(day), "deliveryDate": str(delivery), "cutoff": iso(cutoff_at),
            "rows": rows, "metrics": metrics(rows) if include_actuals else None,
            "summary": {"expected": len(rows), "forecastCount": len(available),
                        "meanForecast": sum(r["forecast"] for r in available) / len(available) if available else None,
                        "peakForecast": max((r["forecast"] for r in available), default=None),
                        "forecastEnergy": sum(r["forecast"] * .5 for r in available) if available else None,
                        "publications": publications,
                        "oldestAgeHours": (cutoff_at - parse(publications[0])).total_seconds() / 3600 if publications else None,
                        "newestAgeHours": (cutoff_at - parse(publications[-1])).total_seconds() / 3600 if publications else None}}
