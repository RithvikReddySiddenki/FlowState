"use client";

import { useEffect, useState } from "react";
import { api, ApiError, API_BASE_URL } from "@/lib/api";

type Application = {
  id: number; company: string; role: string; current_status: string;
  action_required: boolean; deadline: string | null; updated_at: string;
};
type History = { id: number; current_status: string; source: string; created_at: string };
type User = { email: string; name?: string };
const stages = ["Application Received", "Under Review", "Assessment Invite", "Interview Scheduled", "Offer", "Rejected"];
const blank = { company: "", role: "", current_status: stages[0], action_required: false, deadline: "" };
const input = "w-full rounded-lg border border-slate-600 bg-slate-950 p-3 text-white focus:outline-2 focus:outline-cyan-400";
const button = "rounded-lg bg-cyan-300 px-4 py-2 font-semibold text-slate-950 disabled:opacity-50";

export default function DashboardPage() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [applications, setApplications] = useState<Application[]>([]);
  const [form, setForm] = useState(blank);
  const [editing, setEditing] = useState<number | null>(null);
  const [selected, setSelected] = useState<Application | null>(null);
  const [history, setHistory] = useState<History[]>([]);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [sort, setSort] = useState("updated");

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const auth = await api<{ user: User }>("/auth/me", { signal: controller.signal });
        const rows: Application[] = [];
        for (let offset = 0; ; offset += 500) {
          const page = await api<Application[]>(`/applications?limit=500&offset=${offset}`, { signal: controller.signal });
          rows.push(...page);
          if (page.length < 500) break;
        }
        setUser(auth.user);
        setApplications(rows);
      } catch (e) {
        if (controller.signal.aborted) return;
        if (!(e instanceof ApiError && e.status === 401)) setError("Could not load your account. Check the API connection and retry.");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, []);

  async function refresh() {
    const rows: Application[] = [];
    for (let offset = 0; ; offset += 500) {
      const page = await api<Application[]>(`/applications?limit=500&offset=${offset}`);
      rows.push(...page);
      if (page.length < 500) break;
    }
    setApplications(rows);
  }

  async function perform(action: () => Promise<void>) {
    setBusy(true); setError("");
    try { await action(); }
    catch (e) {
      if (e instanceof ApiError && e.status === 401) { setUser(null); setApplications([]); setSelected(null); }
      setError(e instanceof Error ? e.message : "Something went wrong. Please retry.");
    } finally { setBusy(false); }
  }

  const filtered = applications.filter(a =>
    `${a.company} ${a.role}`.toLowerCase().includes(search.toLowerCase()) &&
    (!status || (status === "Action Required" ? a.action_required : a.current_status === status))
  ).sort((a, b) => sort === "company" ? a.company.localeCompare(b.company) : b.updated_at.localeCompare(a.updated_at));

  if (loading) return <main className="min-h-screen bg-slate-950 p-10 text-white" aria-busy="true">Loading your workspace…</main>;
  if (!user) return <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-slate-950 p-6 text-white">
    <h1 className="text-3xl font-bold">Your next chapter starts here.</h1>
    <p className="text-slate-300">Sign in to manage your private application tracker.</p>
    {error && <p role="alert">{error}</p>}
    <a className={button} href={`${API_BASE_URL}/auth/google/login`}>Sign in with Google</a>
    <button onClick={() => window.location.reload()} className="underline">Retry connection</button>
  </main>;

  return <main className="min-h-screen bg-slate-950 px-4 py-8 text-slate-100 sm:px-8">
    <div className="mx-auto max-w-7xl">
      <header className="mb-10 flex flex-wrap items-center justify-between gap-4">
        <div><p className="text-sm font-semibold uppercase tracking-widest text-cyan-300">FlowState</p>
          <h1 className="mt-2 text-3xl font-bold sm:text-4xl">Application workspace</h1>
          <p className="mt-2 text-slate-400">Keep every opportunity moving forward.</p></div>
        <div className="flex flex-wrap items-center gap-4"><span>{user.email}</span>
          <button disabled={busy} className="rounded-lg border border-slate-600 px-4 py-2" onClick={() => void perform(async () => {
            await api("/auth/logout", { method: "POST" }); setUser(null); setApplications([]); setSelected(null);
          })}>Sign out</button></div>
      </header>
      {error && <div role="alert" className="mb-6 rounded-lg border border-rose-400 bg-rose-950 p-4">{error}</div>}
      <section aria-label="Application metrics" className="mb-8 grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-8">
        {["Total", ...stages, "Action Required"].map(label => <div key={label} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
          <p className="text-xs text-slate-400">{label}</p><p className="mt-2 text-3xl font-semibold">{label === "Total" ? applications.length : applications.filter(a => label === "Action Required" ? a.action_required : a.current_status === label).length}</p>
        </div>)}
      </section>
      <div className="grid items-start gap-8 lg:grid-cols-[320px_1fr]">
        <form className="space-y-4 rounded-xl border border-slate-800 bg-slate-900 p-6" onSubmit={event => {
          event.preventDefault();
          void perform(async () => {
            await api(editing ? `/applications/${editing}` : "/applications", {
              method: editing ? "PATCH" : "POST", body: JSON.stringify({ ...form, deadline: form.deadline ? new Date(form.deadline).toISOString() : null }),
            });
            setForm(blank); setEditing(null); await refresh();
          });
        }}>
          <h2 className="text-xl font-semibold">{editing ? "Edit application" : "Add application"}</h2>
          <label className="block">Company<input className={input} required maxLength={255} value={form.company} onChange={e => setForm({ ...form, company: e.target.value })} /></label>
          <label className="block">Role<input className={input} required maxLength={255} value={form.role} onChange={e => setForm({ ...form, role: e.target.value })} /></label>
          <label className="block">Recruiting stage<select className={input} value={form.current_status} onChange={e => setForm({ ...form, current_status: e.target.value })}>{stages.map(s => <option key={s}>{s}</option>)}</select></label>
          <label className="flex gap-2"><input type="checkbox" checked={form.action_required} onChange={e => setForm({ ...form, action_required: e.target.checked })} />Action required</label>
          <label className="block">Deadline (your local time)<input type="datetime-local" className={input} value={form.deadline} onChange={e => setForm({ ...form, deadline: e.target.value })} /></label>
          <button className={button} disabled={busy}>{busy ? "Saving…" : editing ? "Save changes" : "Add application"}</button>
          {editing && <button type="button" className="ml-3 underline" onClick={() => { setEditing(null); setForm(blank); }}>Cancel</button>}
        </form>
        <section aria-label="Applications" className="min-w-0">
          <div className="mb-5 grid gap-3 sm:grid-cols-3">
            <label>Search<input className={input} type="search" placeholder="Company or role" value={search} onChange={e => setSearch(e.target.value)} /></label>
            <label>Status<select className={input} value={status} onChange={e => setStatus(e.target.value)}><option value="">All statuses</option>{[...stages, "Action Required"].map(s => <option key={s}>{s}</option>)}</select></label>
            <label>Sort<select className={input} value={sort} onChange={e => setSort(e.target.value)}><option value="updated">Recently updated</option><option value="company">Company A–Z</option></select></label>
          </div>
          <p className="mb-4 text-sm text-slate-400">{filtered.length} of {applications.length} applications</p>
          {!filtered.length && <p className="rounded-xl border border-dashed border-slate-700 p-10 text-center text-slate-400">{applications.length ? "No applications match your filters." : "Add your first application to get started."}</p>}
          <div className="space-y-3">{filtered.map(a => <article key={a.id} className="rounded-xl border border-slate-800 bg-slate-900 p-5">
            <div className="flex flex-wrap justify-between gap-3"><div><h2 className="text-xl font-semibold">{a.company}</h2><p className="text-slate-300">{a.role}</p></div><span className="h-fit rounded-full bg-slate-800 px-3 py-1 text-sm text-cyan-200">{a.current_status}</span></div>
            {a.action_required && <p className="mt-3 text-amber-300">Action required{a.deadline ? ` · Due ${new Date(a.deadline).toLocaleString()}` : ""}</p>}
            <div className="mt-4 flex flex-wrap gap-5 text-sm">
              <button disabled={busy} className="text-cyan-300 underline" onClick={() => {
                setEditing(a.id); setForm({ company: a.company, role: a.role, current_status: a.current_status, action_required: a.action_required, deadline: a.deadline ? new Date(new Date(a.deadline).getTime() - new Date(a.deadline).getTimezoneOffset() * 60000).toISOString().slice(0, 16) : "" });
                window.scrollTo({ top: 0, behavior: "smooth" });
              }}>Edit</button>
              <button disabled={busy} className="text-cyan-300 underline" onClick={() => void perform(async () => {
                const rows = await api<History[]>(`/applications/${a.id}/history`); setHistory(rows); setSelected(a);
              })}>View history</button>
              <button disabled={busy} className="text-rose-300 underline" onClick={() => {
                if (window.confirm(`Delete ${a.company} — ${a.role}? This also deletes its history.`)) void perform(async () => {
                  await api(`/applications/${a.id}`, { method: "DELETE" }); if (selected?.id === a.id) setSelected(null); if (editing === a.id) { setEditing(null); setForm(blank); } await refresh();
                });
              }}>Delete</button>
            </div>
          </article>)}</div>
          {selected && <section className="mt-6 rounded-xl border border-cyan-700 p-5" aria-label="Status history">
            <div className="flex justify-between gap-4"><h2 className="text-xl font-semibold">{selected.company} · History</h2><button className="underline" onClick={() => setSelected(null)}>Close</button></div>
            <ol className="mt-4 space-y-3">{history.map(h => <li key={h.id}><strong>{h.current_status}</strong><p className="text-sm text-slate-400">{new Date(h.created_at).toLocaleString()} · {h.source}</p></li>)}</ol>
          </section>}
        </section>
      </div>
    </div>
  </main>;
}
