"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api, ApiError, API_BASE_URL, SESSION_EXPIRED_EVENT } from "@/lib/api";
import { GmailPanel } from "../dashboard/gmail-panel";

type User = { email: string; name?: string };
type Application = { id: number; company: string; role: string };

async function loadApplications(signal?: AbortSignal): Promise<Application[]> {
  const applications: Application[] = [];
  for (let offset = 0; ; offset += 500) {
    const page = await api<Application[]>(`/applications?limit=500&offset=${offset}`, { signal });
    applications.push(...page);
    if (page.length < 500) return applications;
  }
}

export default function SettingsPage() {
  const [user, setUser] = useState<User | null>(null);
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    const expire = () => { setUser(null); setApplications([]); };
    window.addEventListener(SESSION_EXPIRED_EVENT, expire);
    async function load() {
      try {
        const auth = await api<{ user: User }>("/auth/me", { signal: controller.signal });
        const applications = await loadApplications(controller.signal);
        setUser(auth.user); setApplications(applications);
      } catch (e) {
        if (!controller.signal.aborted && !(e instanceof ApiError && e.status === 401)) setError("Could not load account settings. Please retry.");
      } finally { if (!controller.signal.aborted) setLoading(false); }
    }
    void load();
    return () => { controller.abort(); window.removeEventListener(SESSION_EXPIRED_EVENT, expire); };
  }, []);

  const refresh = useCallback(async () => setApplications(await loadApplications()), []);
  return <main className="min-h-screen bg-slate-950 px-4 py-10 text-white sm:px-8">
    <div className="mx-auto max-w-5xl">
      <nav className="mb-8 flex gap-6 text-cyan-300"><Link href="/">FlowState</Link><Link href="/dashboard">Application workspace</Link></nav>
      <h1 className="mb-3 text-3xl font-bold">Account settings</h1>
      {loading ? <p aria-busy="true">Loading your account…</p> : user ? <>
        <p className="mb-6 text-slate-300">{user.name || "Google account"} · {user.email}</p>
        <GmailPanel applications={applications} onSynced={refresh} />
        <p className="text-sm text-slate-400">Disconnecting Gmail removes email metadata and revokes access. Your applications remain until you delete them or delete your account.</p>
      </> : <a className="text-cyan-300 underline" href={`${API_BASE_URL}/auth/google/login`}>Sign in with Google</a>}
      {error && <p role="alert" className="mt-5 text-rose-300">{error}</p>}
    </div>
  </main>;
}
