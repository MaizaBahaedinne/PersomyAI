"use client";

import { useState, type FormEvent } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { errorKey, formatDateTime } from "@/lib/errors";
import { useAsync } from "@/lib/useAsync";
import type { CompanyStatus, ContactStatus, CrmCompany, CrmContact, Page } from "@/lib/types";
import { useI18n } from "@/i18n";
import { Badge, EmptyState, ErrorBanner, PageHeader, Spinner, SuccessBanner } from "@/components/ui";

const PAGE_SIZE = 25;
const COMPANY_STATUSES: CompanyStatus[] = ["ACTIVE", "ARCHIVED"];
const CONTACT_STATUSES: ContactStatus[] = ["LEAD", "ACTIVE", "INACTIVE"];

function companyTone(status: CompanyStatus): "ok" | "neutral" {
  return status === "ACTIVE" ? "ok" : "neutral";
}

function contactTone(status: ContactStatus): "info" | "ok" | "neutral" {
  return status === "LEAD" ? "info" : status === "ACTIVE" ? "ok" : "neutral";
}

export function CrmView() {
  const { t, label, locale } = useI18n();
  const { can } = useAuth();
  const canWrite = can("crm:write");

  const [searchCompany, setSearchCompany] = useState("");
  const [searchContact, setSearchContact] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [companyError, setCompanyError] = useState<string | null>(null);
  const [contactError, setContactError] = useState<string | null>(null);

  const companies = useAsync(
    () => api<Page<CrmCompany>>("/crm/companies", { params: { search: searchCompany, limit: PAGE_SIZE, offset: 0 } }),
    [searchCompany],
  );
  const contacts = useAsync(
    () => api<Page<CrmContact>>("/crm/contacts", { params: { search: searchContact, limit: PAGE_SIZE, offset: 0 } }),
    [searchContact],
  );

  const [companyForm, setCompanyForm] = useState({ name: "", website: "" });
  const [contactForm, setContactForm] = useState({ first_name: "", last_name: "", email: "", company_id: "" });

  const createCompany = async (e: FormEvent) => {
    e.preventDefault();
    setCompanyError(null);
    try {
      await api("/crm/companies", { method: "POST", body: { name: companyForm.name, website: companyForm.website || null } });
      setCompanyForm({ name: "", website: "" });
      setNotice(t("crm.company_created"));
      companies.reload();
    } catch (err) {
      setCompanyError(t(errorKey(err)));
    }
  };

  const createContact = async (e: FormEvent) => {
    e.preventDefault();
    setContactError(null);
    try {
      await api("/crm/contacts", {
        method: "POST",
        body: {
          first_name: contactForm.first_name,
          last_name: contactForm.last_name,
          email: contactForm.email || null,
          company_id: contactForm.company_id || null,
          status: "LEAD",
        },
      });
      setContactForm({ first_name: "", last_name: "", email: "", company_id: "" });
      setNotice(t("crm.contact_created"));
      contacts.reload();
    } catch (err) {
      setContactError(t(errorKey(err)));
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader title={t("crm.title")} subtitle={t("crm.subtitle")} />
      {!canWrite && <p className="text-sm text-slate-400">{t("crm.readonly")}</p>}
      {notice && <SuccessBanner message={notice} />}

      <section className="card space-y-4">
        <h2 className="text-lg font-semibold text-white">{t("crm.companies")}</h2>
        <input
          className="input max-w-xs"
          type="search"
          placeholder={t("crm.search_companies")}
          aria-label={t("crm.search_companies")}
          value={searchCompany}
          onChange={(e) => setSearchCompany(e.target.value)}
        />
        {canWrite && (
          <form className="grid gap-3 md:grid-cols-3" onSubmit={createCompany}>
            <input
              className="input"
              placeholder={t("crm.form.company_name")}
              value={companyForm.name}
              onChange={(e) => setCompanyForm((s) => ({ ...s, name: e.target.value }))}
              required
            />
            <input
              className="input"
              placeholder={t("crm.form.company_website")}
              value={companyForm.website}
              onChange={(e) => setCompanyForm((s) => ({ ...s, website: e.target.value }))}
            />
            <button type="submit" className="btn-primary">{t("common.create")}</button>
          </form>
        )}
        {companyError && <ErrorBanner message={companyError} />}

        {companies.loading && !companies.data ? (
          <Spinner />
        ) : companies.error || !companies.data ? (
          <ErrorBanner message={t("crm.load_error")} onRetry={companies.reload} />
        ) : companies.data.items.length === 0 ? (
          <EmptyState message={t("crm.empty_companies")} />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-ink-700">
                <tr>
                  <th className="th">{t("crm.col_company")}</th>
                  <th className="th">{t("crm.col_status")}</th>
                  <th className="th">{t("crm.col_updated")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ink-700">
                {companies.data.items.map((c) => (
                  <tr key={c.id}>
                    <td className="td">
                      <p className="font-medium">{c.name}</p>
                      {c.website && <p className="text-xs text-slate-500">{c.website}</p>}
                    </td>
                    <td className="td"><Badge tone={companyTone(c.status)}>{label("crm.company.status", c.status)}</Badge></td>
                    <td className="td text-slate-400">{formatDateTime(c.updated_at, locale)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="card space-y-4">
        <h2 className="text-lg font-semibold text-white">{t("crm.contacts")}</h2>
        <input
          className="input max-w-xs"
          type="search"
          placeholder={t("crm.search_contacts")}
          aria-label={t("crm.search_contacts")}
          value={searchContact}
          onChange={(e) => setSearchContact(e.target.value)}
        />
        {canWrite && (
          <form className="grid gap-3 md:grid-cols-5" onSubmit={createContact}>
            <input
              className="input"
              placeholder={t("crm.form.first_name")}
              value={contactForm.first_name}
              onChange={(e) => setContactForm((s) => ({ ...s, first_name: e.target.value }))}
              required
            />
            <input
              className="input"
              placeholder={t("crm.form.last_name")}
              value={contactForm.last_name}
              onChange={(e) => setContactForm((s) => ({ ...s, last_name: e.target.value }))}
              required
            />
            <input
              className="input"
              placeholder={t("crm.form.email")}
              value={contactForm.email}
              onChange={(e) => setContactForm((s) => ({ ...s, email: e.target.value }))}
            />
            <select
              className="input"
              value={contactForm.company_id}
              onChange={(e) => setContactForm((s) => ({ ...s, company_id: e.target.value }))}
            >
              <option value="">{t("crm.form.company_none")}</option>
              {(companies.data?.items ?? []).map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
            <button type="submit" className="btn-primary">{t("common.create")}</button>
          </form>
        )}
        {contactError && <ErrorBanner message={contactError} />}

        {contacts.loading && !contacts.data ? (
          <Spinner />
        ) : contacts.error || !contacts.data ? (
          <ErrorBanner message={t("crm.load_error")} onRetry={contacts.reload} />
        ) : contacts.data.items.length === 0 ? (
          <EmptyState message={t("crm.empty_contacts")} />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-ink-700">
                <tr>
                  <th className="th">{t("crm.col_contact")}</th>
                  <th className="th">{t("crm.col_company")}</th>
                  <th className="th">{t("crm.col_status")}</th>
                  <th className="th">{t("crm.col_updated")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ink-700">
                {contacts.data.items.map((c) => (
                  <tr key={c.id}>
                    <td className="td">
                      <p className="font-medium">{c.first_name} {c.last_name}</p>
                      {c.email && <p className="text-xs text-slate-500">{c.email}</p>}
                    </td>
                    <td className="td text-slate-300">{c.company_name ?? t("common.none")}</td>
                    <td className="td"><Badge tone={contactTone(c.status)}>{label("crm.contact.status", c.status)}</Badge></td>
                    <td className="td text-slate-400">{formatDateTime(c.updated_at, locale)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="card">
        <p className="text-sm text-slate-400">{t("crm.scope_note")}</p>
        <div className="mt-3 flex gap-2">
          {COMPANY_STATUSES.map((s) => (
            <Badge key={s} tone={companyTone(s)}>{label("crm.company.status", s)}</Badge>
          ))}
          {CONTACT_STATUSES.map((s) => (
            <Badge key={s} tone={contactTone(s)}>{label("crm.contact.status", s)}</Badge>
          ))}
        </div>
      </section>
    </div>
  );
}
