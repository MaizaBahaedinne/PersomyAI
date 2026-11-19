import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MissionDetailView } from "@/components/MissionDetailView";
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

const mission = (over: Record<string, unknown> = {}) => ({
  id: "m1",
  title: "Campagne Q4",
  description: "Relances",
  status: "OPEN",
  created_at: "2026-11-19T10:00:00Z",
  updated_at: "2026-11-19T10:00:00Z",
  task_counts: { open: 1, total: 1 },
  ...over,
});

const tasks = {
  items: [
    {
      id: "t1",
      title: "Relancer",
      priority: "NORMAL",
      status: "OPEN",
      mission_id: "m1",
      mission_title: "Campagne Q4",
      agent_id: null,
      agent_name: null,
      required_scope: null,
      requires_approval: null,
      created_at: "2026-11-19T10:00:00Z",
      updated_at: "2026-11-19T10:00:00Z",
    },
  ],
  total: 1,
  limit: 100,
  offset: 0,
};

function setAuth(permissions: string[]) {
  auth = { user: adminUser, permissions, can: (p: string) => permissions.includes(p) };
}

function route(m = mission()) {
  return (url: string, init?: RequestInit) => {
    if (url.includes("/agents/catalog")) return Promise.resolve(jsonResponse({ scopes: [] }));
    if (url.includes("/agents")) return Promise.resolve(jsonResponse({ items: [], total: 0, limit: 200, offset: 0 }));
    if (url.includes("/tasks")) return Promise.resolve(jsonResponse(tasks));
    if (init?.method === "PATCH") return Promise.resolve(jsonResponse(m));
    return Promise.resolve(jsonResponse(m));
  };
}

const calls = (fetchMock: ReturnType<typeof vi.fn>, method: string) =>
  fetchMock.mock.calls.filter(([, i]) => (i?.method ?? "GET") === method);

describe("MissionDetailView", () => {
  const fetchMock = vi.fn();
  beforeEach(() => vi.stubGlobal("fetch", fetchMock));
  afterEach(() => {
    fetchMock.mockReset();
    vi.unstubAllGlobals();
  });

  it("lecture seule : détail et tâches sans aucune action", async () => {
    setAuth(["orchestration:read"]);
    fetchMock.mockImplementation(route());
    renderWithI18n(<MissionDetailView id="m1" />);
    expect(await screen.findByRole("heading", { name: "Campagne Q4" })).toBeInTheDocument();
    expect(await screen.findByText("Relancer")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Marquer comme terminée" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Enregistrer" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Nouvelle tâche" })).not.toBeInTheDocument();
    expect(String(fetchMock.mock.calls.find(([u]) => String(u).includes("/tasks"))![0])).toContain("mission_id=m1");
  });

  it("change le statut après confirmation", async () => {
    setAuth(["orchestration:read", "orchestration:write"]);
    fetchMock.mockImplementation(route());
    renderWithI18n(<MissionDetailView id="m1" />);
    await screen.findByRole("heading", { name: "Campagne Q4" });
    fireEvent.click(screen.getByRole("button", { name: "Marquer comme terminée" }));
    expect(calls(fetchMock, "PATCH")).toHaveLength(0);
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Confirmer" }));
    await waitFor(() => expect(calls(fetchMock, "PATCH")).toHaveLength(1));
    const [url, init] = calls(fetchMock, "PATCH")[0];
    expect(String(url)).toBe("/api/v1/missions/m1");
    expect(JSON.parse(init.body)).toEqual({ status: "DONE" });
    expect(await screen.findByText("Mission mise à jour.")).toBeInTheDocument();
  });

  it("crée une tâche rattachée à la mission", async () => {
    setAuth(["orchestration:read", "orchestration:write"]);
    fetchMock.mockImplementation((url: string, init?: RequestInit) =>
      init?.method === "POST" ? Promise.resolve(jsonResponse({}, 201)) : route()(url, init),
    );
    renderWithI18n(<MissionDetailView id="m1" />);
    await screen.findByRole("heading", { name: "Campagne Q4" });
    fireEvent.click(screen.getByRole("button", { name: "Nouvelle tâche" }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByLabelText("Mission")).toBeDisabled();
    fireEvent.change(within(dialog).getByLabelText("Titre"), { target: { value: "Appeler" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Créer" }));
    await waitFor(() => expect(calls(fetchMock, "POST")).toHaveLength(1));
    expect(JSON.parse(calls(fetchMock, "POST")[0][1].body)).toMatchObject({ title: "Appeler", mission_id: "m1" });
  });

  it("n'autorise pas la création de tâche sur une mission terminée", async () => {
    setAuth(["orchestration:read", "orchestration:write"]);
    fetchMock.mockImplementation(route(mission({ status: "DONE" })));
    renderWithI18n(<MissionDetailView id="m1" />);
    await screen.findByRole("heading", { name: "Campagne Q4" });
    expect(screen.queryByRole("button", { name: "Nouvelle tâche" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Rouvrir la mission" })).toBeInTheDocument();
  });

  it("affiche l'erreur traduite si la mission est introuvable", async () => {
    setAuth(["orchestration:read"]);
    fetchMock.mockImplementation((url: string) =>
      Promise.resolve(
        url.includes("/tasks")
          ? jsonResponse(tasks)
          : jsonResponse({ error: { code: "mission_not_found", message: "x" } }, 404),
      ),
    );
    renderWithI18n(<MissionDetailView id="zzz" />);
    expect(await screen.findByText("Mission introuvable.")).toBeInTheDocument();
  });
});
