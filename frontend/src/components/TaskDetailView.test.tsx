import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { TaskDetailView } from "@/components/TaskDetailView";
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

const baseTask = {
  id: "t1",
  title: "Relancer les devis",
  description: "Pour la semaine",
  priority: "NORMAL",
  status: "OPEN",
  mission_id: "m1",
  mission_title: "Q4",
  agent_id: "a1",
  agent_name: "Alpha",
  required_scope: "email:send",
  requires_approval: true,
  approval_requested_at: null,
  decided_by_label: null,
  decided_at: null,
  decision_reason: null,
  created_at: "2026-11-19T10:00:00Z",
  updated_at: new Date().toISOString(),
};

const history = {
  items: [
    {
      id: "e1",
      created_at: "2026-11-19T10:00:00Z",
      actor_label: "admin@example.com",
      action: "task.create",
      target_type: "task",
      target_id: "t1",
      status: "success",
      ip_address: null,
      details: null,
    },
  ],
  total: 1,
  limit: 20,
  offset: 0,
};

const failedRun = {
  id: "r1",
  status: "FAILED",
  provider: "none",
  output: "",
  error_code: "provider_error",
  cost_cents: 0,
  tokens_in: 0,
  tokens_out: 0,
  started_at: "2026-11-19T10:00:00Z",
  finished_at: "2026-11-19T10:00:01Z",
};

function setAuth(permissions: string[]) {
  auth = { user: adminUser, permissions, can: (p: string) => permissions.includes(p) };
}

function route(
  task: Record<string, unknown> = baseTask,
  opts: { configured?: boolean; runs?: unknown[]; post?: (url: string) => Response } = {},
) {
  return (url: string, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    if (method === "POST" && opts.post) return Promise.resolve(opts.post(url));
    if (url.includes("/tasks/provider"))
      return Promise.resolve(jsonResponse({ name: opts.configured ? "demo" : "none", configured: !!opts.configured, paid: false }));
    if (url.includes("/runs")) return Promise.resolve(jsonResponse(opts.runs ?? []));
    if (url.includes("/history")) return Promise.resolve(jsonResponse(history));
    if (url.includes("/agents/catalog")) return Promise.resolve(jsonResponse(catalog));
    if (url.includes("/agents"))
      return Promise.resolve(jsonResponse({ items: [{ id: "a1", name: "Alpha", status: "ACTIVE" }], total: 1, limit: 200, offset: 0 }));
    return Promise.resolve(jsonResponse(task));
  };
}

const calls = (fetchMock: ReturnType<typeof vi.fn>, method: string) =>
  fetchMock.mock.calls.filter(([, i]) => (i?.method ?? "GET") === method);

const ALL = ["orchestration:read", "orchestration:write", "orchestration:approve", "orchestration:run"];

