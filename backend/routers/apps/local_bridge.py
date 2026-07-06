import json
import os
import secrets
import sqlite3
import subprocess
import time
import uuid
from pathlib import Path

import requests
from fastapi import APIRouter, Header, Query, status

from schemas.local_bridge import (
    BridgeActionRequest,
    BridgeActionResponse,
    BridgeInboxMessageRequest,
    InvocationAckRequest,
    InvocationEventRequest,
    InvocationMessageRequest,
    InvocationTaskRequest,
    InvocationTaskStatusRequest,
)
from utils.procedures import CustomError


router = APIRouter(prefix="/local-bridge", tags=["local-bridge"])

APP_ALIASES = {
    "notepad": "notepad.exe",
    "bloc de notas": "notepad.exe",
    "block de notas": "notepad.exe",
    "calculator": "calc.exe",
    "calculadora": "calc.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "vscode": "Code.exe",
    "visual studio code": "Code.exe",
    "media player": "mswindowsmusic:",
    "windows media player": "mswindowsmusic:",
    "windows media": "mswindowsmusic:",
    "reproductor": "mswindowsmusic:",
    "reproductor de musica": "mswindowsmusic:",
    "reproductor de música": "mswindowsmusic:",
    "musica": "mswindowsmusic:",
    "música": "mswindowsmusic:",
    "spotify": "spotify:",
}

EYES_BASE_URL = os.getenv("ARKAIOS_EYES_BASE_URL", "http://127.0.0.1:8001")
MESSAGE_LEASE_SECONDS = 60


def _now() -> float:
    return time.time()


def _app_data_dir() -> Path:
    root = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA") or str(Path.home())
    path = Path(root) / "NeuralAgent"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _token_path() -> Path:
    return _app_data_dir() / "local_bridge_token.txt"


def _load_or_create_token() -> str:
    path = _token_path()
    if path.exists():
        token = path.read_text(encoding="utf-8").strip()
        if token:
            return token
    token = "na-bridge-" + secrets.token_urlsafe(32)
    path.write_text(token, encoding="utf-8")
    return token


def _require_token(x_bridge_token: str | None) -> None:
    expected = _load_or_create_token()
    if not x_bridge_token or not secrets.compare_digest(x_bridge_token, expected):
        raise CustomError(status.HTTP_401_UNAUTHORIZED, "Invalid_Bridge_Token")


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(_app_data_dir() / "local_bridge.sqlite")
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def _init_db() -> None:
    conn = _get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            channel_id TEXT NOT NULL,
            conversation_id TEXT NOT NULL,
            direction TEXT NOT NULL,
            payload TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at REAL NOT NULL,
            updated_at REAL,
            lease_until REAL,
            error TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            channel_id TEXT NOT NULL,
            conversation_id TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            input TEXT NOT NULL,
            status TEXT NOT NULL,
            result TEXT,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            channel_id TEXT NOT NULL,
            task_id TEXT,
            event_type TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at REAL NOT NULL
        )
        """
    )

    # Lightweight migrations for databases created by earlier bridge builds.
    for column, ddl in {
        "updated_at": "REAL",
        "lease_until": "REAL",
        "error": "TEXT",
    }.items():
        _ensure_column(conn, "messages", column, ddl)
    for column, ddl in {
        "channel_id": "TEXT DEFAULT 'legacy'",
        "conversation_id": "TEXT DEFAULT 'default'",
        "input": "TEXT DEFAULT '{}'",
    }.items():
        _ensure_column(conn, "tasks", column, ddl)

    conn.commit()
    conn.close()


_init_db()


def _insert_event(
    conn: sqlite3.Connection,
    channel_id: str,
    event_type: str,
    payload: dict,
    task_id: str | None = None,
) -> str:
    event_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO events (id, channel_id, task_id, event_type, payload, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (event_id, channel_id, task_id, event_type, json.dumps(payload), _now()),
    )
    return event_id


def _insert_message(
    conn: sqlite3.Connection,
    request: InvocationMessageRequest,
    direction: str,
    initial_status: str = "unread",
) -> str:
    msg_id = str(uuid.uuid4())
    ts = _now()
    conn.execute(
        """
        INSERT INTO messages
            (id, channel_id, conversation_id, direction, payload, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            msg_id,
            request.channel_id,
            request.conversation_id,
            direction,
            json.dumps(request.payload),
            initial_status,
            ts,
            ts,
        ),
    )
    _insert_event(
        conn,
        request.channel_id,
        "message.created",
        {
            "message_id": msg_id,
            "conversation_id": request.conversation_id,
            "direction": direction,
            "status": initial_status,
        },
    )
    return msg_id


