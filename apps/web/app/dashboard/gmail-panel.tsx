"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, API_BASE_URL } from "@/lib/api";

type Run = { id: string; status: string; processed: number; imported: number; error: string | null };
type Connection = { connected: boolean; last_synced_at: string | null; latest_run: Run | null };
export type Message = { id: number; subject: string; sender: string; snippet: string; confidence: number; explanation: string; detected_status: string | null; review_required: boolean };

export function GmailPanel({ applications, onSynced }: { applications: { id: number; company: string; role: string }[]; onSynced: () => Promise<void> }) {
  const router = useRouter();
  const [connection, setConnection] = useState<Connection | null>(null);
  const [review, setReview] = useState<Message[]>([]);
  const [run, setRun] = useState<Run | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    const [value, messages] = await Promise.all([api<Connection>("/gmail/connection"), api<Message[]>("/gmail/review")]);
    setConnection(value); setRun(value.latest_run); setReview(messages);
  }, []);

  useEffect(() => {
    let live = true;
    Promise.all([api<Connection>("/gmail/connection"), api<Message[]>("/gmail/review")])
      .then(([value, messages]) => { if (live) { setConnection(value); setRun(value.latest_run); setReview(messages); } })
      .catch(() => { if (live) setError("Gmail connection could not be loaded."); });
    return () => { live = false; };
  }, []);

  useEffect(() => {
    if (!run || !["queued", "running"].includes(run.status)) return;
    let live = true;
    const timer = setInterval(async () => {
      try {
        const next = await api<Run>(`/gmail/sync/status/${run.id}`);
        if (!live) return;
        setRun(next);
        if (!["queued", "running"].includes(next.status)) { await reload(); await onSynced(); }
      } catch { if (live) setError("Sync status unavailable. Check your connection and retry."); }
    }, 3000);
    return () => { live = false; clearInterval(timer); };
  }, [run, reload, onSynced]);

  async function perform(action: () => Promise<void>) {
    setBusy(true); setError("");
    try { await action(); } catch (e) { setError(e instanceof Error ? e.message : "Please retry."); }
    finally { setBusy(false); }
  }
  return <section aria-label="Gmail and account settings" className="mb-8 rounded-xl border border-slate-700 bg-slate-900 p-5">
    <div className="flex flex-wrap items-center justify-between gap-4"><div><h2 className="text-xl font-semibold">Gmail activity</h2>
      <p className="mt-1 text-sm text-slate-400">{connection ? connection.connected ? "Connected with read-only access" : "Connect Gmail to find recruiting updates" : "Loading connection…"}</p>
      {connection?.last_synced_at && <p className="text-sm text-slate-400">Last successful sync: {new Date(connection.last_synced_at).toLocaleString()}</p>}</div>
      <div className="flex flex-wrap gap-4">
        {connection?.connected ? <><button className="rounded-lg bg-cyan-300 px-4 py-2 font-semibold text-slate-950 disabled:opacity-50" disabled={busy} onClick={() => void perform(async () => setRun(await api<Run>("/gmail/sync/start", { method: "POST" })))}>Sync / retry Gmail</button>
          <button className="underline" disabled={busy} onClick={() => { if (window.confirm("Disconnect Gmail? This revokes access and deletes stored email metadata. Your applications remain.")) void perform(async () => { await api("/gmail/disconnect", { method: "POST" }); await reload(); }); }}>Disconnect</button></>
          : connection && <a className="rounded-lg bg-cyan-300 px-4 py-2 font-semibold text-slate-950" href={`${API_BASE_URL}/auth/google/login?gmail=true`}>Connect Gmail</a>}
        <button className="underline" disabled={busy} onClick={() => void perform(reload)}>Refresh activity</button>
        <button className="text-rose-300 underline" disabled={busy} onClick={() => { if (window.confirm("Permanently delete your FlowState account and all application data? Gmail access will be revoked.")) void perform(async () => { await api("/account", { method: "DELETE" }); router.push("/"); }); }}>Delete account</button>
      </div>
    </div>
    {run && <p className="mt-4" role="status">Sync {run.status} · {run.processed} processed · {run.imported} imported{run.error ? ` · ${run.error}` : ""}</p>}
    {error && <p role="alert" className="mt-4 text-rose-300">{error}</p>}
    {review.length > 0 && <details className="mt-5"><summary className="cursor-pointer text-amber-300">{review.length} messages need review (up to 200 shown)</summary>
      <div className="mt-4 space-y-4">{review.map(message => <form key={message.id} className="rounded-lg border border-slate-700 p-4" onSubmit={event => {
        event.preventDefault(); const values = new FormData(event.currentTarget);
        void perform(async () => { await api(`/gmail/review/${message.id}`, { method: "PATCH", body: JSON.stringify({ application_id: Number(values.get("application")), apply_status: values.get("apply") === "on" }) }); await reload(); await onSynced(); });
      }}><MessageDetail message={message} />
        <label className="mt-3 block">Associate with application<select required name="application" className="mt-1 w-full rounded border border-slate-600 bg-slate-950 p-2"><option value="">Choose an application</option>{applications.map(a => <option key={a.id} value={a.id}>{a.company} · {a.role}</option>)}</select></label>
        {message.detected_status && <label className="mt-3 flex gap-2"><input type="checkbox" name="apply" />Apply stage: {message.detected_status} (manual correction)</label>}
        <button disabled={busy} className="mt-3 rounded bg-slate-700 px-3 py-2">Confirm association</button>
      </form>)}</div></details>}
  </section>;
}

export function MessageDetail({ message }: { message: Message }) {
  return <div><h3 className="font-semibold">{message.subject}</h3><p className="text-sm text-slate-400">{message.sender} · {Math.round(message.confidence * 100)}% confidence</p><p className="mt-2 text-sm">{message.snippet}</p><p className="mt-1 text-sm text-slate-400">{message.explanation}</p></div>;
}
