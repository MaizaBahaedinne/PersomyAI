import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DashboardView } from "@/components/DashboardView";
import { jsonResponse, renderWithI18n } from "@/test/utils";

const summary = {
  company: { name: "Persomy AI" },
  generated_at: "2026-11-19T10:00:00Z",
  users: { total: 2, active: 2, disabled: 0, super_admins: 1 },
  sessions: { active: 1 },
  security: { logins_success_24h: 4, logins_failed_24h: 1, logins_throttled_24h: 0, recent_failures: [] },
  recent_activity: [],
  alerts: [{ code: "single_super_admin", severity: "info", count: 1 }],
  services: [
    { name: "api", status: "ok", latency_ms: null },
    { name: "database", status: "down", latency_ms: null },
  ],
  pending_modules: ["missions", "automations"],
  agents: { draft: 1, active: 3, paused: 2, error: 1, disabled: 0, total: 7 },
  emergency_stop: false,
};

describe("DashboardView", () => {
  const fetchMock = vi.fn();
  beforeEach(() => vi.stubGlobal("fetch", fetchMock));
  afterEach(() => {
    fetchMock.mockReset();
    vi.unstubAllGlobals();
  });

  it("affiche un état de chargement", () => {
    fetchMock.mockReturnValue(new Promise(() => undefined));
    renderWithI18n(<DashboardView />);
    expect(screen.getByRole("status")).toHaveTextContent("Chargement");
  });

  it("affiche les données réelles du backend", async () => {
    fetchMock.mockResolvedValue(jsonResponse(summary));
    renderWithI18n(<DashboardView />);
    expect(await screen.findByText("Utilisateurs")).toBeInTheDocument();
    const loginsOk = screen.getByText("Connexions réussies (24 h)").parentElement!;
    expect(loginsOk).toHaveTextContent("4");
    expect(screen.getByText(/Un seul SUPER_ADMIN actif/)).toBeInTheDocument();
    expect(screen.getByText("Indisponible")).toBeInTheDocument();
  });

  it("n'affiche aucun chiffre pour les modules non développés", async () => {
    fetchMock.mockResolvedValue(jsonResponse(summary));
    renderWithI18n(<DashboardView />);
    const missions = (await screen.findByText("Missions")).parentElement!;
    expect(missions).toHaveTextContent("En préparation");
    expect(missions.textContent).not.toMatch(/\d/);
  });

  it("affiche les compteurs réels des agents", async () => {
    fetchMock.mockResolvedValue(jsonResponse(summary));
    renderWithI18n(<DashboardView />);
    const active = (await screen.findByText("Agents actifs")).parentElement!;
    expect(active).toHaveTextContent("3");
    expect(screen.getByText("Agents en pause").parentElement).toHaveTextContent("2");
    expect(screen.getByText("Agents (total)").parentElement).toHaveTextContent("7");
  });

  it("affiche l'alerte d'arrêt d'urgence", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({
        ...summary,
        emergency_stop: true,
        alerts: [{ code: "emergency_stop_active", severity: "warning", count: 1 }],
      }),
    );
    renderWithI18n(<DashboardView />);
    expect(await screen.findByText(/Arrêt d'urgence actif/)).toBeInTheDocument();
  });

  it("affiche les états vides propres", async () => {
    fetchMock.mockResolvedValue(jsonResponse({ ...summary, alerts: [] }));
    renderWithI18n(<DashboardView />);
    expect(await screen.findByText("Aucune alerte.")).toBeInTheDocument();
    expect(screen.getByText("Aucune activité enregistrée.")).toBeInTheDocument();
    expect(screen.getByText("Aucun événement de sécurité sur 24 h.")).toBeInTheDocument();
  });

  it("affiche une erreur et permet de réessayer", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ error: { code: "internal_error", message: "x" } }, 500));
    fetchMock.mockResolvedValueOnce(jsonResponse(summary));
    renderWithI18n(<DashboardView />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Impossible de charger le tableau de bord.");
    fireEvent.click(screen.getByRole("button", { name: "Réessayer" }));
    await waitFor(() => expect(screen.getByText("Connexions réussies (24 h)")).toBeInTheDocument());
  });

  it("est traduit en anglais", async () => {
    fetchMock.mockResolvedValue(jsonResponse(summary));
    renderWithI18n(<DashboardView />, "en");
    expect(await screen.findByText("Successful sign-ins (24 h)")).toBeInTheDocument();
    expect(screen.getByText("AI agents")).toBeInTheDocument();
  });
});
