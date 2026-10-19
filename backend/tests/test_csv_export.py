import csv
import io
from datetime import UTC, date, datetime, time
from types import SimpleNamespace

from app.bookings.service import export_bookings_csv
from app.core.csvutil import csv_cell
from app.trains.service import export_trains_csv


def _rows(text: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(text)))


def test_csv_cell_neutralizes_formula_prefixes():
    for value in ("=1+1", "+SUM(A1)", "-2+3", "@cmd", "\t=1", "\r=1", "\n=1"):
        assert csv_cell(value) == "'" + value
    assert csv_cell("Acme Rail") == "Acme Rail"
    assert csv_cell(42) == 42


def test_train_export_escapes_user_controlled_cells():
    train = SimpleNamespace(
        number="TR-1",
        name="=HYPERLINK(\"http://example.test\")",
        train_type="express",
        source="@source",
        destination="Normal",
        departure_time=time(8, 0),
        arrival_time=time(12, 0),
        days_of_week=[0, 1],
        total_seats=100,
        fare_cents=5000,
        currency="USD",
        is_active=True,
    )
    rows = _rows(export_trains_csv([train]))
    assert rows[0][0] == "number"
    assert rows[1][1] == "'=HYPERLINK(\"http://example.test\")"
    assert rows[1][3] == "'@source"
    assert rows[1][4] == "Normal"


def test_booking_export_escapes_user_controlled_cells():
    train = SimpleNamespace(number="TR-1", name="+Danger")
    booking = SimpleNamespace(
        pnr="ABC123",
        travel_date=date(2026, 11, 1),
        contact_name="=1+1",
        contact_email="@evil.test",
        contact_phone="-123",
        seats=2,
        status="confirmed",
        total_fare_cents=10000,
        currency="USD",
        channel="web",
        refund_status="none",
        created_at=datetime(2026, 10, 1, tzinfo=UTC),
    )
    rows = _rows(export_bookings_csv([(booking, train)]))
    assert rows[0][0] == "pnr"
    assert rows[1][2] == "'+Danger"
    assert rows[1][4] == "'=1+1"
    assert rows[1][5] == "'@evil.test"
    assert rows[1][6] == "'-123"
