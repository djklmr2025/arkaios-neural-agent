from pathlib import Path
import os


APP_DATA = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA")
if APP_DATA:
    WORKSPACE_ROOT = Path(APP_DATA) / "NeuralAgent" / "workspace"
else:
    WORKSPACE_ROOT = Path(__file__).resolve().parents[1] / "workspace"


def resolve_workspace_path(relative_path: str) -> Path:
    if not relative_path or relative_path.strip() in {"", "/", "\\"}:
        raise PermissionError("Invalid workspace path")

    root = WORKSPACE_ROOT.resolve()
    candidate = (root / relative_path).resolve()

    if candidate != root and root not in candidate.parents:
        raise PermissionError("Only files inside the NeuralAgent workspace are allowed")

    return candidate


def ensure_workspace() -> Path:
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    return WORKSPACE_ROOT
