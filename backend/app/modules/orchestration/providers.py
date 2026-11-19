"""Interface commune des fournisseurs d'IA.

Aucun fournisseur réel n'est encore implémenté : le registre est vide, donc `get_provider()` lève
`ProviderNotConfigured` et aucune exécution de tâche n'est possible. Aucune réponse n'est simulée.
Pour ajouter un fournisseur : implémenter `Provider`, l'enregistrer dans `_REGISTRY`, puis renseigner
`AI_PROVIDER`. Les clés d'API ne doivent jamais être stockées en base ni renvoyées au frontend.
"""

from dataclasses import dataclass
from typing import Callable, Protocol

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


_REGISTRY: dict[str, Callable[[], Provider]] = {}


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
