from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
from datetime import date, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(__file__).resolve().parent / "rewards.db"
INDEX_PATH = BASE_DIR / "pomodoro-timer.html"
# Listen on all interfaces in production, localhost in development
HOST = "0.0.0.0"  # Changed from 127.0.0.1 for cloud deployment
PORT = int(os.environ.get("PORT", 8000))  # Use PORT env var if set


def utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (name,),
    ).fetchone()
    return row is not None


def table_columns(conn: sqlite3.Connection, name: str) -> list[str]:
    return [str(row["name"]) for row in conn.execute(f"PRAGMA table_info({name})")]


def ensure_user_profile(conn: sqlite3.Connection, user_id: int) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO user_profiles (
            user_id,
            points,
            total_focus_sessions,
            total_focus_minutes,
            current_streak,
            longest_streak,
            last_focus_date,
            updated_at
        ) VALUES (?, 0, 0, 0, 0, 0, NULL, ?)
        """,
        (user_id, utc_now()),
    )


def migrate_legacy_profile(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "profile"):
        return
    if conn.execute("SELECT COUNT(*) FROM user_profiles").fetchone()[0]:
        return

    target_user = conn.execute("SELECT id FROM users ORDER BY id LIMIT 1").fetchone()
    if not target_user:
        return

    legacy_columns = set(table_columns(conn, "profile"))
    if "user_id" in legacy_columns:
        conn.execute(
            """
            INSERT OR IGNORE INTO user_profiles (
                user_id,
                points,
                total_focus_sessions,
                total_focus_minutes,
                current_streak,
                longest_streak,
                last_focus_date,
                updated_at
            )
            SELECT
                user_id,
                points,
                total_focus_sessions,
                total_focus_minutes,
                current_streak,
                longest_streak,
                last_focus_date,
                updated_at
            FROM profile
            """
        )
        return

    legacy = conn.execute(
        """
        SELECT
            points,
            total_focus_sessions,
            total_focus_minutes,
            current_streak,
            longest_streak,
            last_focus_date,
            updated_at
        FROM profile
        ORDER BY id
        LIMIT 1
        """
    ).fetchone()
    if not legacy:
        return

    conn.execute(
        """
        INSERT OR IGNORE INTO user_profiles (
            user_id,
            points,
            total_focus_sessions,
            total_focus_minutes,
            current_streak,
            longest_streak,
            last_focus_date,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(target_user["id"]),
            int(legacy["points"]),
            int(legacy["total_focus_sessions"]),
            int(legacy["total_focus_minutes"]),
            int(legacy["current_streak"]),
            int(legacy["longest_streak"]),
            legacy["last_focus_date"],
            legacy["updated_at"],
        ),
    )


def migrate_legacy_sessions(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "sessions"):
        return
    if conn.execute("SELECT COUNT(*) FROM user_sessions").fetchone()[0]:
        return

    target_user = conn.execute("SELECT id FROM users ORDER BY id LIMIT 1").fetchone()
    if not target_user:
        return

    legacy_columns = set(table_columns(conn, "sessions"))
    if "user_id" in legacy_columns:
        conn.execute(
            """
            INSERT INTO user_sessions (
                user_id,
                mode,
                duration_seconds,
                task_name,
                points_awarded,
                counted,
                completed_on,
                completed_at
            )
            SELECT
                user_id,
                mode,
                duration_seconds,
                task_name,
                points_awarded,
                counted,
                completed_on,
                completed_at
            FROM sessions
            ORDER BY id
            """
        )
        return

    conn.execute(
        """
        INSERT INTO user_sessions (
            user_id,
            mode,
            duration_seconds,
            task_name,
            points_awarded,
            counted,
            completed_on,
            completed_at
        )
        SELECT
            ?,
            mode,
            duration_seconds,
            task_name,
            points_awarded,
            counted,
            completed_on,
            completed_at
        FROM sessions
        ORDER BY id
        """,
        (int(target_user["id"]),),
    )


