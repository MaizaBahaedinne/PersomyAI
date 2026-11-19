import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";
import { middleware } from "@/middleware";

const call = (path: string, cookie?: string) =>
  middleware(new NextRequest(`https://app.persomy.com${path}`, cookie ? { headers: { cookie } } : undefined));

describe("middleware (routes privées)", () => {
  it("redirige vers /login sans cookie de session", () => {
    const res = call("/dashboard");
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("https://app.persomy.com/login");
  });

  it("laisse passer /login sans session", () => {
    expect(call("/login").headers.get("location")).toBeNull();
  });

  it("laisse passer avec un cookie de session (validité vérifiée par l'API)", () => {
    expect(call("/users", "persomy_session=abc").headers.get("location")).toBeNull();
  });
});
