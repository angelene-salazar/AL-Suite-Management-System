from models import TableModel, RoomModel, BookingModel, is_table_booked, is_room_booked
import database as db
from datetime import datetime, date, time, timedelta

ADULT_ENTRANCE = 150.0
CHILD_ENTRANCE = 130.0


class BookingController:
    def suggest_table(self, adults: int, children: int, date: str = None):
        guests = (adults or 0) + (children or 0)
        return TableModel.find_suitable(guests, date)

    def suggest_tables(self, adults: int, children: int, date: str = None):
        guests = (adults or 0) + (children or 0)
        return TableModel.find_tables_for(guests, date)

    def suggest_room(self, adults: int, children: int, date: str = None):
        guests = (adults or 0) + (children or 0)
        return RoomModel.find_suitable(guests, date)

    def suggest_rooms(self, adults: int, children: int, date: str = None):
        guests = (adults or 0) + (children or 0)
        return RoomModel.find_rooms_for(guests, date)

    def calculate_entrance(self, adults: int, children: int) -> float:
        return (adults or 0) * ADULT_ENTRANCE + (children or 0) * CHILD_ENTRANCE

    def calculate_total(self, adults, children, entrance_fee, table_fee, room_fee, package):
        t_fee = table_fee or 0.0
        r_fee = room_fee or 0.0
        if package == "Day Tour":
            total = (entrance_fee or 0) + t_fee
        elif package == "Overnight":
            total = (entrance_fee or 0) + r_fee + t_fee
        else:
            total = (entrance_fee or 0) + t_fee + r_fee
        return total, entrance_fee

    def validate_availability(self, date, table_ids, room_ids):
        """Return (ok:bool, msg:str). Accepts lists or None."""
        if table_ids:
            for tid in table_ids:
                if is_table_booked(tid, date):
                    return False, f"Table {tid} is already booked for {date}"
        if room_ids:
            for rid in room_ids:
                if is_room_booked(rid, date):
                    return False, f"Room {rid} is already booked for {date}"
        return True, "OK"

    def create_booking(
        self,
        guest_name,
        booking_date,
        adults,
        children,
        package,
        table_ids,
        room_ids,
        table_fee,
        room_fee,
        total_amount,
        amount_paid,
    ):
        entrance_fee = self.calculate_entrance(adults, children)
        BookingModel.create(
            guest_name,
            booking_date,
            adults,
            children,
            package,
            table_ids,
            room_ids,
            table_fee,
            room_fee,
            entrance_fee,
            total_amount,
            amount_paid,
        )

    def edit_booking(self, bid, **kwargs):
        BookingModel.update(bid, **kwargs)

    def add_payment(self, bid, amount):
        BookingModel.add_payment(bid, amount)


class AdminController:
    def report_for_date(self, date_str):
        return BookingModel.fetch_by_date(date_str)

    def report_range(self, dfrom, dto):
        return BookingModel.fetch_range(dfrom, dto)

    def report_all(self):
        # expose whole range
        return BookingModel.fetch_range("0000-01-01", "9999-12-31")

    def checkout(self, booking_id):
        BookingModel.checkout(booking_id)

    def cancel(self, booking_id):
        BookingModel.cancel(booking_id)

    def export_csv(self, rows, path):
        BookingModel.export_csv(rows, path)

    def check_auto_checkout(self) -> list[int]:
        """
        Identifies and RETURNS a list of IDs for 'Overnight' guests
        who are past the 8:00 AM cutoff of the day following their booking_date.
        """
        now = datetime.now()
        today = now.date()

        # Define the cutoff time (8:00 AM)
        cutoff_time = time(8, 0, 0)
        cutoff_dt = datetime.combine(today, cutoff_time)

        # Optimization: only proceed if it's past 8 AM today
        if now < cutoff_dt:
            return []

        # --- FIX: Use get_conn() instead of db.query() ---
        active = []
        with db.get_conn() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT id, booking_date, package
                FROM bookings
                WHERE status = 'checked-in'
            """)
            active = c.fetchall()
        # -------------------------------------------------

        overdue_bookings = []

        for b in active:
            try:
                # b["booking_date"] works because row_factory is sqlite3.Row
                booking_date = datetime.strptime(b["booking_date"], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                continue

            package = b["package"]

            if package.lower() == "overnight":
                expected_checkout_date = booking_date + timedelta(days=1)
                expected_checkout_dt = datetime.combine(expected_checkout_date, cutoff_time)

                if now >= expected_checkout_dt:
                    overdue_bookings.append(b["id"])

        return overdue_bookings

    def create_account(self, username, password):
        """
        Validates password strength, checks username existence,
        hashes password, and creates user.
        """
        import utils
        from models import find_user, create_user

        # 1. Check empty
        if not username or not password:
            return False, "Username and Password are required."

        # 2. Check existence
        if find_user(username):
            return False, "Username already taken."

        # 3. Check Complexity
        is_valid, msg = utils.validate_password_strength(password)
        if not is_valid:
            return False, msg

        # 4. Hash and Save
        salt, pw_hash = utils.hash_password(password)
        try:
            # Creating as admin by default since created from Admin View
            create_user(username, salt, pw_hash, is_admin=1)
            return True, f"Account '{username}' created successfully."
        except Exception as e:
            return False, str(e)