def _message_row(row: sqlite3.Row, status_override: str | None = None) -> dict:
    return {
        "id": row["id"],
        "channel_id": row["channel_id"],
        "conversation_id": row["conversation_id"],
        "direction": row["direction"],
        "payload": json.loads(row["payload"]),
        "status": status_override or row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"] or row["created_at"],
    }


def _task_row(row: sqlite3.Row) -> dict:
    result = json.loads(row["result"]) if row["result"] else None
    return {
        "id": row["id"],
        "channel_id": row["channel_id"],
        "conversation_id": row["conversation_id"],
        "tool_name": row["tool_name"],
        "input": json.loads(row["input"]),
        "status": row["status"],
        "result": result,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _event_row(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "channel_id": row["channel_id"],
        "task_id": row["task_id"],
        "event_type": row["event_type"],
        "payload": json.loads(row["payload"]),
        "created_at": row["created_at"],
    }


def _resolve_app(app_name: str | None) -> str:
    if not app_name:
        raise CustomError(status.HTTP_400_BAD_REQUEST, "Missing_App_Name")
    normalized = app_name.strip().lower()
    if normalized in APP_ALIASES:
        return APP_ALIASES[normalized]
    if normalized.endswith(".exe") and all(ch not in normalized for ch in "\\/:*?\"<>|"):
        return normalized
    raise CustomError(status.HTTP_400_BAD_REQUEST, "Unsupported_App")


@router.get("/health")
def health():
    return {
        "status": "online",
        "name": "NeuralAgent Local Bridge",
        "version": "0.3.0",
        "eyes_base_url": EYES_BASE_URL,
        "actions": [
            "open_app",
            "list_processes",
            "focus_app",
            "click",
            "type_text",
            "hotkey",
            "screenshot",
            "extract_ui",
        ],
        "inbox": {
            "status": "online",
            "storage": "sqlite",
            "modes": ["ask", "puter", "computer"],
        },
        "invocation_channel": {
            "status": "online",
            "acks": True,
            "tasks": True,
            "events": True,
        },
    }


@router.get("/messages")
def list_messages(after_id: int = 0, x_bridge_token: str | None = Header(default=None)):
    _require_token(x_bridge_token)
    conn = _get_db()
    rows = conn.execute(
        """
        SELECT * FROM messages
        WHERE direction='in' AND status IN ('unread', 'processing')
        ORDER BY created_at ASC
        LIMIT 50
        """
    ).fetchall()
    conn.close()
    messages = []
    for index, row in enumerate(rows, start=after_id + 1):
        payload = json.loads(row["payload"])
        messages.append(
            {
                "id": index,
                "source": payload.get("source", row["channel_id"]),
                "text": payload.get("text", json.dumps(payload)),
                "mode": payload.get("mode", "ask"),
                "auto_execute": bool(payload.get("auto_execute", False)),
                "created_at": row["created_at"],
            }
        )
    return {"status": "success", "messages": messages}


@router.post("/messages")
def post_message(
    request: BridgeInboxMessageRequest,
    x_bridge_token: str | None = Header(default=None),
):
    _require_token(x_bridge_token)
    conn = _get_db()
    msg_id = _insert_message(
        conn,
        InvocationMessageRequest(
            channel_id=request.source,
            conversation_id="legacy",
            payload={
                "source": request.source,
                "text": request.text,
                "mode": request.mode,
                "auto_execute": request.auto_execute,
            },
        ),
        "in",
    )
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Message queued in Inbox", "id": msg_id}


@router.post("/messages/inbox")
def post_inbox(
    request: InvocationMessageRequest,
    x_bridge_token: str | None = Header(default=None),
):
    _require_token(x_bridge_token)
    conn = _get_db()
    msg_id = _insert_message(conn, request, "in")
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Message queued in Inbox", "id": msg_id}


@router.get("/messages/inbox")
def get_inbox(
    channel_id: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    x_bridge_token: str | None = Header(default=None),
):
    _require_token(x_bridge_token)
    conn = _get_db()
    ts = _now()
    params: list[object] = [ts, limit]
    channel_filter = ""
    if channel_id:
        channel_filter = "AND channel_id = ?"
        params.insert(1, channel_id)
    rows = conn.execute(
        f"""
        SELECT * FROM messages
        WHERE direction='in'
          AND (status='unread' OR (status='processing' AND COALESCE(lease_until, 0) < ?))
          {channel_filter}
        ORDER BY created_at ASC
        LIMIT ?
        """,
        params,
    ).fetchall()
    for row in rows:
        conn.execute(
            """
            UPDATE messages
            SET status='processing', lease_until=?, updated_at=?
            WHERE id=?
            """,
            (ts + MESSAGE_LEASE_SECONDS, ts, row["id"]),
        )
        _insert_event(
            conn,
            row["channel_id"],
            "message.leased",
            {"message_id": row["id"], "conversation_id": row["conversation_id"]},
        )
    conn.commit()
    conn.close()
    return {
        "status": "success",
        "messages": [_message_row(row, "processing") for row in rows],
    }


@router.post("/messages/inbox/{message_id}/ack")
def ack_inbox(
    message_id: str,
    request: InvocationAckRequest,
    x_bridge_token: str | None = Header(default=None),
):
    _require_token(x_bridge_token)
    final_status = "failed" if request.status == "failed" else "done"
    conn = _get_db()
    row = conn.execute("SELECT * FROM messages WHERE id=? AND direction='in'", (message_id,)).fetchone()
    if not row:
        conn.close()
        raise CustomError(status.HTTP_404_NOT_FOUND, "Message_Not_Found")
    ts = _now()
    conn.execute(
        "UPDATE messages SET status=?, error=?, lease_until=NULL, updated_at=? WHERE id=?",
        (final_status, request.error, ts, message_id),
    )
    _insert_event(
        conn,
        row["channel_id"],
        "message.acked",
        {
            "message_id": message_id,
            "conversation_id": row["conversation_id"],
            "status": final_status,
            "error": request.error,
        },
    )
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Inbox message acknowledged", "id": message_id}


@router.post("/messages/outbox")
def post_outbox(
    request: InvocationMessageRequest,
    x_bridge_token: str | None = Header(default=None),
):
    _require_token(x_bridge_token)
    conn = _get_db()
    msg_id = _insert_message(conn, request, "out")
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Message queued in Outbox", "id": msg_id}


@router.get("/messages/outbox")
def get_outbox(
    channel_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    x_bridge_token: str | None = Header(default=None),
):
    _require_token(x_bridge_token)
    conn = _get_db()
    rows = conn.execute(
        """
        SELECT * FROM messages
        WHERE direction='out' AND status='unread' AND channel_id=?
        ORDER BY created_at ASC
        LIMIT ?
        """,
        (channel_id, limit),
    ).fetchall()
    conn.close()
    return {"status": "success", "messages": [_message_row(row) for row in rows]}


@router.post("/messages/outbox/{message_id}/ack")
def ack_outbox(
    message_id: str,
    request: InvocationAckRequest,
    x_bridge_token: str | None = Header(default=None),
):
    _require_token(x_bridge_token)
    final_status = "failed" if request.status == "failed" else "read"
    conn = _get_db()
    row = conn.execute("SELECT * FROM messages WHERE id=? AND direction='out'", (message_id,)).fetchone()
    if not row:
        conn.close()
        raise CustomError(status.HTTP_404_NOT_FOUND, "Message_Not_Found")
    ts = _now()
    conn.execute(
        "UPDATE messages SET status=?, error=?, updated_at=? WHERE id=?",
        (final_status, request.error, ts, message_id),
    )
    _insert_event(
        conn,
        row["channel_id"],
        "message.acked",
        {
            "message_id": message_id,
            "conversation_id": row["conversation_id"],
            "status": final_status,
            "error": request.error,
        },
    )
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Outbox message acknowledged", "id": message_id}


@router.post("/tasks")
def create_task(
    request: InvocationTaskRequest,
    x_bridge_token: str | None = Header(default=None),
):
    _require_token(x_bridge_token)
    task_id = str(uuid.uuid4())
    ts = _now()
    task_status = "waiting_confirmation" if request.require_confirmation else "queued"
    conn = _get_db()
    conn.execute(
        """
        INSERT INTO tasks
            (id, channel_id, conversation_id, tool_name, input, status, result, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?)
        """,
        (
            task_id,
            request.channel_id,
            request.conversation_id,
            request.tool_name,
            json.dumps(request.input),
            task_status,
            ts,
            ts,
        ),
    )
    _insert_event(
        conn,
        request.channel_id,
        "task.created",
        {
            "task_id": task_id,
            "conversation_id": request.conversation_id,
            "tool_name": request.tool_name,
            "status": task_status,
        },
        task_id,
    )
    conn.commit()
    row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    conn.close()
    return {"status": "success", "task": _task_row(row)}


@router.get("/tasks")
def list_tasks(
    channel_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    x_bridge_token: str | None = Header(default=None),
):
    _require_token(x_bridge_token)
    conn = _get_db()
    if channel_id:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE channel_id=? ORDER BY created_at DESC LIMIT ?",
            (channel_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    conn.close()
    return {"status": "success", "tasks": [_task_row(row) for row in rows]}


@router.get("/tasks/{task_id}")
def get_task(task_id: str, x_bridge_token: str | None = Header(default=None)):
    _require_token(x_bridge_token)
    conn = _get_db()
    row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    conn.close()
    if not row:
        raise CustomError(status.HTTP_404_NOT_FOUND, "Task_Not_Found")
    return {"status": "success", "task": _task_row(row)}


@router.post("/tasks/{task_id}/status")
def update_task_status(
    task_id: str,
    request: InvocationTaskStatusRequest,
    x_bridge_token: str | None = Header(default=None),
):
    _require_token(x_bridge_token)
    conn = _get_db()
    row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    if not row:
        conn.close()
        raise CustomError(status.HTTP_404_NOT_FOUND, "Task_Not_Found")
    ts = _now()
    conn.execute(
        "UPDATE tasks SET status=?, result=?, updated_at=? WHERE id=?",
        (request.status, json.dumps(request.result) if request.result is not None else row["result"], ts, task_id),
    )
    _insert_event(
        conn,
        row["channel_id"],
        "task.status_changed",
        {
            "task_id": task_id,
            "conversation_id": row["conversation_id"],
            "status": request.status,
            "result": request.result,
        },
        task_id,
    )
    conn.commit()
    updated = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    conn.close()
    return {"status": "success", "task": _task_row(updated)}


@router.post("/events")
def post_event(
    request: InvocationEventRequest,
    x_bridge_token: str | None = Header(default=None),
):
    _require_token(x_bridge_token)
    conn = _get_db()
    event_id = _insert_event(
        conn,
        request.channel_id,
        request.event_type,
        request.payload,
        request.task_id,
    )
    conn.commit()
    conn.close()
    return {"status": "success", "id": event_id}


@router.get("/events")
def list_events(
    channel_id: str | None = None,
    after: float = 0,
    limit: int = Query(default=50, ge=1, le=200),
    x_bridge_token: str | None = Header(default=None),
):
    _require_token(x_bridge_token)
    conn = _get_db()
    if channel_id:
        rows = conn.execute(
            """
            SELECT * FROM events
            WHERE channel_id=? AND created_at > ?
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (channel_id, after, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT * FROM events
            WHERE created_at > ?
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (after, limit),
        ).fetchall()
    conn.close()
    return {"status": "success", "events": [_event_row(row) for row in rows]}


def _eyes_get(path: str) -> dict:
    try:
        response = requests.get(f"{EYES_BASE_URL}{path}", timeout=12)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        raise CustomError(status.HTTP_502_BAD_GATEWAY, f"Eyes_Bridge_Unavailable: {exc}")


def _eyes_post(path: str, payload: dict) -> dict:
    try:
        response = requests.post(f"{EYES_BASE_URL}{path}", json=payload, timeout=12)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        raise CustomError(status.HTTP_502_BAD_GATEWAY, f"Eyes_Bridge_Unavailable: {exc}")


@router.post("/actions", response_model=BridgeActionResponse)
def run_action(request: BridgeActionRequest, x_bridge_token: str | None = Header(default=None)):
    _require_token(x_bridge_token)

    if request.action == "open_app":
        executable = _resolve_app(request.app_name)
        if executable.endswith(":"):
            os.startfile(executable)
        else:
            subprocess.Popen([executable], shell=False)
        return BridgeActionResponse(
            status="success",
            message=f"Opened {executable}",
            data={"app": executable},
        )

    if request.action == "focus_app":
        if not request.app_name:
            raise CustomError(status.HTTP_400_BAD_REQUEST, "Missing_App_Name")
        data = _eyes_post("/focus", {"app_name": request.app_name})
        return BridgeActionResponse(status="success", message="Focus requested", data=data)

    if request.action == "click":
        if request.x is None or request.y is None:
            raise CustomError(status.HTTP_400_BAD_REQUEST, "Missing_Coordinates")
        data = _eyes_post(
            "/click",
            {
                "x": request.x,
                "y": request.y,
                "clicks": request.clicks,
                "button": request.button,
            },
        )
        return BridgeActionResponse(status="success", message="Click executed", data=data)

    if request.action == "type_text":
        if not request.text:
            raise CustomError(status.HTTP_400_BAD_REQUEST, "Missing_Text")
        data = _eyes_post("/type", {"text": request.text})
        return BridgeActionResponse(status="success", message="Text typed", data=data)

    if request.action == "hotkey":
        if not request.keys:
            raise CustomError(status.HTTP_400_BAD_REQUEST, "Missing_Keys")
        data = _eyes_post("/hotkey", {"keys": request.keys})
        return BridgeActionResponse(status="success", message="Hotkey executed", data=data)

    if request.action == "screenshot":
        data = _eyes_get("/screenshot")
        return BridgeActionResponse(status="success", message="Screenshot captured", data=data)

    if request.action == "extract_ui":
        data = _eyes_get("/extract_ui")
        return BridgeActionResponse(status="success", message="UI extracted", data=data)

    if request.action == "list_processes":
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        processes = []
        for line in result.stdout.splitlines()[:80]:
            parts = [part.strip('"') for part in line.split('","')]
            if len(parts) >= 2:
                processes.append({"name": parts[0], "pid": parts[1]})
        return BridgeActionResponse(
            status="success",
            message="Process list captured",
            data={"processes": processes},
        )

    raise CustomError(status.HTTP_400_BAD_REQUEST, "Unsupported_Action")