def ensure_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id INTEGER PRIMARY KEY,
                points INTEGER NOT NULL DEFAULT 0,
                total_focus_sessions INTEGER NOT NULL DEFAULT 0,
                total_focus_minutes INTEGER NOT NULL DEFAULT 0,
                current_streak INTEGER NOT NULL DEFAULT 0,
                longest_streak INTEGER NOT NULL DEFAULT 0,
                last_focus_date TEXT,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                mode TEXT NOT NULL,
                duration_seconds INTEGER NOT NULL,
                task_name TEXT,
                points_awarded INTEGER NOT NULL DEFAULT 0,
                counted INTEGER NOT NULL DEFAULT 1,
                completed_on TEXT NOT NULL,
                completed_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_tokens (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        migrate_legacy_profile(conn)
        migrate_legacy_sessions(conn)
        conn.commit()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def create_token(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO auth_tokens (token, user_id, created_at) VALUES (?, ?, ?)",
            (token, user_id, utc_now()),
        )
        conn.commit()
    return token


def verify_token(token: str | None) -> int | None:
    if not token:
        return None
    with get_conn() as conn:
        row = conn.execute(
            "SELECT user_id FROM auth_tokens WHERE token = ?",
            (token,),
        ).fetchone()
    return int(row["user_id"]) if row else None


def revoke_token(token: str | None) -> None:
    if not token:
        return
    with get_conn() as conn:
        conn.execute("DELETE FROM auth_tokens WHERE token = ?", (token,))
        conn.commit()


def get_user(conn: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT id, username, email, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()


def validate_identity(username: str, email: str, password: str) -> str | None:
    username = username.strip()
    email = email.strip()
    if not username or not email or not password:
        return "All fields are required."
    if len(username) < 3:
        return "Username must be at least 3 characters."
    if "@" not in email or "." not in email.split("@")[-1]:
        return "Please enter a valid email address."
    if len(password) < 5:
        return "Password must be at least 5 characters."
    return None


def register_user(username: str, email: str, password: str) -> dict[str, object]:
    error = validate_identity(username, email, password)
    if error:
        return {"status": "error", "error": error}

    try:
        with get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO users (username, email, password_hash, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (username.strip(), email.strip().lower(), hash_password(password), utc_now()),
            )
            user_id = int(cursor.lastrowid)
            ensure_user_profile(conn, user_id)
            conn.commit()
        token = create_token(user_id)
        return {
            "status": "success",
            "token": token,
            "user_id": user_id,
            "username": username.strip(),
        }
    except sqlite3.IntegrityError:
        return {"status": "error", "error": "Username or email already exists."}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def login_user(username: str, password: str) -> dict[str, object]:
    username = username.strip()
    if not username or not password:
        return {"status": "error", "error": "Username and password are required."}

    try:
        with get_conn() as conn:
            user = conn.execute(
                "SELECT id, username, password_hash FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if not user or user["password_hash"] != hash_password(password):
                return {"status": "error", "error": "Invalid credentials."}
            ensure_user_profile(conn, int(user["id"]))
            conn.commit()
        token = create_token(int(user["id"]))
        return {
            "status": "success",
            "token": token,
            "user_id": int(user["id"]),
            "username": str(user["username"]),
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def compute_level(points: int) -> dict[str, int]:
    level = max(1, points // 100 + 1)
    current_floor = (level - 1) * 100
    next_target = level * 100
    return {
        "level": level,
        "current_floor": current_floor,
        "next_target": next_target,
        "progress_points": points - current_floor,
        "points_to_next": next_target - points,
    }


def build_achievements(profile: sqlite3.Row) -> list[dict[str, object]]:
    points = int(profile["points"])
    sessions = int(profile["total_focus_sessions"])
    streak = int(profile["current_streak"])
    longest_streak = int(profile["longest_streak"])
    return [
        {
            "id": "first_focus",
            "title": "First Focus",
            "earned": sessions >= 1,
            "hint": "Complete your first focus session.",
        },
        {
            "id": "streak_3",
            "title": "3-Day Streak",
            "earned": streak >= 3 or longest_streak >= 3,
            "hint": "Focus on three different days.",
        },
        {
            "id": "pomodoro_10",
            "title": "Pomodoro Ten",
            "earned": sessions >= 10,
            "hint": "Complete ten focus sessions.",
        },
        {
            "id": "points_500",
            "title": "500 Points",
            "earned": points >= 500,
            "hint": "Reach 500 total reward points.",
        },
    ]


def reward_snapshot(conn: sqlite3.Connection, user_id: int) -> dict[str, object]:
    ensure_user_profile(conn, user_id)
    profile = conn.execute(
        "SELECT * FROM user_profiles WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    recent_rows = conn.execute(
        """
        SELECT mode, duration_seconds, task_name, points_awarded, counted, completed_at
        FROM user_sessions
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 6
        """,
        (user_id,),
    ).fetchall()
    level = compute_level(int(profile["points"]))
    return {
        "connected": True,
        "profile": {
            "points": int(profile["points"]),
            "total_focus_sessions": int(profile["total_focus_sessions"]),
            "total_focus_minutes": int(profile["total_focus_minutes"]),
            "current_streak": int(profile["current_streak"]),
            "longest_streak": int(profile["longest_streak"]),
            "last_focus_date": profile["last_focus_date"],
            **level,
        },
        "achievements": build_achievements(profile),
        "recent_sessions": [
            {
                "mode": row["mode"],
                "duration_seconds": int(row["duration_seconds"]),
                "task_name": row["task_name"],
                "points_awarded": int(row["points_awarded"]),
                "counted": bool(row["counted"]),
                "completed_at": row["completed_at"],
            }
            for row in recent_rows
        ],
    }


def update_streak(last_focus_date: str | None, completed_on: str) -> tuple[int, int]:
    if not completed_on:
        completed_on = date.today().isoformat()
    if not last_focus_date:
        return 1, 1
    try:
        prev = date.fromisoformat(last_focus_date)
        current = date.fromisoformat(completed_on)
    except ValueError:
        return 1, 1
    delta = (current - prev).days
    if delta <= 0:
        return 0, 0
    if delta == 1:
        return 1, 0
    return 1, 1


def award_points(duration_seconds: int) -> int:
    minutes = max(1, round(duration_seconds / 60))
    return max(10, min(60, minutes + 5))


def record_session(user_id: int, payload: dict[str, object]) -> dict[str, object]:
    mode = str(payload.get("mode") or "focus")
    duration_seconds = max(0, int(payload.get("duration_seconds") or 0))
    task_name = str(payload.get("task_name") or "").strip() or None
    counted_value = payload.get("counted", True)
    counted = counted_value if isinstance(counted_value, bool) else str(counted_value).lower() == "true"
    completed_at = str(payload.get("completed_at") or utc_now())
    completed_on = str(payload.get("completed_on") or date.today().isoformat())

    points_awarded = 0
    minutes = round(duration_seconds / 60)

    with get_conn() as conn:
        ensure_user_profile(conn, user_id)
        profile = conn.execute(
            "SELECT * FROM user_profiles WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        if counted and mode == "focus":
            points_awarded = award_points(duration_seconds)
            streak_delta, streak_reset = update_streak(profile["last_focus_date"], completed_on)
            current_streak = 1 if streak_reset else int(profile["current_streak"]) + streak_delta
            if streak_delta == 0 and profile["last_focus_date"] == completed_on:
                current_streak = int(profile["current_streak"])
            longest_streak = max(int(profile["longest_streak"]), current_streak)
            conn.execute(
                """
                UPDATE user_profiles
                SET points = points + ?,
                    total_focus_sessions = total_focus_sessions + 1,
                    total_focus_minutes = total_focus_minutes + ?,
                    current_streak = ?,
                    longest_streak = ?,
                    last_focus_date = ?,
                    updated_at = ?
                WHERE user_id = ?
                """,
                (
                    points_awarded,
                    minutes,
                    current_streak,
                    longest_streak,
                    completed_on,
                    utc_now(),
                    user_id,
                ),
            )
        else:
            conn.execute(
                "UPDATE user_profiles SET updated_at = ? WHERE user_id = ?",
                (utc_now(), user_id),
            )

        conn.execute(
            """
            INSERT INTO user_sessions (
                user_id,
                mode,
                duration_seconds,
                task_name,
                points_awarded,
                counted,
                completed_on,
                completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                mode,
                duration_seconds,
                task_name,
                points_awarded,
                1 if counted else 0,
                completed_on,
                completed_at,
            ),
        )
        conn.commit()
        snapshot = reward_snapshot(conn, user_id)

    snapshot["last_award"] = {
        "points_awarded": points_awarded,
        "counted": counted,
        "mode": mode,
        "duration_minutes": minutes,
        "task_name": task_name,
    }
    return snapshot


class Handler(BaseHTTPRequestHandler):
    server_version = "FocusTomatoBackend/2.0"

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        super().end_headers()

    def log_message(self, fmt: str, *args: object) -> None:
        return

    def _send_json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_html(self, path: Path) -> None:
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict[str, object]:
        size = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(size) if size else b"{}"
        return json.loads(raw.decode("utf-8"))

    def _get_token(self) -> str | None:
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return auth[7:]
        return None

    def _require_user(self) -> int | None:
        return verify_token(self._get_token())

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/pomodoro-timer.html"}:
            return self._send_html(INDEX_PATH)
        if parsed.path == "/api/health":
            return self._send_json({"status": "ok", "timestamp": utc_now()})

        user_id = self._require_user()

        if parsed.path == "/api/me":
            if not user_id:
                return self._send_json({"error": "Unauthorized"}, HTTPStatus.UNAUTHORIZED)
            with get_conn() as conn:
                user = get_user(conn, user_id)
                reward_data = reward_snapshot(conn, user_id)
            return self._send_json(
                {
                    "status": "success",
                    "user": {
                        "id": int(user["id"]),
                        "username": str(user["username"]),
                        "email": str(user["email"]),
                        "created_at": str(user["created_at"]),
                    },
                    "rewards": reward_data,
                }
            )

        if parsed.path == "/api/rewards":
            if not user_id:
                return self._send_json({"error": "Unauthorized"}, HTTPStatus.UNAUTHORIZED)
            with get_conn() as conn:
                return self._send_json(reward_snapshot(conn, user_id))

        return self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/api/register":
            try:
                payload = self._read_json()
            except json.JSONDecodeError:
                return self._send_json({"error": "Invalid JSON"}, HTTPStatus.BAD_REQUEST)
            result = register_user(
                str(payload.get("username", "")),
                str(payload.get("email", "")),
                str(payload.get("password", "")),
            )
            status = HTTPStatus.OK if result.get("status") == "success" else HTTPStatus.BAD_REQUEST
            return self._send_json(result, status)

        if parsed.path == "/api/login":
            try:
                payload = self._read_json()
            except json.JSONDecodeError:
                return self._send_json({"error": "Invalid JSON"}, HTTPStatus.BAD_REQUEST)
            result = login_user(
                str(payload.get("username", "")),
                str(payload.get("password", "")),
            )
            status = HTTPStatus.OK if result.get("status") == "success" else HTTPStatus.UNAUTHORIZED
            return self._send_json(result, status)

        if parsed.path == "/api/logout":
            token = self._get_token()
            revoke_token(token)
            return self._send_json({"status": "success"})

        user_id = self._require_user()

        if parsed.path == "/api/session/complete":
            if not user_id:
                return self._send_json({"error": "Unauthorized"}, HTTPStatus.UNAUTHORIZED)
            try:
                payload = self._read_json()
            except json.JSONDecodeError:
                return self._send_json({"error": "Invalid JSON"}, HTTPStatus.BAD_REQUEST)
            return self._send_json(record_session(user_id, payload))

        return self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)


def main() -> None:
    ensure_db()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"FocusTomato backend running at http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
