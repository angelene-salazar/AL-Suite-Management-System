# database.py — optimized, clearer, safer
import sqlite3
from pathlib import Path
import csv
from datetime import datetime
from contextlib import contextmanager
from typing import Iterable, List, Optional, Any, Dict

DB_PATH = Path(__file__).parent / "resort.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_conn():
    """c"""
    conn = sqlite3.connect(
        DB_PATH,
        timeout=5,
        detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
    )
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Initialize database schema and seed default rows if missing."""
    with get_conn() as conn:
        c = conn.cursor()
        # users
        c.execute(
            """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            salt TEXT,
            password_hash TEXT,
            is_admin INTEGER DEFAULT 0
        );
        """
        )

        # bookings
        c.execute(
            """
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guest_name TEXT NOT NULL,
            booking_date TEXT NOT NULL,
            adults INTEGER NOT NULL,
            children INTEGER NOT NULL,
            guest_count INTEGER NOT NULL,
            package TEXT NOT NULL,
            table_id TEXT,
            room_id TEXT,
            table_fee REAL NOT NULL,
            room_fee REAL NOT NULL,
            entrance_fee REAL NOT NULL DEFAULT 0,
            total_amount REAL NOT NULL,
            amount_paid REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'checked-in',
            checkin_time TEXT,
            updated_at TEXT
        );
        """
        )

        # tables
        c.execute(
            """
        CREATE TABLE IF NOT EXISTS tables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            capacity INTEGER,
            price REAL,
            status TEXT DEFAULT 'available'
        );
        """
        )

        # rooms
        c.execute(
            """
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            capacity INTEGER,
            price REAL,
            status TEXT DEFAULT 'available'
        );
        """
        )

        conn.commit()

        # seed admin if none
        c.execute("SELECT COUNT(*) FROM users")
        if c.fetchone()[0] == 0:
            import utils

            salt, ph = utils.hash_password("Lresort123")
            c.execute(
                "INSERT INTO users (username, salt, password_hash, is_admin) VALUES (?, ?, ?, ?)",
                ("admin", salt, ph, 1),
            )
            conn.commit()

        # seed tables
        c.execute("SELECT COUNT(*) FROM tables")
        if c.fetchone()[0] == 0:
            rows = []
            for i in range(1, 9):
                rows.append((f"Table {i}", 5, 300))
            for i in range(9, 12):
                rows.append((f"Family Table {i-8}", 10, 800))
            c.executemany("INSERT INTO tables (name, capacity, price) VALUES (?, ?, ?)", rows)
            conn.commit()

        # seed rooms
        c.execute("SELECT COUNT(*) FROM rooms")
        if c.fetchone()[0] == 0:
            rooms = [
                ("Standard Room A", 2, 800),
                ("Standard Room B", 2, 800),
                ("Family Room A", 6, 1800),
                ("Family Room B", 8, 2200),
                ("Barkada Room", 12, 3500),
                ("Dorm Room", 20, 6000),
            ]
            c.executemany("INSERT INTO rooms (name, capacity, price) VALUES (?, ?, ?)", rooms)
            conn.commit()


# ----------------------
# Availability helpers
# ----------------------


def _row_has_id_in_col(row_value: Optional[str], check_id: int) -> bool:
    """Check whether a comma-separated string column contains a particular id."""
    if not row_value:
        return False
    parts = [p for p in row_value.split(",") if p.strip()]
    return str(check_id) in parts


def is_table_booked(table_id: Any, date: str) -> bool:
    """
    table_id can be int, str with commas, or list/tuple of ints.
    Returns True if any of the provided table ids has an existing checked-in booking for the date.
    """
    if not table_id:
        return False

    def ids_from(x):
        if isinstance(x, (list, tuple)):
            return [int(i) for i in x]
        if isinstance(x, int):
            return [x]
        if isinstance(x, str):
            return [int(p) for p in x.split(",") if p.strip()]
        return []

    ids = ids_from(table_id)
    if not ids:
        return False

    with get_conn() as conn:
        c = conn.cursor()
        for tid in ids:
            c.execute(
                "SELECT 1 FROM bookings WHERE booking_date=? AND instr(','||IFNULL(table_id,'')||',', ','||?||',')>0 AND status='checked-in' LIMIT 1",
                (date, str(tid)),
            )
            if c.fetchone():
                return True
    return False


def is_room_booked(room_id: Any, date: str) -> bool:
    """Same semantics as is_table_booked for rooms."""
    if not room_id:
        return False

    def ids_from(x):
        if isinstance(x, (list, tuple)):
            return [int(i) for i in x]
        if isinstance(x, int):
            return [x]
        if isinstance(x, str):
            return [int(p) for p in x.split(",") if p.strip()]
        return []

    ids = ids_from(room_id)
    if not ids:
        return False

    with get_conn() as conn:
        c = conn.cursor()
        for rid in ids:
            c.execute(
                "SELECT 1 FROM bookings WHERE booking_date=? AND instr(','||IFNULL(room_id,'')||',', ','||?||',')>0 AND status='checked-in' LIMIT 1",
                (date, str(rid)),
            )
            if c.fetchone():
                return True
    return False


# ----------------------
# Users
# ----------------------


def find_user(username: str) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        return c.fetchone()


def create_user(username: str, salt: str, password_hash: str, is_admin: int = 0) -> None:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO users (username, salt, password_hash, is_admin) VALUES (?, ?, ?, ?)",
            (username, salt, password_hash, is_admin),
        )
        conn.commit()


# Table / Room helpers

def _list_table_rows(table: str) -> List[sqlite3.Row]:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(f"SELECT * FROM {table} ORDER BY capacity, id")
        return c.fetchall()


def list_tables():
    return _list_table_rows("tables")


def list_rooms():
    return _list_table_rows("rooms")


def _set_status(table: str, id_or_list: Any, status: str) -> None:
    if not id_or_list:
        return
    if isinstance(id_or_list, str) and "," in id_or_list:
        ids = [int(x) for x in id_or_list.split(",") if x.strip()]
    elif isinstance(id_or_list, (list, tuple)):
        ids = [int(x) for x in id_or_list]
    else:
        ids = [int(id_or_list)]
    with get_conn() as conn:
        c = conn.cursor()
        for i in ids:
            c.execute(f"UPDATE {table} SET status=? WHERE id=?", (status, i))
        conn.commit()


def occupy_table(id_or_list: Any):
    _set_status("tables", id_or_list, "occupied")


def free_table(id_or_list: Any):
    _set_status("tables", id_or_list, "available")


def occupy_room(id_or_list: Any):
    _set_status("rooms", id_or_list, "occupied")


def free_room(id_or_list: Any):
    _set_status("rooms", id_or_list, "available")


# BOOKINGS (atomic)
def _norm_ids(x: Any) -> Optional[str]:
    if not x:
        return None
    if isinstance(x, str):
        return x
    if isinstance(x, int):
        return str(x)
    if isinstance(x, (list, tuple)):
        return ",".join(str(int(i)) for i in x)
    return str(x)


def _to_list(x: Any) -> List[int]:
    if not x:
        return []
    if isinstance(x, str):
        return [int(i) for i in x.split(",") if i.strip()]
    if isinstance(x, (list, tuple)):
        return [int(i) for i in x]
    return [int(x)]


def create_booking(
    guest_name: str,
    booking_date: str,
    adults: int,
    children: int,
    package: str,
    table_id: Any,
    room_id: Any,
    table_fee: float,
    room_fee: float,
    entrance_fee: float,
    total_amount: float,
    amount_paid: float,
) -> None:
    """Insert booking and mark associated tables/rooms as occupied in a single transaction."""
    guest_count = (adults or 0) + (children or 0)
    table_s = _norm_ids(table_id)
    room_s = _norm_ids(room_id)

    now = datetime.now().isoformat()
    checkin_time = datetime.now().strftime("%H:%M:%S")

    with get_conn() as conn:
        c = conn.cursor()

        c.execute(
            """
            INSERT INTO bookings
            (guest_name, booking_date, adults, children, guest_count,
             package, table_id, room_id, table_fee, room_fee,
             entrance_fee, total_amount, amount_paid,
             status, checkin_time, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'checked-in', ?, ?)
            """,
            (
                guest_name,
                booking_date,
                adults,
                children,
                guest_count,
                package,
                table_s,
                room_s,
                table_fee,
                room_fee,
                entrance_fee,
                total_amount,
                amount_paid,
                checkin_time,   # NEW
                now             # updated_at
            ),
        )

        # mark tables occupied
        for tid in _to_list(table_s):
            c.execute("UPDATE tables SET status='occupied' WHERE id=?", (tid,))

        # mark rooms occupied
        for rid in _to_list(room_s):
            c.execute("UPDATE rooms SET status='occupied' WHERE id=?", (rid,))

        conn.commit()




# Fetch bookings
def fetch_bookings_by_date(date: str):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM bookings WHERE booking_date=? ORDER BY id", (date,))
        return c.fetchall()


def fetch_bookings_range(dfrom: str, dto: str):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT * FROM bookings WHERE booking_date BETWEEN ? AND ? ORDER BY booking_date, id",
            (dfrom, dto),
        )
        return c.fetchall()



# Checkout / Cancel / Update / Payment

def checkout_booking(bid: int):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE bookings SET status='checked-out' WHERE id=?", (bid,))
        conn.commit()


def cancel_booking(bid: int):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE bookings SET status='cancelled' WHERE id=?", (bid,))
        conn.commit()


def update_booking(bid: int, **kwargs):
    if not kwargs:
        return
    with get_conn() as conn:
        c = conn.cursor()
        fields = ", ".join(f"{k}=?" for k in kwargs)
        values = list(kwargs.values())
        values.append(bid)
        c.execute(f"UPDATE bookings SET {fields} WHERE id=?", values)
        conn.commit()


def set_payment(bid: int, amount: float):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE bookings SET amount_paid = amount_paid + ? WHERE id=?", (amount, bid))
        conn.commit()


# Export helpers
def export_bookings_csv(rows: Iterable[Dict[str, Any]], path: str):
    """
    rows: iterable of sqlite3.Row or dict-like objects with keys used below.
    path: filesystem path to write to.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "id",
                "guest_name",
                "booking_date",
                "adults",
                "children",
                "guest_count",
                "package",
                "table_id",
                "room_id",
                "total_amount",
                "amount_paid",
                "status",
            ]
        )
        for r in rows:
            # support sqlite Row or dict
            try:
                get = lambda k: r[k]
            except Exception:
                get = lambda k: r.get(k)
            w.writerow(
                [
                    get("id"),
                    get("guest_name"),
                    get("booking_date"),
                    get("adults"),
                    get("children"),
                    get("guest_count"),
                    get("package"),
                    get("table_id"),
                    get("room_id"),
                    get("total_amount"),
                    get("amount_paid"),
                    get("status"),
                ]
            )
