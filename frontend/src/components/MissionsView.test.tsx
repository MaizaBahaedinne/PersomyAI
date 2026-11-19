import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MissionsView } from "@/components/MissionsView";
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

const mission = {
  id: "m1",
  title: "Campagne Q4",
  description: "",
  status: "OPEN",
  created_at: "2026-11-19T10:00:00Z",
  updated_at: "2026-11-19T10:00:00Z",
  task_counts: { open: 2, done: 1, total: 3 },
};
const page = (items: unknown[]) => ({ items, total: items.length, limit: 25, offset: 0 });

function setAuth(permissions: string[]) {
  auth = { user: adminUser, permissions, can: (p: string) => permissions.includes(p) };
}

const calls = (fetchMock: ReturnType<typeof vi.fn>, method: string) =>
  fetchMock.mock.calls.filter(([, i]) => (i?.method ?? "GET") === method);

describe("MissionsView", () => {
  const fetchMock = vi.fn();
  beforeEach(() => vi.stubGlobal("fetch", fetchMock));
  afterEach(() => {
    fetchMock.mockReset();
    vi.unstubAllGlobals();
  });

  it("liste les missions avec le nombre réel de tâches", async () => {
    setAuth(["orchestration:read"]);
    fetchMock.mockResolvedValue(jsonResponse(page([mission])));
    renderWithI18n(<MissionsView />);
    expect(await screen.findByText("Campagne Q4")).toBeInTheDocument();
    const row = screen.getAllByRole("row")[1];
    expect(within(row).getByText("3")).toBeInTheDocument();
    expect(within(row).getByText("Ouverte")).toBeInTheDocument();
    expect(within(row).getByRole("link", { name: "Ouvrir" })).toHaveAttribute("href", "/missions/m1");
    expect(screen.queryByRole("button", { name: "Nouvelle mission" })).not.toBeInTheDocument();
  });

  it("affiche l'état vide", async () => {
    setAuth(["orchestration:read"]);
    fetchMock.mockResolvedValue(jsonResponse(page([])));
    renderWithI18n(<MissionsView />);
    expect(await screen.findByText("Aucune mission pour le moment.")).toBeInTheDocument();
  });

  it("crée une mission", async () => {
    setAuth(["orchestration:read", "orchestration:write"]);
    fetchMock.mockImplementation((_url: string, init?: RequestInit) =>
      Promise.resolve(init?.method === "POST" ? jsonResponse(mission, 201) : jsonResponse(page([]))),
    );
    renderWithI18n(<MissionsView />);
    fireEvent.click(await screen.findByRole("button", { name: "Nouvelle mission" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Titre"), { target: { value: "Campagne" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Créer" }));
    await waitFor(() => expect(calls(fetchMock, "POST")).toHaveLength(1));
    const [url, init] = calls(fetchMock, "POST")[0];
    expect(String(url)).toBe("/api/v1/missions");
    expect(JSON.parse(init.body)).toEqual({ title: "Campagne", description: "" });
    expect(await screen.findByText("Mission créée.")).toBeInTheDocument();
  });

  it("affiche une erreur de chargement", async () => {
    setAuth(["orchestration:read"]);
    fetchMock.mockResolvedValue(jsonResponse({ error: { code: "internal_error", message: "x" } }, 500));
    renderWithI18n(<MissionsView />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Impossible de charger les missions.");
  });
});
