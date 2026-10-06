"""Lakeside Clinics' legacy booking database: a 2019 PHP app's Postgres, as the IT contractor describes it.

It is deliberately awkward, in the ways real customer systems are: cryptic names, phone numbers in six formats,
a write path that is one non-idempotent stored procedure, and no protection against double-booking outside
the PHP app that no longer exists in your world.
"""

import random
import re
import time
from datetime import date, datetime, timedelta

import psycopg

from . import config

CLINICS = [  # id, name, city, region, hours
    (1, "Lakeside Osu", "Accra", "Greater Accra", "Mon-Fri 08:00-18:00, Sat 08:00-14:00, Sun closed"),
    (2, "Lakeside Labone", "Accra", "Greater Accra", "Mon-Fri 08:00-18:00, Sat 08:00-14:00, Sun closed"),
    (3, "Lakeside East Legon", "Accra", "Greater Accra", "Mon-Sat 07:30-19:00, Sun closed"),
    (4, "Lakeside Madina", "Accra", "Greater Accra", "Mon-Fri 08:00-17:00, Sat 08:00-13:00, Sun closed"),
    (5, "Lakeside Dansoman", "Accra", "Greater Accra", "Mon-Fri 08:00-17:00, Sat closed, Sun closed"),
    (6, "Lakeside Spintex", "Accra", "Greater Accra", "Mon-Sat 08:00-18:00, Sun closed"),
    (7, "Lakeside Adenta", "Accra", "Greater Accra", "Mon-Fri 08:00-17:00, Sat 08:00-12:00, Sun closed"),
    (8, "Lakeside Tema Community 2", "Tema", "Greater Accra", "Mon-Fri 08:00-17:00, Sat closed, Sun closed"),
    (9, "Lakeside Adum", "Kumasi", "Ashanti", "Mon-Sat 08:00-18:00, Sun closed"),
    (10, "Lakeside Ahodwo", "Kumasi", "Ashanti", "Mon-Fri 08:00-17:00, Sat 08:00-13:00, Sun closed"),
    (11, "Lakeside Bantama", "Kumasi", "Ashanti", "Mon-Fri 08:00-17:00, Sat 08:00-13:00, Sun closed"),
    (12, "Lakeside Suame", "Kumasi", "Ashanti", "Mon-Fri 08:00-17:00, Sat closed, Sun closed"),
    (13, "Lakeside Kwadaso", "Kumasi", "Ashanti", "Mon-Fri 08:00-17:00, Sat 08:00-12:00, Sun closed"),
    (14, "Lakeside Asokwa", "Kumasi", "Ashanti", "Mon-Fri 08:00-17:00, Sat closed, Sun closed"),
]
SERVICES = [("GEN", "General consultation", 120), ("ANC", "Antenatal visit", 150), ("PED", "Paediatric consultation", 140),
            ("DEN", "Dental scaling", 200), ("LAB", "Malaria test", 60), ("EYE", "Eye examination", 180), ("VAC", "Immunisation", 80)]

