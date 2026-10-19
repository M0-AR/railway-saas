"""Property-based tests for the small pure helpers that guard invariants.

derandomize=True keeps the suite reproducible (each failing example stays a
counterexample forever); 50 examples per property keeps CI fast while still
pinning the edges Hypothesis is good at finding (zeros, negatives, extremes).
"""

from hypothesis import given
from hypothesis import settings as hypothesis_settings
from hypothesis import strategies as st

from app.bookings.service import PNR_ALPHABET, PNR_LENGTH, _generate_pnr
from app.core.csvutil import csv_cell
from app.core.pagination import clamp_page
from app.identity.schemas import RESERVED_SLUGS, SLUG_RE, normalize_slug
from app.trains.service import _parse_days, _parse_fare_cents

PROPERTY = hypothesis_settings(derandomize=True, max_examples=50, deadline=None)

DANGEROUS_PREFIXES = ("=", "+", "-", "@", "\t", "\r", "\n")


@PROPERTY
@given(page=st.integers(-10_000, 10_000), page_size=st.integers(-10_000, 10_000))
def test_clamp_page_always_returns_a_sound_window(page: int, page_size: int):
    clamped_page, clamped_size, offset = clamp_page(page, page_size)
    assert clamped_page >= 1
    assert 1 <= clamped_size <= 100
    assert offset == (clamped_page - 1) * clamped_size


@PROPERTY
@given(value=st.from_regex(SLUG_RE.pattern, fullmatch=True))
def test_normalize_slug_is_idempotent_for_valid_slugs(value: str):
    if value in RESERVED_SLUGS:
        return
    assert normalize_slug(value) == value


@PROPERTY
@given(value=st.from_regex(SLUG_RE.pattern, fullmatch=True))
def test_normalize_slug_lowercases_and_strips_arbitrary_input(value: str):
    if value in RESERVED_SLUGS:
        return
    noisy = f"  {value.upper()}  "
    assert normalize_slug(noisy) == value


@PROPERTY
@given(value=st.text())
def test_csv_cell_is_inert_or_unchanged(value: str):
    result = csv_cell(value)
    if value.startswith(DANGEROUS_PREFIXES):
        assert result == "'" + value
    else:
        assert result == value


@PROPERTY
@given(amount=st.decimals(min_value=0, max_value=1_000_000, places=2))
def test_parse_fare_cents_round_trips_two_decimal_amounts(amount):
    assert _parse_fare_cents(str(amount)) == int(amount * 100)


@PROPERTY
@given(days=st.sets(st.integers(min_value=1, max_value=7), min_size=1))
def test_parse_days_normalizes_to_sorted_unique_numbers(days: set[int]):
    raw = ",".join(str(day) for day in sorted(days))
    assert _parse_days(raw) == sorted(days)


def test_parse_days_defaults_and_rejects_out_of_range():
    assert _parse_days(None) == [1, 2, 3, 4, 5, 6, 7]
    assert _parse_days("  ") == [1, 2, 3, 4, 5, 6, 7]
    for bad in ("0", "8", "1,8", "abc"):
        try:
            _parse_days(bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad!r} should have been rejected")


@PROPERTY
@given(repeats=st.integers(min_value=1, max_value=25))
def test_pnrs_stay_inside_the_declared_alphabet(repeats: int):
    for _ in range(repeats):
        pnr = _generate_pnr()
        assert len(pnr) == PNR_LENGTH
        assert set(pnr) <= set(PNR_ALPHABET)
