import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


APP_ALIASES = {
    "notepad": "notepad",
    "bloc": "notepad",
    "block": "notepad",
    "proceso": "list_processes",
    "procesos": "list_processes",
    "captura": "screenshot",
    "pantalla": "screenshot",
    "reproductor": "media player",
    "musica": "media player",
    "música": "media player",
    "media player": "media player",
    "windows media": "media player",
}

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

ARKAIOS_SYSTEM_PROMPT = """Eres ARKAIOS viviendo en Puter y operando en segundo plano.
Responde en espanol claro, breve y accionable.
Si el usuario pide tocar la computadora, explica que usaras el canal computer solo cuando este autorizado.
No inventes que hiciste acciones si solo respondiste texto."""


def _token_path() -> str:
    root = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(root, "NeuralAgent", "local_bridge_token.txt")


def _load_token() -> str:
    path = _token_path()
    if not os.path.exists(path):
        raise RuntimeError(f"No encontre token local: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        token = fh.read().strip()
    if not token:
        raise RuntimeError(f"Token local vacio: {path}")
    return token


class BridgeClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token

    def request(self, method: str, path: str, payload: dict | None = None) -> dict:
        data = None
        headers = {"X-Bridge-Token": self.token}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers=headers,
            method=method,
        )
        with urllib.request.urlopen(req, timeout=20) as response:
            raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else {}

    def inbox(self, channel_id: str, limit: int = 10) -> list[dict]:
        query = urllib.parse.urlencode({"channel_id": channel_id, "limit": limit})
        payload = self.request("GET", f"/messages/inbox?{query}")
        return payload.get("messages", [])

    def ack_inbox(self, message_id: str, status: str = "done", error: str | None = None) -> None:
        body = {"status": status}
        if error:
            body["error"] = error[:1000]
        self.request("POST", f"/messages/inbox/{message_id}/ack", body)

    def outbox(self, channel_id: str, conversation_id: str, result: dict) -> None:
        self.request(
            "POST",
            "/messages/outbox",
            {
                "channel_id": channel_id,
                "conversation_id": conversation_id,
                "payload": {
                    "source": "arkaios-worker",
                    "result": result,
                },
            },
        )

    def event(self, channel_id: str, event_type: str, payload: dict) -> None:
        self.request(
            "POST",
            "/events",
            {
                "channel_id": channel_id,
                "event_type": event_type,
                "payload": payload,
            },
        )

    def action(self, payload: dict) -> dict:
        return self.request("POST", "/actions", payload)


def _route_computer(client: BridgeClient, text: str) -> dict:
    lower = text.lower()
    if any(key in lower for key in ("notepad", "bloc", "block")):
        return client.action({"action": "open_app", "app_name": "notepad"})
    if any(key in lower for key in ("reproductor", "musica", "música", "media player", "windows media", "spotify")):
        app_name = "spotify" if "spotify" in lower else "media player"
        return client.action({"action": "open_app", "app_name": app_name})
    if "proceso" in lower:
        return client.action({"action": "list_processes"})
    if "captura" in lower or "pantalla" in lower:
        return client.action({"action": "screenshot"})
    return {
        "status": "needs-routing",
        "message": "Orden recibida por worker invisible. Falta mapear esta intencion a una accion local segura.",
        "text": text,
    }


def _route_puter(text: str) -> dict:
    return {
        "status": "puter-worker-received",
        "message": "Orden recibida por el worker. Las acciones visuales internas de Puter requieren la app ARKAIOS abierta o un worker Puter nativo.",
        "text": text,
    }


def _message_content(response: object) -> str:
    content = getattr(response, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part).strip()
    return str(response)


