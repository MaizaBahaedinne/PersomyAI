"use client";

import { useState, type FormEvent } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { errorKey, formatDateTime } from "@/lib/errors";
import { useAsync } from "@/lib/useAsync";
import type { Language, Page, Role, User } from "@/lib/types";
import { useI18n } from "@/i18n";
import { Badge, ConfirmDialog, EmptyState, ErrorBanner, Modal, PageHeader, Spinner, SuccessBanner } from "@/components/ui";

const ALL_ROLES: Role[] = ["SUPER_ADMIN", "ADMIN", "OPERATOR", "VIEWER"];
const PRIVILEGED: Role[] = ["SUPER_ADMIN", "ADMIN"];
const PAGE_SIZE = 25;

type Dialog =
  | { kind: "create" }
  | { kind: "edit"; user: User }
  | { kind: "password"; user: User }
  | { kind: "toggle"; user: User }
  | { kind: "revoke"; user: User }
  | null;

export function UsersView() {
  const { t, locale } = useI18n();
  const { user: me, can } = useAuth();
  const canWrite = can("users:write");
  const isSuper = me?.role === "SUPER_ADMIN";

  const [search, setSearch] = useState("");
  const [role, setRole] = useState("");
  const [active, setActive] = useState("");
  const [offset, setOffset] = useState(0);
  const [dialog, setDialog] = useState<Dialog>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const { data, loading, error, reload } = useAsync(
    () =>
      api<Page<User>>("/users", {
        params: { search, role, active, limit: PAGE_SIZE, offset },
      }),
    [search, role, active, offset],
  );

  const roleOptions = isSuper ? ALL_ROLES : ALL_ROLES.filter((r) => !PRIVILEGED.includes(r));
  const manageable = (u: User) => canWrite && u.id !== me?.id && (isSuper || !PRIVILEGED.includes(u.role));

  const done = (message: string) => {
    setDialog(null);
    setActionError(null);
    setNotice(message);
    reload();
  };

  return (
    <div>
      <PageHeader
        title={t("users.title")}
        subtitle={t("users.subtitle")}
        actions={
          canWrite && (
            <button type="button" className="btn-primary" onClick={() => setDialog({ kind: "create" })}>
              {t("users.create")}
            </button>
          )
        }
      />
      {!canWrite && <p className="mb-4 text-sm text-slate-400">{t("users.readonly")}</p>}
      {notice && (
        <div className="mb-4">
          <SuccessBanner message={notice} />
        </div>
      )}

      <div className="mb-4 flex flex-wrap gap-3">
        <input
          className="input max-w-xs"
          type="search"
          placeholder={t("users.search")}
          aria-label={t("users.search")}
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setOffset(0);
          }}
        />
        <select className="input w-auto" aria-label={t("users.filter_role")} value={role} onChange={(e) => { setRole(e.target.value); setOffset(0); }}>
          <option value="">{t("users.filter_role")} : {t("common.all")}</option>
          {ALL_ROLES.map((r) => (
            <option key={r} value={r}>{t(`role.${r}`)}</option>
          ))}
        </select>
        <select className="input w-auto" aria-label={t("users.filter_status")} value={active} onChange={(e) => { setActive(e.target.value); setOffset(0); }}>
          <option value="">{t("users.filter_status")} : {t("common.all")}</option>
          <option value="true">{t("users.active")}</option>
          <option value="false">{t("users.disabled")}</option>
        </select>
      </div>

      {loading && !data ? (
        <Spinner />
      ) : error || !data ? (
        <ErrorBanner message={t("users.load_error")} onRetry={reload} />
      ) : data.items.length === 0 ? (
        <EmptyState message={t("users.empty")} />
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full">
            <thead className="border-b border-ink-700">
              <tr>
                <th className="th">{t("users.col_name")}</th>
                <th className="th">{t("users.col_email")}</th>
                <th className="th">{t("users.col_role")}</th>
                <th className="th">{t("users.col_status")}</th>
                <th className="th">{t("users.col_last_login")}</th>
                <th className="th">{t("common.actions")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-700">
              {data.items.map((u) => (
                <tr key={u.id}>
                  <td className="td font-medium">
                    {u.display_name} {u.id === me?.id && <span className="text-xs text-slate-500">({t("common.you")})</span>}
                  </td>
                  <td className="td text-slate-400">{u.email}</td>
                  <td className="td"><Badge tone={PRIVILEGED.includes(u.role) ? "info" : "neutral"}>{t(`role.${u.role}`)}</Badge></td>
                  <td className="td"><Badge tone={u.is_active ? "ok" : "danger"}>{u.is_active ? t("users.active") : t("users.disabled")}</Badge></td>
                  <td className="td text-slate-400">{u.last_login_at ? formatDateTime(u.last_login_at, locale) : t("common.never")}</td>
                  <td className="td">
                    {manageable(u) ? (
                      <div className="flex flex-wrap gap-1.5">
                        <button type="button" className="btn-secondary px-2 py-1 text-xs" onClick={() => setDialog({ kind: "edit", user: u })}>{t("users.edit")}</button>
                        <button type="button" className="btn-secondary px-2 py-1 text-xs" onClick={() => setDialog({ kind: "toggle", user: u })}>
                          {u.is_active ? t("users.disable") : t("users.enable")}
                        </button>
                        <button type="button" className="btn-secondary px-2 py-1 text-xs" onClick={() => setDialog({ kind: "revoke", user: u })}>{t("users.revoke_sessions")}</button>
                        {isSuper && (
                          <button type="button" className="btn-secondary px-2 py-1 text-xs" onClick={() => setDialog({ kind: "password", user: u })}>{t("users.reset_password")}</button>
                        )}
                      </div>
                    ) : (
                      <span className="text-slate-600">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex items-center justify-between border-t border-ink-700 px-3 py-2 text-xs text-slate-400">
            <span>{t("common.total", { count: data.total })}</span>
            <div className="flex gap-2">
              <button type="button" className="btn-secondary px-2 py-1 text-xs" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>{t("common.previous")}</button>
              <button type="button" className="btn-secondary px-2 py-1 text-xs" disabled={offset + PAGE_SIZE >= data.total} onClick={() => setOffset(offset + PAGE_SIZE)}>{t("common.next")}</button>
            </div>
          </div>
        </div>
      )}

      {dialog?.kind === "create" && (
        <UserFormModal roles={roleOptions} onClose={() => setDialog(null)} onDone={() => done(t("users.created"))} />
      )}
      {dialog?.kind === "edit" && (
        <UserFormModal user={dialog.user} roles={roleOptions} onClose={() => setDialog(null)} onDone={() => done(t("users.updated"))} />
      )}
      {dialog?.kind === "password" && (
        <PasswordModal user={dialog.user} onClose={() => setDialog(null)} onDone={() => done(t("users.password_reset_done"))} />
      )}
      {dialog?.kind === "toggle" && (
        <ActionConfirm
          title={dialog.user.is_active ? t("users.disable") : t("users.enable")}
          message={t(dialog.user.is_active ? "users.disable_confirm" : "users.enable_confirm", { name: dialog.user.display_name })}
          danger={dialog.user.is_active}
          error={actionError}
          onCancel={() => { setDialog(null); setActionError(null); }}
          run={() => api(`/users/${dialog.user.id}`, { method: "PATCH", body: { is_active: !dialog.user.is_active } })}
          onDone={() => done(t("users.updated"))}
          onError={setActionError}
        />
      )}
      {dialog?.kind === "revoke" && (
        <ActionConfirm
          title={t("users.revoke_sessions")}
          message={t("users.revoke_confirm", { name: dialog.user.display_name })}
          danger
          error={actionError}
          onCancel={() => { setDialog(null); setActionError(null); }}
          run={() => api(`/users/${dialog.user.id}/sessions`, { method: "DELETE" })}
          onDone={() => done(t("users.sessions_revoked"))}
          onError={setActionError}
        />
      )}
    </div>
  );
}

function ActionConfirm(props: {
  title: string;
  message: string;
  danger?: boolean;
  error: string | null;
  run: () => Promise<unknown>;
  onDone: () => void;
  onCancel: () => void;
  onError: (message: string) => void;
}) {
  const { t } = useI18n();
  const [busy, setBusy] = useState(false);
  return (
    <div>
      <ConfirmDialog
        title={props.title}
        message={props.message}
        danger={props.danger}
        busy={busy}
        onCancel={props.onCancel}
        onConfirm={async () => {
          setBusy(true);
          try {
            await props.run();
            props.onDone();
          } catch (e) {
            props.onError(t(errorKey(e)));
          } finally {
            setBusy(false);
          }
        }}
      />
      {props.error && (
        <div className="fixed bottom-4 left-1/2 z-[60] -translate-x-1/2">
          <ErrorBanner message={props.error} />
        </div>
      )}
    </div>
  );
}

function UserFormModal({ user, roles, onClose, onDone }: { user?: User; roles: Role[]; onClose: () => void; onDone: () => void }) {
  const { t } = useI18n();
  const [email, setEmail] = useState(user?.email ?? "");
  const [name, setName] = useState(user?.display_name ?? "");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>(user?.role ?? roles[roles.length - 1]);
  const [language, setLanguage] = useState<Language>(user?.preferred_language ?? "fr");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (user) {
        await api(`/users/${user.id}`, { method: "PATCH", body: { display_name: name, role, preferred_language: language } });
      } else {
        await api("/users", { method: "POST", body: { email, display_name: name, password, role, preferred_language: language } });
      }
      onDone();
    } catch (err) {
      setError(t(errorKey(err)));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title={user ? t("users.edit") : t("users.create")} onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        {!user && (
          <div>
            <label htmlFor="u-email" className="label">{t("users.col_email")}</label>
            <input id="u-email" type="email" required className="input" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
        )}
        <div>
          <label htmlFor="u-name" className="label">{t("users.display_name")}</label>
          <input id="u-name" required maxLength={120} className="input" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        {!user && (
          <div>
            <label htmlFor="u-pass" className="label">{t("users.password")}</label>
            <input id="u-pass" type="password" required minLength={12} autoComplete="new-password" className="input" value={password} onChange={(e) => setPassword(e.target.value)} />
            <p className="mt-1 text-xs text-slate-500">{t("users.password_hint")}</p>
          </div>
        )}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="u-role" className="label">{t("users.col_role")}</label>
            <select id="u-role" className="input" value={role} onChange={(e) => setRole(e.target.value as Role)}>
              {(roles.includes(role) ? roles : [role, ...roles]).map((r) => (
                <option key={r} value={r} disabled={!roles.includes(r)}>{t(`role.${r}`)}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="u-lang" className="label">{t("users.language")}</label>
            <select id="u-lang" className="input" value={language} onChange={(e) => setLanguage(e.target.value as Language)}>
              <option value="fr">{t("lang.fr")}</option>
              <option value="en">{t("lang.en")}</option>
            </select>
          </div>
        </div>
        {error && <ErrorBanner message={error} />}
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" className="btn-secondary" onClick={onClose}>{t("common.cancel")}</button>
          <button type="submit" className="btn-primary" disabled={busy}>{user ? t("common.save") : t("common.create")}</button>
        </div>
      </form>
    </Modal>
  );
}

function PasswordModal({ user, onClose, onDone }: { user: User; onClose: () => void; onDone: () => void }) {
  const { t } = useI18n();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api(`/users/${user.id}/password`, { method: "PUT", body: { new_password: password } });
      onDone();
    } catch (err) {
      setError(t(errorKey(err)));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title={`${t("users.reset_password")} — ${user.display_name}`} onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <div>
          <label htmlFor="p-new" className="label">{t("users.new_password")}</label>
          <input id="p-new" type="password" required minLength={12} autoComplete="new-password" className="input" value={password} onChange={(e) => setPassword(e.target.value)} />
          <p className="mt-1 text-xs text-slate-500">{t("users.password_hint")}</p>
        </div>
        {error && <ErrorBanner message={error} />}
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" className="btn-secondary" onClick={onClose}>{t("common.cancel")}</button>
          <button type="submit" className="btn-danger" disabled={busy}>{t("common.confirm")}</button>
        </div>
      </form>
    </Modal>
  );
}
