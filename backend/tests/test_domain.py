from datetime import date

import pytest

from backend.domain import decision, index_records, metrics, parse, select_latest
from backend.ingest import normalize


def record(start="2026-01-02T00:00:00Z", published="2026-01-01T09:30:00Z", value=100):
    return {"startTime": start, "publishTime": published, "generation": value}


def test_latest_before_cutoff_and_inclusive_boundary():
    rows = [record(value=100), record(published="2026-01-01T10:00:00Z", value=120), record(published="2026-01-01T10:01:00Z", value=999)]
    selected, status = select_latest(rows, parse("2026-01-01T10:00:00Z"))
    assert selected["generation"] == 120
    assert status == "available"


def test_conflict_at_latest_publication_does_not_fall_back():
    rows = [record(published="2026-01-01T07:30:00Z", value=90), record(value=100), record(value=110)]
    assert select_latest(rows, parse("2026-01-01T10:00:00Z")) == (None, "conflict")


def test_later_only_forecast_is_missing():
    assert select_latest([record()], parse("2026-01-01T08:00:00Z")) == (None, "missing")


def test_hourly_source_never_fills_half_hour_and_actuals_hidden():
    forecasts = index_records([record()])
    actuals = index_records([record(value=80)])
    result = decision(date(2026, 1, 1), "10:00", forecasts, actuals)
    assert len(result["rows"]) == 48
    assert result["rows"][0]["forecast"] == 100
    assert result["rows"][1]["forecast"] is None
    assert result["rows"][0]["actual"] is None
    assert result["rows"][0]["actualPublishTime"] is None
    assert result["metrics"] is None


def test_month_boundary_and_mixed_vintages():
    rows = [record("2026-02-01T00:00:00Z", "2026-01-31T09:30:00Z"), record("2026-02-01T01:00:00Z", "2026-01-30T23:30:00Z")]
    result = decision(date(2026, 1, 31), "10:00", index_records(rows), {})
    assert result["deliveryDate"] == "2026-02-01"
    assert len(result["summary"]["publications"]) == 2
    assert result["rows"][-1]["startTime"] == "2026-02-01T23:30:00Z"


def test_offset_timestamps_are_normalized():
    rows = [record("2026-01-02T01:00:00+01:00", "2026-01-01T10:30:00+01:00")]
    result = decision(date(2026, 1, 1), "10:00", index_records(rows), {})
    assert result["rows"][0]["forecast"] == 100


def test_metrics_independent_hand_calculation():
    # Errors: +20, -10, 0. A zero actual is valid; the unmatched fourth slot is excluded.
    rows = [{"forecast": 100, "actual": 80}, {"forecast": 20, "actual": 30}, {"forecast": 0, "actual": 0}, {"forecast": None, "actual": 40}]
    result = metrics(rows)
    assert result["mae"] == 10
    assert result["rmse"] == pytest.approx((500 / 3) ** .5)
    assert result["bias"] == pytest.approx(10 / 3)
    assert result["overforecastFrequency"] == pytest.approx(100 / 3)
    assert result["coverage"] == 75
    assert result["shortfallEnergy"] == 10
    assert result["matchedForecastEnergy"] == 60
    assert result["matchedActualEnergy"] == 55


def test_zero_matches_unavailable():
    result = metrics([{"forecast": None, "actual": 100}])
    assert result["mae"] is None
    assert result["shortfallEnergy"] is None
    assert result["coverage"] == 0


def test_normalization_filters_invalid_and_other_fuels():
    good = {**record(), "fuelType": "WIND"}
    normalized, quality = normalize([good, good, {**good, "generation": -1}, {**good, "generation": "100"}, {**good, "fuelType": "GAS"}], "FUELHH")
    assert len(normalized) == 1
    assert quality["exact_duplicates"] == 1
    assert quality["invalid_records"] == 2
    assert quality["excluded_other_fuel"] == 1


def test_actuals_latest_revision_selected():
    original = record(value=90)
    revised = record(published="2026-01-03T00:00:00Z", value=80)
    result = decision(date(2026, 1, 1), "10:00", index_records([record()]), index_records([original, revised]), True)
    assert result["rows"][0]["actual"] == 80
    assert result["rows"][0]["error"] == 20
