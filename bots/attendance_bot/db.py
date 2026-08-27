import os
import json
import datetime
import asyncpg
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://bot_user:bot_password@localhost/attendance_bot"
)

# Database pool
pool = None

# Legacy files for migration
ATTENDANCE_FILE = "attendance.json"
EVENTS_FILE = "events.json"
MEMBERS_FILE = "members.json"


async def init_db(JST):
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL)

    async with pool.acquire() as conn:
        # Create tables
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                name VARCHAR NOT NULL,
                is_main BOOLEAN DEFAULT FALSE,
                is_tracking BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Cleanup "Unknown" users who might have been added by error
        await conn.execute("UPDATE users SET is_tracking = FALSE WHERE name ILIKE 'unknown'")

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                target_date DATE NOT NULL,
                status VARCHAR NOT NULL,
                is_test BOOLEAN DEFAULT FALSE,
                recorded_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, target_date)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                name VARCHAR PRIMARY KEY,
                event_date DATE NOT NULL
            )
        """)

    # Check for migration
    if any(os.path.exists(f) for f in [ATTENDANCE_FILE, EVENTS_FILE, MEMBERS_FILE]):
        await migrate_json_to_db(JST)


async def migrate_json_to_db(JST):
    print("Starting data migration from JSON to DB...")
    async with pool.acquire() as conn:
        # Migrate Members
        if os.path.exists(MEMBERS_FILE):
            try:
                with open(MEMBERS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    main_members = data.get("main_members", {})
                    active_members = data.get("active_members", {})

                    # Combine and insert
                    all_uids = set(main_members.keys()) | set(active_members.keys())
                    for uid in all_uids:
                        name = main_members.get(uid) or active_members.get(uid)
                        await conn.execute(
                            """
                            INSERT INTO users (user_id, name, is_tracking)
                            VALUES ($1, $2, TRUE)
                            ON CONFLICT (user_id) DO UPDATE 
                            SET name = EXCLUDED.name
                        """,
                            int(uid),
                            name,
                        )
                os.rename(MEMBERS_FILE, MEMBERS_FILE + ".bak")
            except Exception as e:
                print(f"Error migrating members: {e}")

        # Migrate Events
        if os.path.exists(EVENTS_FILE):
            try:
                with open(EVENTS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for name, date_str in data.items():
                        try:
                            event_date = datetime.datetime.strptime(date_str, "%Y/%m/%d").date()
                            await conn.execute(
                                """
                                INSERT INTO events (name, event_date)
                                VALUES ($1, $2)
                                ON CONFLICT (name) DO UPDATE SET event_date = EXCLUDED.event_date
                            """,
                                name,
                                event_date,
                            )
                        except ValueError:
                            continue
                os.rename(EVENTS_FILE, EVENTS_FILE + ".bak")
            except Exception as e:
                print(f"Error migrating events: {e}")

        # Migrate Attendance (Only today's)
        if os.path.exists(ATTENDANCE_FILE):
            try:
                today = datetime.datetime.now(JST).date()
                with open(ATTENDANCE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for uid, info in data.items():
                        await conn.execute(
                            """
                            INSERT INTO users (user_id, name)
                            VALUES ($1, $2)
                            ON CONFLICT (user_id) DO UPDATE SET name = EXCLUDED.name
                        """,
                            int(uid),
                            info["name"],
                        )

                        await conn.execute(
                            """
                            INSERT INTO attendance (user_id, target_date, status)
                            VALUES ($1, $2, $3)
                            ON CONFLICT (user_id, target_date) DO UPDATE SET status = EXCLUDED.status
                        """,
                            int(uid),
                            today,
                            info["status"],
                        )
                os.rename(ATTENDANCE_FILE, ATTENDANCE_FILE + ".bak")
            except Exception as e:
                print(f"Error migrating attendance: {e}")
    print("Migration completed.")
