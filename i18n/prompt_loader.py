import importlib
import threading
from types import ModuleType
from typing import Any


_PROMPT_RELOAD_LOCK = threading.Lock()


def load_localized_values(module: ModuleType, *names: str) -> tuple[Any, ...]:
    """Reload and copy locale-dependent module values atomically."""
    with _PROMPT_RELOAD_LOCK:
        reloaded = importlib.reload(module)
        return tuple(getattr(reloaded, name) for name in names)
