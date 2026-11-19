import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LoginForm } from "@/components/LoginForm";
import { ApiError } from "@/lib/api";
import { renderWithI18n } from "@/test/utils";

const replace = vi.fn();
const login = vi.fn();
let status = "anonymous";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace }) }));
vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ login, status, refresh: vi.fn() }),
}));

function fill(email: string, password: string) {
  fireEvent.change(screen.getByLabelText("Adresse e-mail"), { target: { value: email } });
  fireEvent.change(screen.getByLabelText("Mot de passe"), { target: { value: password } });
}

describe("LoginForm", () => {
  beforeEach(() => {
    replace.mockReset();
    login.mockReset();
    status = "anonymous";
  });

  it("connecte puis redirige vers le tableau de bord", async () => {
    login.mockResolvedValue(undefined);
    renderWithI18n(<LoginForm />);
    fill("admin@example.com", "secret-password-1");
    fireEvent.click(screen.getByRole("button", { name: "Se connecter" }));
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
    expect(login).toHaveBeenCalledWith("admin@example.com", "secret-password-1", undefined);
  });

  it("affiche un message générique pour des identifiants invalides et vide le mot de passe", async () => {
    login.mockRejectedValue(new ApiError(401, "invalid_credentials", "x"));
    renderWithI18n(<LoginForm />);
    fill("admin@example.com", "bad");
    fireEvent.click(screen.getByRole("button", { name: "Se connecter" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Adresse e-mail ou mot de passe incorrect.");
    expect(screen.getByLabelText("Mot de passe")).toHaveValue("");
    expect(replace).not.toHaveBeenCalled();
  });

  it("affiche le délai d'attente en cas de limitation", async () => {
    login.mockRejectedValue(new ApiError(429, "login_throttled", "x", 600));
    renderWithI18n(<LoginForm />);
    fill("admin@example.com", "bad");
    fireEvent.click(screen.getByRole("button", { name: "Se connecter" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("10 minute(s)");
  });

  it("affiche une erreur réseau", async () => {
    login.mockRejectedValue(new TypeError("fetch failed"));
    renderWithI18n(<LoginForm />);
    fill("admin@example.com", "x");
    fireEvent.click(screen.getByRole("button", { name: "Se connecter" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Impossible de joindre le serveur.");
  });

  it("désactive le bouton pendant la connexion (état de chargement)", async () => {
    let resolve: () => void = () => undefined;
    login.mockReturnValue(new Promise<void>((r) => (resolve = r)));
    renderWithI18n(<LoginForm />);
    fill("admin@example.com", "x");
    fireEvent.click(screen.getByRole("button", { name: "Se connecter" }));
    const button = await screen.findByRole("button", { name: "Connexion…" });
    expect(button).toBeDisabled();
    resolve();
  });

  it("demande le code de vérification puis renvoie identifiants et code", async () => {
    login.mockRejectedValueOnce(new ApiError(401, "two_factor_required", "x"));
    login.mockResolvedValueOnce(undefined);
    renderWithI18n(<LoginForm />);
    fill("admin@example.com", "secret-password-1");
    fireEvent.click(screen.getByRole("button", { name: "Se connecter" }));
    const otp = await screen.findByLabelText("Code de vérification");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Mot de passe")).toHaveValue("secret-password-1");
    fireEvent.change(otp, { target: { value: " 123456 " } });
    fireEvent.click(screen.getByRole("button", { name: "Se connecter" }));
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
    expect(login).toHaveBeenLastCalledWith("admin@example.com", "secret-password-1", "123456");
  });

  it("affiche une erreur pour un code de vérification incorrect", async () => {
    login.mockRejectedValueOnce(new ApiError(401, "two_factor_required", "x"));
    login.mockRejectedValueOnce(new ApiError(401, "invalid_otp", "x"));
    renderWithI18n(<LoginForm />);
    fill("admin@example.com", "secret-password-1");
    fireEvent.click(screen.getByRole("button", { name: "Se connecter" }));
    fireEvent.change(await screen.findByLabelText("Code de vérification"), { target: { value: "000000" } });
    fireEvent.click(screen.getByRole("button", { name: "Se connecter" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Code de vérification incorrect.");
    expect(replace).not.toHaveBeenCalled();
  });

  it("redirige si déjà authentifié", () => {
    status = "authenticated";
    renderWithI18n(<LoginForm />);
    expect(replace).toHaveBeenCalledWith("/dashboard");
  });

  it("est bilingue", () => {
    renderWithI18n(<LoginForm />, "en");
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
  });
});
