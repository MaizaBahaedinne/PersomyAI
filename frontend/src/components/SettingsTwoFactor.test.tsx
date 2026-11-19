import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SettingsView } from "@/components/SettingsView";
import { adminUser, jsonResponse, renderWithI18n } from "@/test/utils";

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ user: adminUser, permissions: ["settings:read", "settings:write"], can: () => true, refresh: vi.fn() }),
}));

let state: { enabled: boolean; available: boolean; recovery_codes_left: number };

function route(url: string, init?: RequestInit) {
  const method = init?.method ?? "GET";
  if (url.endsWith("/auth/sessions")) return Promise.resolve(jsonResponse([]));
  if (url.endsWith("/auth/2fa") && method === "GET") return Promise.resolve(jsonResponse(state));
  if (url.endsWith("/auth/2fa/setup")) {
    return Promise.resolve(jsonResponse({ secret: "JBSWY3DPEHPK3PXP", otpauth_uri: "otpauth://totp/Persomy:a?secret=JBSWY3DPEHPK3PXP" }));
  }
  if (url.endsWith("/auth/2fa/enable")) {
    state = { enabled: true, available: true, recovery_codes_left: 2 };
    return Promise.resolve(jsonResponse({ recovery_codes: ["aaaaa-bbbbb", "ccccc-ddddd"] }));
  }
  if (url.endsWith("/auth/2fa/disable")) {
    state = { enabled: false, available: true, recovery_codes_left: 0 };
    return Promise.resolve(jsonResponse(null, 204));
  }
  return Promise.resolve(jsonResponse({}, 404));
}

describe("SettingsView — 2FA", () => {
  const fetchMock = vi.fn();
  beforeEach(() => {
    state = { enabled: false, available: true, recovery_codes_left: 0 };
    fetchMock.mockImplementation(route);
    vi.stubGlobal("fetch", fetchMock);
  });
  afterEach(() => {
    fetchMock.mockReset();
    vi.unstubAllGlobals();
  });

  async function openSecurity() {
    renderWithI18n(<SettingsView />);
    fireEvent.click(screen.getByRole("tab", { name: "Sécurité" }));
    await screen.findByText("Authentification à deux facteurs (TOTP)");
  }

  it("indique l'indisponibilité sans clé serveur et ne propose pas l'activation", async () => {
    state = { enabled: false, available: false, recovery_codes_left: 0 };
    await openSecurity();
    expect(await screen.findByRole("note")).toHaveTextContent("TWO_FACTOR_KEY");
    expect(screen.queryByRole("button", { name: "Activer" })).not.toBeInTheDocument();
  });

  it("active la 2FA : mot de passe, clé, code, puis codes de secours affichés une fois", async () => {
    await openSecurity();
    fireEvent.click(await screen.findByRole("button", { name: "Activer" }));
    fireEvent.change(screen.getByLabelText("Mot de passe actuel", { selector: "#tfa-pw" }), { target: { value: "pw-pw-pw-pw-12" } });
    fireEvent.click(screen.getByRole("button", { name: "Activer" }));
    expect(await screen.findByText("JBSWY3DPEHPK3PXP")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Code à 6 chiffres"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirmer" }));
    expect(await screen.findByText("aaaaa-bbbbb")).toBeInTheDocument();
    expect(screen.queryByText("JBSWY3DPEHPK3PXP")).not.toBeInTheDocument();
    const enable = fetchMock.mock.calls.find(([u]) => String(u).endsWith("/auth/2fa/enable"))!;
    expect(JSON.parse(enable[1].body)).toEqual({ code: "123456" });
    fireEvent.click(screen.getByRole("button", { name: "J'ai conservé les codes" }));
    expect(screen.queryByText("aaaaa-bbbbb")).not.toBeInTheDocument();
    expect(await screen.findByText("Activée")).toBeInTheDocument();
  });

  it("désactive la 2FA avec mot de passe et code", async () => {
    state = { enabled: true, available: true, recovery_codes_left: 10 };
    await openSecurity();
    fireEvent.click(await screen.findByRole("button", { name: "Désactiver" }));
    fireEvent.change(screen.getByLabelText("Mot de passe actuel", { selector: "#tfa-pw" }), { target: { value: "pw-pw-pw-pw-12" } });
    fireEvent.change(screen.getByLabelText("Code à 6 chiffres"), { target: { value: "654321" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Désactiver" })[0]);
    await waitFor(() => expect(screen.getByText("Désactivée")).toBeInTheDocument());
    const call = fetchMock.mock.calls.find(([u]) => String(u).endsWith("/auth/2fa/disable"))!;
    expect(JSON.parse(call[1].body)).toEqual({ password: "pw-pw-pw-pw-12", code: "654321" });
  });
});
