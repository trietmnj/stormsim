"""
On-demand tide fetching for the hydrograph manipulator.

The manipulator reads tides only inside each storm's own date window, but used
to pre-fetch every day between the first and last year of the lifecycle. These
cover what that change has to get right:

  - a window resolves to the same values the whole-span fetch would have given
  - only the chunks a storm actually touches are requested
  - a storm crossing a chunk boundary gets both chunks, in order
  - two storms in one chunk share a single request
  - an empty NOAA response raises instead of silently dropping tides
"""
from datetime import datetime, timedelta

import pytest

from stormsim.noaa_py import tides
from stormsim.noaa_py.data_query import filter_tide_data

STATION = "8443970"
ANCHOR = datetime(2033, 1, 1)


def _synthetic_predictions(st_date, ed_date, interval_minutes=60):
    """Stand in for NOAA: one record per step, value encodes the timestamp."""
    start = datetime.strptime(st_date, "%Y%m%d")
    end = datetime.strptime(ed_date, "%Y%m%d").replace(hour=23, minute=59)
    out = []
    t = start
    while t <= end:
        out.append({"t": t.strftime("%Y-%m-%d %H:%M"), "v": f"{t.timestamp():.0f}"})
        t += timedelta(minutes=interval_minutes)
    return out


@pytest.fixture
def recorded_fetch(monkeypatch):
    """Replace the network call and record every window requested."""
    calls = []

    def fake_fetch(station, st_date, ed_date, interval, datum):
        calls.append((st_date, ed_date))
        return _synthetic_predictions(st_date, ed_date)

    monkeypatch.setattr(tides, "_fetch_prediction_chunk", fake_fetch)
    return calls


def _cache(chunk_days=30):
    return tides.TidalPredictionCache(
        {"station": STATION, "start_date": "20330101", "end_date": "20421231",
         "interval": "h", "datum": "MSL"},
        chunk_days=chunk_days,
    )


def test_window_matches_a_whole_span_fetch(recorded_fetch):
    """The values a storm sees must not change because of how they were fetched."""
    storm_start = datetime(2033, 2, 10, 6)
    storm_end = datetime(2033, 2, 12, 18)

    cache = _cache()
    windowed = filter_tide_data(cache.get_window(storm_start, storm_end), storm_start, storm_end)

    whole_span = tides._format_predictions(_synthetic_predictions("20330101", "20330630"))
    expected = filter_tide_data(whole_span, storm_start, storm_end)

    assert windowed == expected
    assert len(windowed[0]) > 0


def test_only_touched_chunks_are_fetched(recorded_fetch):
    cache = _cache()
    # Day 40 of the lifecycle lands in the second 30-day chunk.
    cache.get_window(datetime(2033, 2, 10), datetime(2033, 2, 11))

    assert recorded_fetch == [("20330131", "20330301")]


def test_storm_crossing_a_chunk_boundary_gets_both_chunks(recorded_fetch):
    cache = _cache()
    # 20330131 is the first day of chunk 1, so this storm straddles chunks 0 and 1.
    times = cache.get_window(datetime(2033, 1, 30, 12), datetime(2033, 2, 1, 12))["time"]

    assert len(recorded_fetch) == 2
    assert times == sorted(times), "merged chunks must stay in chronological order"


def test_storms_in_the_same_chunk_share_one_request(recorded_fetch):
    cache = _cache()
    cache.get_window(datetime(2033, 1, 5), datetime(2033, 1, 6))
    cache.get_window(datetime(2033, 1, 20), datetime(2033, 1, 21))

    assert len(recorded_fetch) == 1
    assert cache.request_count == 1


def test_sparse_storms_cost_far_fewer_requests_than_the_span(recorded_fetch):
    """The point of the change: a 10 year lifecycle with a handful of storms."""
    cache = _cache()
    for year in range(2033, 2043):
        cache.get_window(datetime(year, 6, 1), datetime(year, 6, 3))

    # One chunk per storm, versus ~122 to blanket 2033-2042 at 30 days a chunk.
    assert cache.request_count == 10


def test_empty_noaa_response_raises_rather_than_dropping_tides(monkeypatch):
    """
    NOAA answers an over-long window with HTTP 200 and no predictions. Silently
    continuing would produce water levels missing their tidal component, which
    looks like a successful run.
    """
    monkeypatch.setattr(tides, "_fetch_url", lambda *a, **k: {"predictions": []})

    with pytest.raises(RuntimeError, match="no predictions"):
        tides._fetch_prediction_chunk(STATION, "20330101", "20330131", "1", "MSL")


def test_failed_request_raises_instead_of_crashing_later(monkeypatch):
    """_fetch_url returns None once retries are exhausted."""
    monkeypatch.setattr(tides, "_fetch_url", lambda *a, **k: None)

    with pytest.raises(RuntimeError, match="failed"):
        tides._fetch_prediction_chunk(STATION, "20330101", "20330131", "1", "MSL")