def _route_ask(text: str) -> dict:
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from utils import llm_provider

        requested_agents = [
            item.strip()
            for item in os.getenv(
                "ARKAIOS_WORKER_AGENTS",
                os.getenv("ARKAIOS_WORKER_AGENT", "planner"),
            ).split(",")
            if item.strip()
        ]
        for fallback in ("computer_use", "suggestor", "classifier", "title"):
            if fallback not in requested_agents:
                requested_agents.append(fallback)

        seen_configs: set[tuple[str, str]] = set()
        last_error = None
        missing = []
        puter_session_blocked = False

        for agent in requested_agents:
            config = llm_provider.get_model_config(agent)
            config_key = (config.model_type, config.model_id)
            if config_key in seen_configs:
                continue
            seen_configs.add(config_key)

            if not config.configured:
                missing.extend(config.missing)
                continue

            try:
                llm = llm_provider.get_llm(
                    agent=agent,
                    temperature=float(os.getenv("ARKAIOS_WORKER_TEMPERATURE", "0.2")),
                    max_tokens=int(os.getenv("ARKAIOS_WORKER_MAX_TOKENS", "900")),
                )
                response = llm.invoke(
                    [
                        SystemMessage(content=ARKAIOS_SYSTEM_PROMPT),
                        HumanMessage(content=text),
                    ]
                )
                return {
                    "status": "success",
                    "agent": agent,
                    "model_type": config.model_type,
                    "model_id": config.model_id,
                    "message": _message_content(response),
                }
            except Exception as exc:
                last_error = str(exc)
                if "only available to user sessions" in last_error.lower():
                    puter_session_blocked = True
                    continue

        if puter_session_blocked:
            return {
                "status": "ai-provider-requires-browser-session",
                "message": "Puter AI rechazo la llamada server-side. Para IA invisible real configura GEMINI_API_KEY, OPENAI_API_KEY u otro proveedor server-side; para Puter AI usa el worker nativo dentro de Puter con sesion de usuario.",
                "text": text,
            }

        if missing:
            return {
                "status": "ai-not-configured",
                "message": f"ARKAIOS recibio el mensaje, pero falta configurar: {', '.join(sorted(set(missing)))}.",
                "text": text,
            }

        return {
            "status": "ai-error",
            "message": "ARKAIOS recibio el mensaje, pero el proveedor AI fallo.",
            "error": last_error or "unknown AI provider error",
            "text": text,
        }
    except Exception as exc:
        return {
            "status": "ai-error",
            "message": "ARKAIOS recibio el mensaje, pero el proveedor AI fallo.",
            "error": str(exc),
            "text": text,
        }


def handle_message(client: BridgeClient, message: dict) -> None:
    payload = message.get("payload") or {}
    channel_id = message["channel_id"]
    conversation_id = message["conversation_id"]
    text = payload.get("text") or json.dumps(payload, ensure_ascii=False)
    mode = payload.get("mode", "ask")
    auto_execute = bool(payload.get("auto_execute", False))

    client.event(
        channel_id,
        "worker.message_received",
        {
            "message_id": message["id"],
            "conversation_id": conversation_id,
            "mode": mode,
            "auto_execute": auto_execute,
        },
    )

    if not auto_execute:
        result = {
            "status": "waiting_confirmation",
            "message": "ARKAIOS recibio la orden en segundo plano, pero requiere autorizacion porque auto_execute=false.",
            "text": text,
        }
        client.outbox(channel_id, conversation_id, result)
        client.ack_inbox(message["id"], "done")
        return

    try:
        if mode == "computer":
            result = _route_computer(client, text)
        elif mode == "puter":
            result = _route_puter(text)
        else:
            result = _route_ask(text)
        client.outbox(channel_id, conversation_id, result)
        client.ack_inbox(message["id"], "done")
        client.event(
            channel_id,
            "worker.message_completed",
            {"message_id": message["id"], "conversation_id": conversation_id},
        )
    except Exception as exc:
        error = str(exc)
        client.outbox(channel_id, conversation_id, {"status": "failed", "error": error})
        client.ack_inbox(message["id"], "failed", error)
        client.event(
            channel_id,
            "worker.message_failed",
            {"message_id": message["id"], "conversation_id": conversation_id, "error": error},
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="ARKAIOS invisible invocation worker")
    parser.add_argument("--bridge-url", default="http://127.0.0.1:8000/local-bridge")
    parser.add_argument("--channel-id", default="neuro-login")
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    client = BridgeClient(args.bridge_url, _load_token())
    print(f"ARKAIOS worker online. channel={args.channel_id} bridge={args.bridge_url}", flush=True)

    while True:
        try:
            messages = client.inbox(args.channel_id)
            for message in messages:
                handle_message(client, message)
        except urllib.error.URLError as exc:
            print(f"Bridge unavailable: {exc}", flush=True)
        except Exception as exc:
            print(f"Worker error: {exc}", flush=True)

        if args.once:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
