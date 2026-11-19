import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AgentDetailView } from "@/components/AgentDetailView";
import { adminUser, jsonResponse, renderWithI18n } from "@/test/utils";

let auth: any;
const push = vi.fn();
vi.mock("@/lib/auth", () => ({ useAuth: () => auth }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: any) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

const catalog = {
  departments: ["sales", "finance"],
  statuses: ["DRAFT", "ACTIVE", "PAUSED", "ERROR", "DISABLED"],
  settable_statuses: ["DRAFT", "ACTIVE", "PAUSED", "DISABLED"],
  scopes: [
    { code: "crm:read", critical: false },
    { code: "email:send", critical: true },
  ],
  tools: ["web_search", "crm"],
  autonomy_levels: [1, 2, 3],
};

const baseAgent = {
  id: "a1",
  identity_key: "agt_0123456789abcdef",
  name: "Alpha",
  description: "",
  department: "sales",
  role: "Assistant",
  mission: "Vendre",
  skills: ["prospection"],
  status: "ACTIVE",
  autonomy_level: 1,
  config: { tone: "formel" },
  max_actions_per_day: 50,
  monthly_budget_cents: 0,
  access_revoked_at: null,
  created_at: "2026-11-19T10:00:00Z",
  updated_at: "2026-11-19T10:00:00Z",
  permissions: ["crm:read"],
  tools: [],
};

const history = {
  items: [
    {
      id: "e1",
      created_at: "2026-11-19T10:00:00Z",
      actor_label: "admin@example.com",
      action: "agent.create",
      target_type: "agent",
      target_id: "a1",
      status: "success",
      ip_address: null,
      details: null,
    },
  ],
  total: 1,
  limit: 20,
  offset: 0,
};

function setAuth(permissions: string[]) {
  auth = { user: adminUser, permissions, can: (p: string) => permissions.includes(p) };
}

function route(agent: Record<string, unknown> = baseAgent) {
  return (url: string, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    if (url.includes("/catalog")) return Promise.resolve(jsonResponse(catalog));
    if (url.includes("/history")) return Promise.resolve(jsonResponse(history));
    if (method === "DELETE") return Promise.resolve(jsonResponse(null, 204));
    return Promise.resolve(jsonResponse(agent));
  };
}

const calls = (fetchMock: ReturnType<typeof vi.fn>, method: string) =>
  fetchMock.mock.calls.filter(([, i]) => (i?.method ?? "GET") === method);

describe("AgentDetailView", () => {
  const fetchMock = vi.fn();
  beforeEach(() => {
    push.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });
  afterEach(() => {
    fetchMock.mockReset();
    vi.unstubAllGlobals();
  });

  it("lecture seule : aucune action de modification, permissions affichées en texte", async () => {
    setAuth(["agents:read"]);
    fetchMock.mockImplementation(route());
    renderWithI18n(<AgentDetailView id="a1" />);
    expect(await screen.findByRole("heading", { name: "Alpha" })).toBeInTheDocument();
    expect(screen.getByText("agt_0123456789abcdef")).toBeInTheDocument();
    expect(screen.getByText("CRM : lecture")).toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Mettre en pause" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Enregistrer" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Révoquer tous les accès" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Supprimer" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Nom")).toBeDisabled();
    expect(screen.getByText("Agent créé")).toBeInTheDocument(); // historique
  });

  it("affiche l'erreur traduite si l'agent est introuvable", async () => {
    setAuth(["agents:read"]);
    fetchMock.mockImplementation((url: string) =>
      Promise.resolve(
        url.includes("/catalog")
          ? jsonResponse(catalog)
          : jsonResponse({ error: { code: "agent_not_found", message: "x" } }, 404),
      ),
    );
    renderWithI18n(<AgentDetailView id="zzz" />);
    expect(await screen.findByText("Agent introuvable.")).toBeInTheDocument();
  });

  it("ne propose que les transitions valides et demande confirmation", async () => {
    setAuth(["agents:read", "agents:write"]);
    fetchMock.mockImplementation(route());
    renderWithI18n(<AgentDetailView id="a1" />);
    await screen.findByRole("heading", { name: "Alpha" });
    expect(screen.queryByRole("button", { name: "Activer" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Désactiver" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Mettre en pause" }));
    expect(calls(fetchMock, "POST")).toHaveLength(0);
    const dialog = screen.getByRole("dialog");
    fireEvent.change(screen.getByLabelText("Motif (facultatif)"), { target: { value: "audit" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Confirmer" }));
    await waitFor(() => expect(calls(fetchMock, "POST")).toHaveLength(1));
    const [url, init] = calls(fetchMock, "POST")[0];
    expect(String(url)).toBe("/api/v1/agents/a1/status");
    expect(JSON.parse(init.body)).toEqual({ status: "PAUSED", reason: "audit" });
    expect(await screen.findByText("Statut mis à jour.")).toBeInTheDocument();
  });

  it("affiche l'erreur de transition renvoyée par le serveur", async () => {
    setAuth(["agents:read", "agents:write"]);
    fetchMock.mockImplementation((url: string, init?: RequestInit) =>
      init?.method === "POST"
        ? Promise.resolve(jsonResponse({ error: { code: "emergency_stop_active", message: "x" } }, 409))
        : route({ ...baseAgent, status: "PAUSED" })(url, init),
    );
    renderWithI18n(<AgentDetailView id="a1" />);
    await screen.findByRole("heading", { name: "Alpha" });
    fireEvent.click(screen.getByRole("button", { name: "Activer" }));
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Confirmer" }));
    expect(await screen.findByText(/L'arrêt d'urgence est actif/)).toBeInTheDocument();
  });

  it("ADMIN : autonomie supérieure et budget non attribuables, config invalide refusée côté client", async () => {
    setAuth(["agents:read", "agents:write"]);
    fetchMock.mockImplementation(route());
    renderWithI18n(<AgentDetailView id="a1" />);
    await screen.findByRole("heading", { name: "Alpha" });
    expect(screen.getByRole("option", { name: /Niveau 2/ })).toBeDisabled();
    expect(screen.getByRole("option", { name: /Niveau 1/ })).not.toBeDisabled();
    fireEvent.change(screen.getByLabelText("Configuration (JSON)"), { target: { value: "[1,2]" } });
    fireEvent.click(screen.getByRole("button", { name: "Enregistrer" }));
    expect(await screen.findByText(/JSON invalide/)).toBeInTheDocument();
    expect(calls(fetchMock, "PATCH")).toHaveLength(0);
  });

  it("enregistre les paramètres sans envoyer les champs réservés non modifiés", async () => {
    setAuth(["agents:read", "agents:write"]);
    fetchMock.mockImplementation(route());
    renderWithI18n(<AgentDetailView id="a1" />);
    await screen.findByRole("heading", { name: "Alpha" });
    fireEvent.change(screen.getByLabelText("Rôle"), { target: { value: "Responsable" } });
    fireEvent.click(screen.getByRole("button", { name: "Enregistrer" }));
    await waitFor(() => expect(calls(fetchMock, "PATCH")).toHaveLength(1));
    const body = JSON.parse(calls(fetchMock, "PATCH")[0][1].body);
    expect(body.role).toBe("Responsable");
    expect(body.skills).toEqual(["prospection"]);
    expect(body.config).toEqual({ tone: "formel" });
    expect(body).not.toHaveProperty("autonomy_level");
    expect(body).not.toHaveProperty("monthly_budget_cents");
  });

  it("agents:grant : coche permissions et outils puis enregistre les deux listes", async () => {
    setAuth(["agents:read", "agents:write", "agents:grant"]);
    fetchMock.mockImplementation(route());
    renderWithI18n(<AgentDetailView id="a1" />);
    await screen.findByRole("heading", { name: "Alpha" });
    expect(screen.getByText("critique")).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: /CRM : lecture/ })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: /E-mail : envoyer/ })).not.toBeChecked();
    fireEvent.click(screen.getByRole("checkbox", { name: /E-mail : envoyer/ }));
    fireEvent.click(screen.getByRole("checkbox", { name: "Recherche web" }));
    const section = screen.getByRole("region", { name: "Permissions" });
    fireEvent.click(within(section).getByRole("button", { name: "Enregistrer" }));
    await waitFor(() => expect(calls(fetchMock, "PUT")).toHaveLength(2));
    const [perm, tool] = calls(fetchMock, "PUT");
    expect(String(perm[0])).toBe("/api/v1/agents/a1/permissions");
    expect(JSON.parse(perm[1].body)).toEqual({ permissions: ["crm:read", "email:send"] });
    expect(String(tool[0])).toBe("/api/v1/agents/a1/tools");
    expect(JSON.parse(tool[1].body)).toEqual({ tools: ["web_search"] });
  });

  it("révocation des accès : confirmation obligatoire", async () => {
    setAuth(["agents:read", "agents:write", "agents:grant"]);
    fetchMock.mockImplementation(route());
    renderWithI18n(<AgentDetailView id="a1" />);
    await screen.findByRole("heading", { name: "Alpha" });
    expect(screen.queryByRole("button", { name: "Supprimer" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Révoquer tous les accès" }));
    expect(calls(fetchMock, "POST")).toHaveLength(0);
    expect(screen.getByRole("dialog")).toHaveTextContent("Alpha");
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Confirmer" }));
    await waitFor(() => expect(String(calls(fetchMock, "POST")[0][0])).toBe("/api/v1/agents/a1/revoke-access"));
  });

  it("suppression : réservée à agents:delete, redirige vers la liste", async () => {
    setAuth(["agents:read", "agents:write", "agents:grant", "agents:delete"]);
    fetchMock.mockImplementation(route());
    renderWithI18n(<AgentDetailView id="a1" />);
    await screen.findByRole("heading", { name: "Alpha" });
    fireEvent.click(screen.getByRole("button", { name: "Supprimer" }));
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Confirmer" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/agents"));
    expect(String(calls(fetchMock, "DELETE")[0][0])).toBe("/api/v1/agents/a1");
  });

  it("signale des accès révoqués", async () => {
    setAuth(["agents:read"]);
    fetchMock.mockImplementation(route({ ...baseAgent, status: "DISABLED", access_revoked_at: "2026-11-19T10:00:00Z", permissions: [] }));
    renderWithI18n(<AgentDetailView id="a1" />);
    expect(await screen.findByText(/Accès révoqués le/)).toBeInTheDocument();
    expect(screen.getAllByText("Aucune")).toHaveLength(2); // ni permission ni outil
  });
});
