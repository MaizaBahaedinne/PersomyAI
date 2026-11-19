import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppShell } from "@/components/AppShell";
import { RequirePermission } from "@/components/RequirePermission";
import { adminUser, jsonResponse, renderWithI18n } from "@/test/utils";

const replace = vi.fn();
let auth: any;

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  usePathname: () => "/dashboard",
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: any) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));
vi.mock("@/lib/auth", () => ({ useAuth: () => auth }));

function setAuth(status: string, permissions: string[] = []) {
  auth = {
    status,
    user: status === "authenticated" ? adminUser : null,
    permissions,
    can: (p: string) => permissions.includes(p),
    logout: vi.fn(),
    refresh: vi.fn(),
  };
}

describe("AppShell (accès privés)", () => {
  beforeEach(() => {
    replace.mockReset();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ alerts: [] })));
  });

  it("affiche un état de chargement sans contenu privé pendant la vérification", () => {
    setAuth("loading");
    renderWithI18n(<AppShell><p>secret</p></AppShell>);
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.queryByText("secret")).not.toBeInTheDocument();
  });

  it("redirige vers /login et n'affiche rien si anonyme", () => {
    setAuth("anonymous");
    renderWithI18n(<AppShell><p>secret</p></AppShell>);
    expect(replace).toHaveBeenCalledWith("/login");
    expect(screen.queryByText("secret")).not.toBeInTheDocument();
  });

  it("affiche le contenu et la navigation filtrée par permissions", () => {
    setAuth("authenticated", ["dashboard:read", "users:read"]);
    renderWithI18n(<AppShell><p>secret</p></AppShell>);
    expect(screen.getByText("secret")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Utilisateurs" }).length).toBeGreaterThan(0);
    expect(screen.queryByRole("link", { name: "Journal d'audit" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Paramètres" })).not.toBeInTheDocument();
  });

  it("signale les modules non développés comme « Bientôt »", () => {
    setAuth("authenticated", ["dashboard:read"]);
    renderWithI18n(<AppShell><p>x</p></AppShell>);
    expect(screen.getAllByText("Bientôt").length).toBeGreaterThanOrEqual(7);
    // Les agents sont développés : visibles seulement avec la permission, sans mention « Bientôt ».
    expect(screen.queryByRole("link", { name: "Agents IA" })).not.toBeInTheDocument();
  });

  it("affiche le module Agents IA avec la permission agents:read", () => {
    setAuth("authenticated", ["dashboard:read", "agents:read"]);
    renderWithI18n(<AppShell><p>x</p></AppShell>);
    const link = screen.getAllByRole("link", { name: "Agents IA" })[0];
    expect(link).toHaveAttribute("href", "/agents");
    expect(link).not.toHaveTextContent("Bientôt");
  });
});

describe("RequirePermission", () => {
  it("bloque sans la permission", () => {
    setAuth("authenticated", ["dashboard:read"]);
    renderWithI18n(<RequirePermission permission="audit:read"><p>audit</p></RequirePermission>);
    expect(screen.queryByText("audit")).not.toBeInTheDocument();
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("autorise avec la permission", () => {
    setAuth("authenticated", ["audit:read"]);
    renderWithI18n(<RequirePermission permission="audit:read"><p>audit</p></RequirePermission>);
    expect(screen.getByText("audit")).toBeInTheDocument();
  });
});
