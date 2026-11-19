import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { TasksView } from "@/components/TasksView";
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

const task = (over: Record<string, unknown> = {}) => ({
  id: "t1",
  title: "Relancer les devis",
  priority: "NORMAL",
  status: "OPEN",
  mission_id: "m1",
  mission_title: "Q4",
  agent_id: "a1",
  agent_name: "Alpha",
  required_scope: "email:send",
  requires_approval: true,
  created_at: "2026-11-19T10:00:00Z",
  updated_at: "2026-11-19T10:00:00Z",
  ...over,
});

const page = (items: unknown[]) => ({ items, total: items.length, limit: 25, offset: 0 });

const catalog = {
  departments: [],
  statuses: [],
  settable_statuses: [],
  scopes: [
    { code: "crm:read", critical: false },
    { code: "email:send", critical: true },
  ],
  tools: [],
  autonomy_levels: [1, 2, 3],
};

function setAuth(permissions: string[]) {
  auth = { user: adminUser, permissions, can: (p: string) => permissions.includes(p) };
}

function route(items: unknown[]) {
  return (url: string, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    if (url.includes("/agents/catalog")) return Promise.resolve(jsonResponse(catalog));
    if (url.includes("/agents")) return Promise.resolve(jsonResponse(page([{ id: "a1", name: "Alpha", status: "ACTIVE" }])));
    if (url.includes("/missions")) return Promise.resolve(jsonResponse(page([{ id: "m1", title: "Q4" }])));
    if (method === "POST") return Promise.resolve(jsonResponse(task(), 201));
    return Promise.resolve(jsonResponse(page(items)));
  };
}

const calls = (fetchMock: ReturnType<typeof vi.fn>, method: string) =>
  fetchMock.mock.calls.filter(([, i]) => (i?.method ?? "GET") === method);

describe("TasksView", () => {
  const fetchMock = vi.fn();
  beforeEach(() => vi.stubGlobal("fetch", fetchMock));
  afterEach(() => {
    fetchMock.mockReset();
    vi.unstubAllGlobals();
  });

  it("affiche les tâches réelles avec statut, validation et lien", async () => {
    setAuth(["orchestration:read"]);
    fetchMock.mockImplementation(
      route([task(), task({ id: "t2", title: "Rapport", status: "AWAITING_APPROVAL", agent_id: null, agent_name: null, requires_approval: null })]),
    );
    renderWithI18n(<TasksView />);
    expect(await screen.findByText("Relancer les devis")).toBeInTheDocument();
    const rows = screen.getAllByRole("row");
    expect(within(rows[1]).getByText("Ouverte")).toBeInTheDocument();
    expect(within(rows[1]).getByText("Requise")).toBeInTheDocument();
    expect(within(rows[2]).getByText("En attente de validation")).toBeInTheDocument();
    expect(within(rows[2]).getByText("Non affectée")).toBeInTheDocument();
    expect(within(rows[1]).getByRole("link", { name: "Ouvrir" })).toHaveAttribute("href", "/tasks/t1");
  });

  it("lecture seule : pas de bouton de création", async () => {
    setAuth(["orchestration:read"]);
    fetchMock.mockImplementation(route([task()]));
    renderWithI18n(<TasksView />);
    await screen.findByText("Relancer les devis");
    expect(screen.queryByRole("button", { name: "Nouvelle tâche" })).not.toBeInTheDocument();
    expect(screen.getByText(/Lecture seule/)).toBeInTheDocument();
  });

  it("filtre par statut côté serveur", async () => {
    setAuth(["orchestration:read"]);
    fetchMock.mockImplementation(route([task()]));
    renderWithI18n(<TasksView />);
    await screen.findByText("Relancer les devis");
    fireEvent.change(screen.getByLabelText("Statut"), { target: { value: "AWAITING_APPROVAL" } });
    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([u]) => String(u).includes("status=AWAITING_APPROVAL"))).toBe(true),
    );
  });

  it("affiche l'état vide et l'erreur de chargement", async () => {
    setAuth(["orchestration:read"]);
    fetchMock.mockImplementation(route([]));
    const { unmount } = renderWithI18n(<TasksView />);
    expect(await screen.findByText("Aucune tâche pour le moment.")).toBeInTheDocument();
    unmount();
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({ error: { code: "internal_error", message: "x" } }, 500)));
    renderWithI18n(<TasksView />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Impossible de charger les tâches.");
  });

  it("crée une tâche avec les champs saisis", async () => {
    setAuth(["orchestration:read", "orchestration:write"]);
    fetchMock.mockImplementation(route([]));
    renderWithI18n(<TasksView />);
    fireEvent.click(await screen.findByRole("button", { name: "Nouvelle tâche" }));
    const dialog = await screen.findByRole("dialog");
    await within(dialog).findByRole("option", { name: "Alpha" });
    fireEvent.change(within(dialog).getByLabelText("Titre"), { target: { value: "Nouvelle" } });
    fireEvent.change(within(dialog).getByLabelText("Agent"), { target: { value: "a1" } });
    fireEvent.change(within(dialog).getByLabelText("Permission exigée"), { target: { value: "email:send" } });
    fireEvent.change(within(dialog).getByLabelText("Priorité"), { target: { value: "HIGH" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Créer" }));
    await waitFor(() => expect(calls(fetchMock, "POST")).toHaveLength(1));
    const [url, init] = calls(fetchMock, "POST")[0];
    expect(String(url)).toBe("/api/v1/tasks");
    expect(JSON.parse(init.body)).toEqual({
      title: "Nouvelle",
      description: "",
      priority: "HIGH",
      agent_id: "a1",
      required_scope: "email:send",
    });
    expect(await screen.findByText("Tâche créée.")).toBeInTheDocument();
  });

  it("affiche l'erreur traduite renvoyée à la création", async () => {
    setAuth(["orchestration:read", "orchestration:write"]);
    fetchMock.mockImplementation((url: string, init?: RequestInit) =>
      init?.method === "POST"
        ? Promise.resolve(jsonResponse({ error: { code: "agent_not_assignable", message: "x" } }, 409))
        : route([])(url, init),
    );
    renderWithI18n(<TasksView />);
    fireEvent.click(await screen.findByRole("button", { name: "Nouvelle tâche" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Titre"), { target: { value: "X" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Créer" }));
    expect(await within(dialog).findByRole("alert")).toBeInTheDocument();
    expect(within(dialog).getByRole("alert")).not.toHaveTextContent("error.");
  });
});
