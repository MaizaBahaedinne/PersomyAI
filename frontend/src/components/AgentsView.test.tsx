import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AgentsView } from "@/components/AgentsView";
import { adminUser, jsonResponse, renderWithI18n } from "@/test/utils";

let auth: any;
vi.mock("@/lib/auth", () => ({ useAuth: () => auth }));
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
  scopes: [],
  tools: [],
  autonomy_levels: [1, 2, 3],
};

const agent = (id: string, name: string, status: string, department = "sales") => ({
  id,
  identity_key: `agt_${id}`,
  name,
  department,
  role: "Assistant",
  skills: [],
  status,
  autonomy_level: 1,
  updated_at: "2026-11-19T10:00:00Z",
});

const page = { items: [agent("1", "Alpha", "ACTIVE"), agent("2", "Beta", "DRAFT", "finance")], total: 2, limit: 25, offset: 0 };

function setAuth(permissions: string[]) {
  auth = { user: adminUser, permissions, can: (p: string) => permissions.includes(p) };
}

function route(emergency: Record<string, unknown> = { active: false, at: null, by: null, paused_agents: 0 }) {
  return (url: string, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    if (url.includes("/agents/catalog")) return Promise.resolve(jsonResponse(catalog));
    if (url.includes("/agents/emergency-stop")) {
      if (method === "POST") return Promise.resolve(jsonResponse({ active: true, at: "x", by: "y", paused_agents: 2 }));
      if (method === "DELETE") return Promise.resolve(jsonResponse({ active: false, at: null, by: null, paused_agents: 0 }));
      return Promise.resolve(jsonResponse(emergency));
    }
    if (method === "POST") return Promise.resolve(jsonResponse(agent("3", "Gamma", "DRAFT"), 201));
    return Promise.resolve(jsonResponse(page));
  };
}