SCHEMA = """
DROP SCHEMA public CASCADE; CREATE SCHEMA public;
CREATE TABLE tbl_clinic (clinic_id int PRIMARY KEY, clinic_nm text, city text, region text, open_hrs text);
CREATE TABLE tbl_svc (svc_code text PRIMARY KEY, svc_nm text, price_ghs numeric(8,2));
CREATE TABLE tbl_pt (pt_id serial PRIMARY KEY, pt_fname text, pt_lname text, pt_phone text, pt_dob date, pt_created timestamp);
CREATE TABLE tbl_slot (slot_id serial PRIMARY KEY, clinic_id int REFERENCES tbl_clinic, slot_dt timestamp, svc_code text REFERENCES tbl_svc, slot_st char(1) DEFAULT 'O');
CREATE TABLE tbl_appt (appt_id serial PRIMARY KEY, pt_id int REFERENCES tbl_pt, slot_id int REFERENCES tbl_slot, booked_on timestamp, appt_st char(1), rem_sent boolean DEFAULT false);
CREATE TABLE tbl_sys (k text PRIMARY KEY, v text);
CREATE INDEX ON tbl_slot (clinic_id, slot_dt);
CREATE INDEX ON tbl_appt (pt_id);
CREATE INDEX ON tbl_appt (slot_id);
COMMENT ON COLUMN tbl_slot.slot_st IS 'O open, B booked, X blocked';
COMMENT ON COLUMN tbl_appt.appt_st IS 'B booked, C cancelled, A attended, N no-show';

CREATE FUNCTION create_booking(p_phone text, p_clinic int, p_slot int) RETURNS int
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_pt int; v_appt int;
BEGIN
  IF (SELECT v FROM tbl_sys WHERE k = 'backup_window') = 'on' THEN
    RAISE EXCEPTION 'canceling statement due to lock timeout' USING ERRCODE = '55P03';
  END IF;
  SELECT pt_id INTO v_pt FROM tbl_pt WHERE pt_phone = p_phone LIMIT 1;      -- exact string match
  IF v_pt IS NULL THEN
    INSERT INTO tbl_pt (pt_fname, pt_lname, pt_phone, pt_created) VALUES ('', '', p_phone, now()) RETURNING pt_id INTO v_pt;
  END IF;
  INSERT INTO tbl_appt (pt_id, slot_id, booked_on, appt_st) VALUES (v_pt, p_slot, now(), 'B') RETURNING appt_id INTO v_appt;
  UPDATE tbl_slot SET slot_st = 'B' WHERE slot_id = p_slot;
  RETURN v_appt;
END $$;

CREATE FUNCTION cancel_booking(p_appt int) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  IF (SELECT v FROM tbl_sys WHERE k = 'backup_window') = 'on' THEN
    RAISE EXCEPTION 'canceling statement due to lock timeout' USING ERRCODE = '55P03';
  END IF;
  UPDATE tbl_appt SET appt_st = 'C' WHERE appt_id = p_appt;
  UPDATE tbl_slot SET slot_st = 'O' WHERE slot_id = (SELECT slot_id FROM tbl_appt WHERE appt_id = p_appt);
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'replica_ro') THEN CREATE ROLE replica_ro LOGIN PASSWORD 'replica-pass'; END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'bookings_writer') THEN CREATE ROLE bookings_writer LOGIN PASSWORD 'writer-pass'; END IF;
END $$;
REVOKE ALL ON FUNCTION create_booking(text, int, int), cancel_booking(int) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION create_booking(text, int, int), cancel_booking(int) TO bookings_writer;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO replica_ro;
GRANT USAGE ON SCHEMA public TO replica_ro, bookings_writer;
"""

FIRST = ["Kofi", "Ama", "Kwame", "Abena", "Yaw", "Akosua", "Kwesi", "Efua", "Kojo", "Adwoa", "Nana", "Esi", "Kwabena", "Afia",
         "Fiifi", "Araba", "Yaa", "Kobby", "Maame", "Selorm", "Edem", "Mawuli", "Dela", "Senyo", "Wumbei", "Abdul", "Fati", "Ibrahim"]
LAST = ["Mensah", "Owusu", "Boateng", "Asante", "Addo", "Appiah", "Darko", "Ofori", "Quaye", "Tetteh", "Amoah", "Sarpong", "Agyei",
        "Nkrumah", "Ansah", "Frimpong", "Badu", "Yeboah", "Acheampong", "Adjei", "Ampofo", "Lamptey", "Kuffour", "Danquah", "Gyamfi"]


def connect(dsn: str | None = None, **kw) -> psycopg.Connection:
    return psycopg.connect(dsn or config.LAKESIDE_ADMIN_DSN, autocommit=True, **kw)


def phone_formats(national: str, rnd: random.Random) -> str | None:
    """Nine-digit national number -> the way some PHP form stored it."""
    r = rnd.random()
    if r < 0.03:
        return None
    if r < 0.06:
        return rnd.choice(["N/A", "0", "none", national[:5]])
    forms = [f"0{national}", f"+233{national}", f"233{national}", f"0{national[:2]} {national[2:5]} {national[5:]}",
             f"0{national[:2]}-{national[2:5]}-{national[5:]}", national]
    return forms[int(rnd.random() ** 1.6 * len(forms))]      # favours the first formats


def norm9(phone: str | None) -> str:
    """Last nine digits: the join key for 'same phone number', whatever the format."""
    return re.sub(r"\D", "", phone or "")[-9:]


def _wait_ready(timeout: float = 60.0):
    end = time.time() + timeout
    while True:
        try:
            with connect(connect_timeout=3):
                return
        except psycopg.OperationalError:
            if time.time() > end:
                raise
            time.sleep(1.5)


def is_seeded() -> bool:
    try:
        with connect() as c:
            row = c.execute("SELECT v FROM tbl_sys WHERE k = 'seeded_on'").fetchone()
        return bool(row) and (date.today() - date.fromisoformat(row[0])).days < 3
    except psycopg.Error:
        return False


