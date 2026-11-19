import { describe, expect, it } from "vitest";
import { en } from "@/i18n/en";
import { fr } from "@/i18n/fr";
import { translate } from "@/i18n/core";

describe("i18n", () => {
  it("fr et en ont exactement les mêmes clés", () => {
    expect(Object.keys(en).sort()).toEqual(Object.keys(fr).sort());
  });

  it("aucune traduction vide", () => {
    for (const dict of [fr, en] as Record<string, string>[]) {
      for (const [key, value] of Object.entries(dict)) expect(value.trim(), key).not.toBe("");
    }
  });

  it("les paramètres {x} sont identiques dans les deux langues", () => {
    const params = (s: string) => (s.match(/\{\w+\}/g) ?? []).sort().join(",");
    for (const key of Object.keys(fr) as (keyof typeof fr)[]) {
      expect(params(en[key]), key).toBe(params(fr[key]));
    }
  });

  it("interpole les paramètres", () => {
    expect(translate("fr", "login.error.throttled", { minutes: 5 })).toContain("5");
    expect(translate("en", "dashboard.subtitle", { company: "Acme" })).toBe("Overview of Acme");
  });
});
