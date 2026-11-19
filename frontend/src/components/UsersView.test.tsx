import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { UsersView } from "@/components/UsersView";
import { adminUser, jsonResponse, renderWithI18n } from "@/test/utils";

let auth: any;
vi.mock("@/lib/auth", () => ({ useAuth: () => auth }));

const mk = (id: string, role: string, name: string, active = true) => ({
  ...adminUser,
  id,
  role,
  display_name: name,
  email: `${name.toLowerCase()}@example.com`,
  is_active: active,
});

const page = {
  items: [mk("u1", "SUPER_ADMIN", "Admin"), mk("u2", "ADMIN", "Alice"), mk("u3", "VIEWER", "Victor")],
  total: 3,
  limit: 25,
  offset: 0,
};

function setAuth(role: string, permissions: string[]) {
  auth = { user: { ...adminUser, role }, permissions, can: (p: string) => permissions.includes(p) };
}

describe("UsersView", () => {
  const fetchMock = vi.fn();
  beforeEach(() => vi.stubGlobal("fetch", fetchMock));
  afterEach(() => {
    fetchMock.mockReset();
    vi.unstubAllGlobals();
  });

  it("lecture seule : pas de bouton de création ni d'actions", async () => {
    setAuth("OPERATOR", ["users:read"]);
    fetchMock.mockResolvedValue(jsonResponse(page));
    renderWithI18n(<UsersView />);
    await screen.findByText("Victor");
    expect(screen.queryByRole("button", { name: "Nouvel utilisateur" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Désactiver" })).not.toBeInTheDocument();
    expect(screen.getByText(/Lecture seule/)).toBeInTheDocument();
  });

  it("un ADMIN ne peut pas agir sur les comptes administrateurs ni sur lui-même", async () => {
    setAuth("ADMIN", ["users:read", "users:write"]);
    auth.user.id = "u2";
    fetchMock.mockResolvedValue(jsonResponse(page));
    renderWithI18n(<UsersView />);
    await screen.findByText("Victor");
    const rows = screen.getAllByRole("row");
    const rowOf = (name: string) => rows.find((r) => within(r).queryByText(name))!;
    expect(within(rowOf("Admin")).queryByRole("button")).not.toBeInTheDocument();
    expect(within(rowOf("Alice")).queryByRole("button")).not.toBeInTheDocument();
    expect(within(rowOf("Victor")).getByRole("button", { name: "Désactiver" })).toBeInTheDocument();
    expect(within(rowOf("Victor")).queryByRole("button", { name: "Réinitialiser le mot de passe" })).not.toBeInTheDocument();
  });

  it("demande une confirmation avant de désactiver puis appelle l'API avec PATCH", async () => {
    setAuth("SUPER_ADMIN", ["users:read", "users:write"]);
    fetchMock.mockImplementation((url: string, init?: RequestInit) =>
      Promise.resolve(init?.method === "PATCH" ? jsonResponse({}) : jsonResponse(page)),
    );
    renderWithI18n(<UsersView />);
    await screen.findByText("Victor");
    const row = screen.getAllByRole("row").find((r) => within(r).queryByText("Victor"))!;
    fireEvent.click(within(row).getByRole("button", { name: "Désactiver" }));
    expect(screen.getByRole("dialog")).toHaveTextContent("Désactiver Victor ?");
    expect(fetchMock.mock.calls.some(([, i]) => i?.method === "PATCH")).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: "Confirmer" }));
    await waitFor(() => {
      const call = fetchMock.mock.calls.find(([, i]) => i?.method === "PATCH");
      expect(call?.[0]).toBe("/api/v1/users/u3");
      expect(call?.[1].body).toBe('{"is_active":false}');
    });
  });

  it("affiche un état vide", async () => {
    setAuth("SUPER_ADMIN", ["users:read", "users:write"]);
    fetchMock.mockResolvedValue(jsonResponse({ ...page, items: [], total: 0 }));
    renderWithI18n(<UsersView />);
    expect(await screen.findByText("Aucun utilisateur ne correspond.")).toBeInTheDocument();
  });

  it("affiche une erreur de chargement avec bouton de relance", async () => {
    setAuth("SUPER_ADMIN", ["users:read", "users:write"]);
    fetchMock.mockResolvedValue(jsonResponse({ error: { code: "x", message: "x" } }, 500));
    renderWithI18n(<UsersView />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Impossible de charger les utilisateurs.");
    expect(screen.getByRole("button", { name: "Réessayer" })).toBeInTheDocument();
  });

  it("formulaire de création : envoie les données et affiche les erreurs serveur", async () => {
    setAuth("SUPER_ADMIN", ["users:read", "users:write"]);
    fetchMock.mockImplementation((url: string, init?: RequestInit) =>
      Promise.resolve(
        init?.method === "POST"
          ? jsonResponse({ error: { code: "email_taken", message: "x" } }, 409)
          : jsonResponse(page),
      ),
    );
    renderWithI18n(<UsersView />);
    await screen.findByText("Victor");
    fireEvent.click(screen.getByRole("button", { name: "Nouvel utilisateur" }));
    const dialog = screen.getByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("E-mail"), { target: { value: "new@example.com" } });
    fireEvent.change(within(dialog).getByLabelText("Nom affiché"), { target: { value: "New" } });
    fireEvent.change(within(dialog).getByLabelText("Mot de passe"), { target: { value: "Strong-Password-12" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Créer" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("Cette adresse e-mail est déjà utilisée.");
    const post = fetchMock.mock.calls.find(([, i]) => i?.method === "POST")!;
    expect(JSON.parse(post[1].body)).toMatchObject({ email: "new@example.com", display_name: "New", role: "VIEWER" });
  });
});