def seed(seed_value: int = 2019) -> dict:
    """(Re)build the whole database. Dates are relative to today, so slots are always in the future."""
    rnd = random.Random(seed_value)
    today = date.today()
    _wait_ready()
    with connect() as c:
        c.execute(SCHEMA)
        c.cursor().executemany("INSERT INTO tbl_clinic VALUES (%s,%s,%s,%s,%s)", CLINICS)
        c.cursor().executemany("INSERT INTO tbl_svc VALUES (%s,%s,%s)", SERVICES)

        # patients: ~3,600, with the phone-format mess. A person is one row, in one format
        pts = []
        used = set()
        for i in range(3600):
            f, l = rnd.choice(FIRST), rnd.choice(LAST)
            national = rnd.choice(["24", "54", "55", "20", "50", "27", "26", "57", "59"]) + "".join(rnd.choice("0123456789") for _ in range(7))
            if national in used:
                continue
            used.add(national)
            pts.append((f, l, phone_formats(national, rnd), date(rnd.randint(1950, 2020), rnd.randint(1, 12), rnd.randint(1, 28)),
                        datetime.combine(today - timedelta(days=rnd.randint(1, 900)), datetime.min.time())))
        with c.cursor().copy("COPY tbl_pt (pt_fname, pt_lname, pt_phone, pt_dob, pt_created) FROM STDIN") as cp:
            for r in pts:
                cp.write_row(r)
        n_pt = len(pts)

        # slots: 14 clinics x [-300, +21] days x 9 hourly slots, Sundays closed
        slot_rows, hist = [], []
        for cid, *_ in CLINICS:
            for off in range(-300, 22):
                d = today + timedelta(days=off)
                if d.weekday() == 6:
                    continue
                for h in range(8, 17):
                    svc = "GEN" if h not in (11, 14) else rnd.choice(["GEN", "GEN", "ANC", "PED", "LAB", "DEN", "EYE", "VAC"])
                    slot_rows.append((cid, datetime(d.year, d.month, d.day, h), svc, "O", off))
        with c.cursor().copy("COPY tbl_slot (clinic_id, slot_dt, svc_code, slot_st) FROM STDIN") as cp:
            for r in slot_rows:
                cp.write_row(r[:4])
        ids = c.execute("SELECT slot_id, slot_dt FROM tbl_slot ORDER BY slot_id").fetchall()

        # appointments: ~1/3 of past slots were booked (with outcomes), ~40% of future slots are booked.
        # No-show probability is ~18% overall, with real structure for the reminder model to find.
        appts, booked_slots = [], []
        for (sid, dt), row in zip(ids, slot_rows):
            off = row[4]
            if rnd.random() > (0.34 if off < 0 else 0.40):
                continue
            pt = rnd.randint(1, n_pt)
            if off < 0:
                p = 0.17
                p += 0.07 if dt.weekday() == 0 else 0
                p += 0.06 if dt.hour == 8 else 0
                p += 0.05 if pt > n_pt * 0.8 else 0              # newer patients miss more
                reminded = off > -120 and rnd.random() < 0.5     # a reminder pilot ran for the last 120 days
                p -= 0.08 if reminded else 0
                st = "N" if rnd.random() < max(p, 0.02) else "A"
                appts.append((pt, sid, dt - timedelta(days=rnd.randint(1, 14)), st, reminded))
            else:
                appts.append((pt, sid, datetime.now() - timedelta(days=rnd.randint(0, 6)), "B", False))
                booked_slots.append(sid)
        with c.cursor().copy("COPY tbl_appt (pt_id, slot_id, booked_on, appt_st, rem_sent) FROM STDIN") as cp:
            for r in appts:
                cp.write_row(r)
        c.execute("UPDATE tbl_slot SET slot_st = 'B' WHERE slot_id = ANY(%s)", (booked_slots,))
        c.execute("INSERT INTO tbl_sys VALUES ('backup_window', 'off'), ('seeded_on', %s)", (today.isoformat(),))
        c.execute("ANALYZE")
    return {"patients": n_pt, "slots": len(ids), "appointments": len(appts)}


def ensure_seeded():
    _wait_ready()
    if not is_seeded():
        seed()


def set_backup_window(on: bool):
    with connect() as c:
        c.execute("UPDATE tbl_sys SET v = %s WHERE k = 'backup_window'", ("on" if on else "off",))


def backup_window() -> bool:
    with connect() as c:
        r = c.execute("SELECT v FROM tbl_sys WHERE k = 'backup_window'").fetchone()
    return bool(r) and r[0] == "on"


def stats() -> dict:
    with connect() as c:
        q = lambda sql: c.execute(sql).fetchone()[0]
        return {"clinics": q("SELECT count(*) FROM tbl_clinic"), "patients": q("SELECT count(*) FROM tbl_pt"),
                "slots": q("SELECT count(*) FROM tbl_slot"), "appointments": q("SELECT count(*) FROM tbl_appt"),
                "backup_window": backup_window()}