describe("AgentsView", () => {
  const fetchMock = vi.fn();
  beforeEach(() => vi.stubGlobal("fetch", fetchMock));
  afterEach(() => {
    fetchMock.mockReset();
    vi.unstubAllGlobals();
  });

  it("lecture seule : liste traduite sans bouton de création ni d'arrêt d'urgence", async () => {
    setAuth(["agents:read"]);
    fetchMock.mockImplementation(route());
    renderWithI18n(<AgentsView />);
    await screen.findByText("Alpha");
    const row = screen.getAllByRole("row").find((r) => within(r).queryByText("Beta"))!;
    expect(within(row).getByText("Finance")).toBeInTheDocument();
    expect(within(row).getByText("Brouillon")).toBeInTheDocument();
    expect(within(row).getByRole("link", { name: "Ouvrir" })).toHaveAttribute("href", "/agents/2");
    expect(screen.queryByRole("button", { name: "Nouvel agent" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Arrêt d'urgence" })).not.toBeInTheDocument();
    expect(screen.getByText(/Lecture seule/)).toBeInTheDocument();
  });

  it("affiche un état vide honnête sans agent", async () => {
    setAuth(["agents:read"]);
    fetchMock.mockImplementation((url: string) =>
      Promise.resolve(
        url.includes("/catalog")
          ? jsonResponse(catalog)
          : url.includes("emergency")
            ? jsonResponse({ active: false, at: null, by: null, paused_agents: 0 })
            : jsonResponse({ items: [], total: 0, limit: 25, offset: 0 }),
      ),
    );
    renderWithI18n(<AgentsView />);
    expect(await screen.findByText("Aucun agent pour le moment.")).toBeInTheDocument();
  });

  it("filtre par statut via l'API", async () => {
    setAuth(["agents:read"]);
    fetchMock.mockImplementation(route());
    renderWithI18n(<AgentsView />);
    await screen.findByText("Alpha");
    await screen.findByRole("option", { name: "Actif" });
    fireEvent.change(screen.getByLabelText("Statut"), { target: { value: "ACTIVE" } });
    await waitFor(() => expect(fetchMock.mock.calls.some(([u]) => String(u).includes("status=ACTIVE"))).toBe(true));
  });

  it("arrêt d'urgence : confirmation puis POST, résultat réel affiché", async () => {
    setAuth(["agents:read", "agents:write"]);
    fetchMock.mockImplementation(route());
    renderWithI18n(<AgentsView />);
    await screen.findByText("Alpha");
    fireEvent.click(screen.getByRole("button", { name: "Arrêt d'urgence" }));
    const dialog = screen.getByRole("dialog");
    expect(fetchMock.mock.calls.some(([, i]) => i?.method === "POST")).toBe(false);
    fireEvent.click(within(dialog).getByRole("button", { name: "Confirmer" }));
    expect(await screen.findByText(/2 agent\(s\) suspendu\(s\)/)).toBeInTheDocument();
    const post = fetchMock.mock.calls.find(([, i]) => i?.method === "POST")!;
    expect(String(post[0])).toBe("/api/v1/agents/emergency-stop");
  });

  it("arrêt d'urgence actif : bannière, levée réservée à agents:grant", async () => {
    setAuth(["agents:read", "agents:write"]);
    fetchMock.mockImplementation(route({ active: true, at: "x", by: "y", paused_agents: 0 }));
    const { unmount } = renderWithI18n(<AgentsView />);
    expect(await screen.findByText(/Arrêt d'urgence actif/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Lever l'arrêt d'urgence" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Arrêt d'urgence" })).not.toBeInTheDocument();
    unmount();

    setAuth(["agents:read", "agents:write", "agents:grant"]);
    renderWithI18n(<AgentsView />);
    fireEvent.click(await screen.findByRole("button", { name: "Lever l'arrêt d'urgence" }));
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Confirmer" }));
    expect(await screen.findByText("Arrêt d'urgence levé.")).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([, i]) => i?.method === "DELETE")).toBe(true);
  });

  it("création : envoie les champs et sépare les compétences", async () => {
    setAuth(["agents:read", "agents:write"]);
    fetchMock.mockImplementation(route());
    renderWithI18n(<AgentsView />);
    await screen.findByText("Alpha");
    await screen.findByRole("option", { name: "Finance" });
    fireEvent.click(screen.getByRole("button", { name: "Nouvel agent" }));
    fireEvent.change(screen.getByLabelText("Nom"), { target: { value: "Gamma" } });
    fireEvent.change(screen.getByLabelText("Rôle"), { target: { value: "Analyste" } });
    fireEvent.change(screen.getByLabelText("Mission"), { target: { value: "Analyser" } });
    fireEvent.change(screen.getByLabelText("Compétences"), { target: { value: "a, b ,," } });
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Créer" }));
    expect(await screen.findByText(/sans aucun accès/)).toBeInTheDocument();
    const post = fetchMock.mock.calls.find(([, i]) => i?.method === "POST")!;
    expect(JSON.parse(post[1].body)).toEqual({
      name: "Gamma",
      department: "sales",
      role: "Analyste",
      mission: "Analyser",
      skills: ["a", "b"],
    });
  });

  it("affiche l'erreur de l'API traduite (nom déjà pris)", async () => {
    setAuth(["agents:read", "agents:write"]);
    fetchMock.mockImplementation((url: string, init?: RequestInit) => {
      if (init?.method === "POST") {
        return Promise.resolve(jsonResponse({ error: { code: "agent_name_taken", message: "x" } }, 409));
      }
      return route()(url, init);
    });
    renderWithI18n(<AgentsView />);
    await screen.findByText("Alpha");
    await screen.findByRole("option", { name: "Finance" });
    fireEvent.click(screen.getByRole("button", { name: "Nouvel agent" }));
    fireEvent.change(screen.getByLabelText("Nom"), { target: { value: "Alpha" } });
    fireEvent.change(screen.getByLabelText("Rôle"), { target: { value: "R" } });
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Créer" }));
    expect(await screen.findByText("Un agent porte déjà ce nom.")).toBeInTheDocument();
  });

  it("affiche une erreur avec réessai si le chargement échoue", async () => {
    setAuth(["agents:read"]);
    fetchMock.mockResolvedValue(jsonResponse({ error: { code: "internal_error", message: "x" } }, 500));
    renderWithI18n(<AgentsView />);
    expect(await screen.findByText("Impossible de charger les agents.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Réessayer" })).toBeInTheDocument();
  });
});
