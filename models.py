import database as db
from itertools import combinations
from typing import List, Optional


# user model
def find_user(username):
    return db.find_user(username)


def create_user(username, salt, pw_hash, is_admin=0):
    return db.create_user(username, salt, pw_hash, is_admin)


class TableModel:
    @staticmethod
    def list_available():
        return db.list_tables()

    @staticmethod
    def occupy(table_id):
        return db.occupy_table(table_id)

    @staticmethod
    def free(table_id):
        return db.free_table(table_id)

    @staticmethod
    def find_suitable(guest_count, date=None):
        # 1. Get all available tables
        rows = db.list_tables()

        # 2. Filter by date availability
        if date:
            rows = [r for r in rows if not db.is_table_booked(r["id"], date)]

        # 3. Filter: Capacity must be >= guest_count
        candidates = [r for r in rows if r["capacity"] >= guest_count]

        if candidates:
            # Sort by capacity (smallest fit first), then price
            candidates.sort(key=lambda x: (x["capacity"], x["price"]))
            return candidates[0]

        return None

    @staticmethod
    def find_tables_for(guest_count, date=None) -> List:
        rows = [r for r in db.list_tables() if r["status"] == "available"]
        if date:
            rows = [r for r in rows if not db.is_table_booked(r["id"], date)]
        if not rows:
            return []
        # greedy by capacity descending then price
        rows.sort(key=lambda x: (-x["capacity"], x["price"]))
        selected = []
        total = 0
        for r in rows:
            if total >= guest_count:
                break
            selected.append(r)
            total += r["capacity"]
        if total >= guest_count:
            return selected
        # combinatorial fallback (small sizes)
        max_comb = min(5, len(rows))
        for sz in range(1, max_comb + 1):
            for comb in combinations(rows, sz):
                if sum(r["capacity"] for r in comb) >= guest_count:
                    return list(comb)
        return []

    @staticmethod
    def is_table_booked(table_id, date):
        # reuse the low-level database function already implemented
        return db.is_table_booked(table_id, date)


class RoomModel:
    @staticmethod
    def list_available():
        return db.list_rooms()

    @staticmethod
    def occupy(room_id):
        return db.occupy_room(room_id)

    @staticmethod
    def free(room_id):
        return db.free_room(room_id)

    @staticmethod
    def find_suitable(guest_count, date=None):
        rows = db.list_rooms()
        if date:
            rows = [r for r in rows if not db.is_room_booked(r["id"], date)]

        candidates = [r for r in rows if r["capacity"] >= guest_count]

        if candidates:
            candidates.sort(key=lambda x: (x["capacity"], x["price"]))
            return candidates[0]

        return None

    @staticmethod
    def find_rooms_for(guest_count, date=None):
        rows = [r for r in db.list_rooms() if r["status"] == "available"]
        if date:
            rows = [r for r in rows if not db.is_room_booked(r["id"], date)]
        if not rows:
            return []
        rows.sort(key=lambda x: (-x["capacity"], x["price"]))
        selected = []
        total = 0
        for r in rows:
            if total >= guest_count:
                break
            selected.append(r)
            total += r["capacity"]
        if total >= guest_count:
            return selected
        max_comb = min(6, len(rows))
        for sz in range(1, max_comb + 1):
            for comb in combinations(rows, sz):
                if sum(r["capacity"] for r in comb) >= guest_count:
                    return list(comb)
        return []

    @staticmethod
    def is_room_booked(room_id, date):
        # reuse the low-level database function already implemented
        return db.is_room_booked(room_id, date)


class BookingModel:
    @staticmethod
    def create(*args, **kwargs):
        return db.create_booking(*args, **kwargs)

    @staticmethod
    def fetch_by_date(date):
        return db.fetch_bookings_by_date(date)

    @staticmethod
    def fetch_range(date_from, date_to):
        return db.fetch_bookings_range(date_from, date_to)

    @staticmethod
    def checkout(bid):
        return db.checkout_booking(bid)

    @staticmethod
    def cancel(bid):
        return db.cancel_booking(bid)

    @staticmethod
    def update(bid, **kwargs):
        return db.update_booking(bid, **kwargs)

    @staticmethod
    def add_payment(bid, amount):
        return db.set_payment(bid, amount)

    @staticmethod
    def export_csv(rows, path):
        return db.export_bookings_csv(rows, path)


# expose availability helpers for controllers
is_table_booked = db.is_table_booked
is_room_booked = db.is_room_booked
