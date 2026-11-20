"""Interface commune des fournisseurs d'IA.

Fournisseur local supporté : `ollama` (auto-hébergé).
Le fournisseur actif se règle via `AI_PROVIDER`.
"""

from dataclasses import dataclass
import json
import socket
from typing import Callable, Protocol
from urllib import error, request

from app.core.config import get_settings
from app.core.errors import Conflict


class ProviderNotConfigured(Conflict):
    code = "provider_not_configured"


class ProviderError(Exception):
    """Échec d'un appel au fournisseur. Seul `code` est conservé (le message peut contenir des données sensibles)."""

    def __init__(self, code: str = "provider_error", message: str = ""):
        super().__init__(message or code)
        self.code = code


@dataclass(frozen=True)
class Completion:
    text: str
    cost_cents: int = 0
    tokens_in: int = 0
    tokens_out: int = 0


class Provider(Protocol):
    name: str
    paid: bool  # True si chaque appel entraîne un coût : soumis au budget mensuel de l'agent

    def complete(self, *, system: str, prompt: str, timeout_seconds: float) -> Completion: ...


class OllamaProvider:
    name = "ollama"
    paid = False

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model.strip()

    def complete(self, *, system: str, prompt: str, timeout_seconds: float) -> Completion:
        if not self.model:
            raise ProviderError("provider_not_configured", "OLLAMA_MODEL is empty")
        payload = {
            "model": self.model,
            "system": system,
            "prompt": prompt,
            "stream": False,
        }
        req = request.Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=timeout_seconds) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as exc:
            raise ProviderError("provider_http_error", str(exc.code)) from exc
        except (error.URLError, ConnectionError) as exc:
            raise ProviderError("provider_connection", str(exc)) from exc
        except (socket.timeout, TimeoutError) as exc:
            raise ProviderError("provider_timeout", str(exc)) from exc
        except json.JSONDecodeError as exc:
            raise ProviderError("provider_bad_response", "invalid JSON") from exc

        text = body.get("response")
        if not isinstance(text, str):
            raise ProviderError("provider_bad_response", "missing response text")
        return Completion(
            text=text,
            cost_cents=0,
            tokens_in=max(0, int(body.get("prompt_eval_count") or 0)),
            tokens_out=max(0, int(body.get("eval_count") or 0)),
        )


_REGISTRY: dict[str, Callable[[], Provider]] = {"ollama": OllamaProvider}


def get_provider() -> Provider:
    name = get_settings().ai_provider.strip().lower()
    factory = _REGISTRY.get(name)
    if factory is None:
        raise ProviderNotConfigured("No AI provider is configured")
    return factory()


def provider_info() -> dict:
    try:
        provider = get_provider()
    except ProviderNotConfigured:
        return {"name": get_settings().ai_provider.strip().lower() or "none", "configured": False, "paid": False}
    return {"name": provider.name, "configured": True, "paid": provider.paid}