describe("TaskDetailView", () => {
  const fetchMock = vi.fn();
  beforeEach(() => vi.stubGlobal("fetch", fetchMock));
  afterEach(() => {
    fetchMock.mockReset();
    vi.unstubAllGlobals();
  });

  it("lecture seule : aucune action, formulaire désactivé, fournisseur absent signalé", async () => {
    setAuth(["orchestration:read"]);
    fetchMock.mockImplementation(route());
    renderWithI18n(<TaskDetailView id="t1" />);
    expect(await screen.findByRole("heading", { name: "Relancer les devis" })).toBeInTheDocument();
    expect(await screen.findByText(/Aucun fournisseur IA n'est configuré : les tâches/)).toBeInTheDocument();
    for (const name of ["Demander la validation", "Approuver", "Rejeter", "Exécuter", "Annuler la tâche", "Enregistrer"]) {
      expect(screen.queryByRole("button", { name })).not.toBeInTheDocument();
    }
    expect(screen.getByLabelText("Titre")).toBeDisabled();
    expect(await screen.findByText("Tâche créée")).toBeInTheDocument(); // historique
    expect(screen.getByText("Aucune exécution.")).toBeInTheDocument();
  });

  it("signale la règle des quatre yeux pour une permission critique", async () => {
    setAuth(["orchestration:read"]);
    fetchMock.mockImplementation(route());
    renderWithI18n(<TaskDetailView id="t1" />);
    expect(await screen.findByText(/doit venir d'une autre personne/)).toBeInTheDocument();
    expect(screen.getByText(/exige une validation humaine/)).toBeInTheDocument();
  });

  it("n'offre pas l'exécution tant que la validation requise n'est pas obtenue", async () => {
    setAuth(ALL);
    fetchMock.mockImplementation(route(baseTask, { configured: true }));
    renderWithI18n(<TaskDetailView id="t1" />);
    await screen.findByRole("heading", { name: "Relancer les devis" });
    expect(screen.queryByRole("button", { name: "Exécuter" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Demander la validation" })).toBeInTheDocument();
  });

  it("demande la validation après confirmation", async () => {
    setAuth(ALL);
    fetchMock.mockImplementation(route(baseTask, { post: () => jsonResponse(baseTask) }));
    renderWithI18n(<TaskDetailView id="t1" />);
    await screen.findByRole("heading", { name: "Relancer les devis" });
    fireEvent.click(screen.getByRole("button", { name: "Demander la validation" }));
    expect(calls(fetchMock, "POST")).toHaveLength(0);
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Confirmer" }));
    await waitFor(() => expect(calls(fetchMock, "POST")).toHaveLength(1));
    expect(String(calls(fetchMock, "POST")[0][0])).toBe("/api/v1/tasks/t1/request-approval");
    expect(await screen.findByText("Validation demandée.")).toBeInTheDocument();
  });

  it("approuve avec un commentaire facultatif", async () => {
    setAuth(ALL);
    fetchMock.mockImplementation(
      route({ ...baseTask, status: "AWAITING_APPROVAL" }, { post: () => jsonResponse(baseTask) }),
    );
    renderWithI18n(<TaskDetailView id="t1" />);
    await screen.findByRole("heading", { name: "Relancer les devis" });
    fireEvent.click(screen.getByRole("button", { name: "Approuver" }));
    const dialog = screen.getByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Commentaire (facultatif)"), { target: { value: "ok" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Confirmer" }));
    await waitFor(() => expect(calls(fetchMock, "POST")).toHaveLength(1));
    const [url, init] = calls(fetchMock, "POST")[0];
    expect(String(url)).toBe("/api/v1/tasks/t1/approve");
    expect(JSON.parse(init.body)).toEqual({ comment: "ok" });
    expect(await screen.findByText("Tâche approuvée.")).toBeInTheDocument();
  });

  it("exige un motif pour rejeter", async () => {
    setAuth(ALL);
    fetchMock.mockImplementation(
      route({ ...baseTask, status: "AWAITING_APPROVAL" }, { post: () => jsonResponse(baseTask) }),
    );
    renderWithI18n(<TaskDetailView id="t1" />);
    await screen.findByRole("heading", { name: "Relancer les devis" });
    fireEvent.click(screen.getByRole("button", { name: "Rejeter" }));
    const dialog = screen.getByRole("dialog");
    const confirm = within(dialog).getByRole("button", { name: "Confirmer" });
    expect(confirm).toBeDisabled();
    fireEvent.change(within(dialog).getByLabelText("Motif du rejet"), { target: { value: "hors budget" } });
    expect(confirm).toBeEnabled();
    fireEvent.click(confirm);
    await waitFor(() => expect(calls(fetchMock, "POST")).toHaveLength(1));
    expect(JSON.parse(calls(fetchMock, "POST")[0][1].body)).toEqual({ reason: "hors budget" });
  });

  it("n'affiche pas approuver/rejeter sans la permission d'approbation", async () => {
    setAuth(["orchestration:read", "orchestration:write"]);
    fetchMock.mockImplementation(route({ ...baseTask, status: "AWAITING_APPROVAL" }));
    renderWithI18n(<TaskDetailView id="t1" />);
    await screen.findByRole("heading", { name: "Relancer les devis" });
    expect(screen.queryByRole("button", { name: "Approuver" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Rejeter" })).not.toBeInTheDocument();
  });

  it("affiche l'erreur traduite quand l'auto-validation est refusée", async () => {
    setAuth(ALL);
    fetchMock.mockImplementation(
      route(
        { ...baseTask, status: "AWAITING_APPROVAL" },
        { post: () => jsonResponse({ error: { code: "self_approval_forbidden", message: "x" } }, 403) },
      ),
    );
    renderWithI18n(<TaskDetailView id="t1" />);
    await screen.findByRole("heading", { name: "Relancer les devis" });
    fireEvent.click(screen.getByRole("button", { name: "Approuver" }));
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Confirmer" }));
    expect(await screen.findByText(/doit être validée par une autre personne/)).toBeInTheDocument();
  });

  it("exécute une tâche approuvée après confirmation et signale un échec du fournisseur", async () => {
    setAuth(ALL);
    fetchMock.mockImplementation(
      route(
        { ...baseTask, status: "APPROVED" },
        { configured: true, post: () => jsonResponse({ task: { ...baseTask, status: "FAILED" }, run: failedRun }) },
      ),
    );
    renderWithI18n(<TaskDetailView id="t1" />);
    await screen.findByRole("heading", { name: "Relancer les devis" });
    fireEvent.click(screen.getByRole("button", { name: "Exécuter" }));
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveTextContent("Alpha");
    expect(calls(fetchMock, "POST")).toHaveLength(0);
    fireEvent.click(within(dialog).getByRole("button", { name: "Confirmer" }));
    await waitFor(() => expect(calls(fetchMock, "POST")).toHaveLength(1));
    expect(String(calls(fetchMock, "POST")[0][0])).toBe("/api/v1/tasks/t1/run");
    expect(await screen.findByText(/L'exécution a échoué : Erreur du fournisseur IA/)).toBeInTheDocument();
  });

  it("affiche l'erreur traduite si aucun fournisseur n'est configuré", async () => {
    setAuth(ALL);
    fetchMock.mockImplementation(
      route(
        { ...baseTask, status: "APPROVED" },
        { post: () => jsonResponse({ error: { code: "provider_not_configured", message: "x" } }, 409) },
      ),
    );
    renderWithI18n(<TaskDetailView id="t1" />);
    await screen.findByRole("heading", { name: "Relancer les devis" });
    fireEvent.click(screen.getByRole("button", { name: "Exécuter" }));
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Confirmer" }));
    expect(
      await screen.findByText("Aucun fournisseur IA n'est configuré : la tâche ne peut pas être exécutée."),
    ).toBeInTheDocument();
  });

  it("propose l'exécution directe si l'agent est autonome et la permission non critique", async () => {
    setAuth(ALL);
    fetchMock.mockImplementation(
      route({ ...baseTask, required_scope: "crm:read", requires_approval: false }, { configured: true }),
    );
    renderWithI18n(<TaskDetailView id="t1" />);
    await screen.findByRole("heading", { name: "Relancer les devis" });
    expect(screen.getByRole("button", { name: "Exécuter" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Demander la validation" })).not.toBeInTheDocument();
    expect(screen.getByText("Fournisseur IA : demo")).toBeInTheDocument();
  });

  it("enregistre la modification avec les champs effacés envoyés à null", async () => {
    setAuth(ALL);
    fetchMock.mockImplementation(route(baseTask, { post: () => jsonResponse(baseTask) }));
    renderWithI18n(<TaskDetailView id="t1" />);
    await screen.findByRole("heading", { name: "Relancer les devis" });
    await screen.findByRole("option", { name: "Alpha" });
    fireEvent.change(screen.getByLabelText("Permission exigée"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Enregistrer" }));
    await waitFor(() => expect(calls(fetchMock, "PATCH")).toHaveLength(1));
    const [url, init] = calls(fetchMock, "PATCH")[0];
    expect(String(url)).toBe("/api/v1/tasks/t1");
    expect(JSON.parse(init.body)).toEqual({
      title: "Relancer les devis",
      description: "Pour la semaine",
      priority: "NORMAL",
      agent_id: "a1",
      required_scope: null,
    });
  });

  it("verrouille l'édition d'une tâche terminée et affiche le résultat de l'exécution", async () => {
    setAuth(ALL);
    const doneRun = { ...failedRun, status: "SUCCESS", error_code: null, output: "Brouillon prêt", tokens_in: 10, tokens_out: 20 };
    fetchMock.mockImplementation(route({ ...baseTask, status: "DONE" }, { runs: [doneRun] }));
    renderWithI18n(<TaskDetailView id="t1" />);
    await screen.findByRole("heading", { name: "Relancer les devis" });
    expect(screen.getByLabelText("Titre")).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Enregistrer" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Exécuter" })).not.toBeInTheDocument();
    expect(await screen.findByText("Brouillon prêt")).toBeInTheDocument();
    expect(screen.getByText(/10 entrée \/ 20 sortie/)).toBeInTheDocument();
  });

  it("affiche l'erreur traduite si la tâche est introuvable", async () => {
    setAuth(["orchestration:read"]);
    fetchMock.mockImplementation((url: string) =>
      Promise.resolve(
        url.includes("/tasks/zzz") && !url.includes("/runs") && !url.includes("/history")
          ? jsonResponse({ error: { code: "task_not_found", message: "x" } }, 404)
          : jsonResponse([]),
      ),
    );
    renderWithI18n(<TaskDetailView id="zzz" />);
    expect(await screen.findByText("Tâche introuvable.")).toBeInTheDocument();
  });
});
