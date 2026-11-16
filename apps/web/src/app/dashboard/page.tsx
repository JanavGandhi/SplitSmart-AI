"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, LoaderCircle, Plus, ReceiptText, Users } from "lucide-react";
import SiteHeader from "@/components/SiteHeader";
import DemoLaunchButton from "@/components/DemoLaunchButton";
import ReceiptUploadForm from "@/components/ReceiptUploadForm";
import { api } from "@/lib/api";
import type { Group } from "@/lib/types";

export default function DashboardPage() {
  const router = useRouter();
  const [groups, setGroups] = useState<Group[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [groupName, setGroupName] = useState("");
  const [creating, setCreating] = useState(false);
  const [selectedGroupId, setSelectedGroupId] = useState("");
  const [roomCode, setRoomCode] = useState("");

  const refreshGroups = useCallback(async () => {
    try {
      const result = await api.groups.list();
      setGroups(result);
      setError(null);
      setSelectedGroupId((current) =>
        result.some((group) => group.id === current) ? current : (result[0]?.id ?? ""),
      );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Groups could not be loaded");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshGroups();
  }, [refreshGroups]);

  async function createGroup(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = groupName.trim();
    if (!name) return;
    setCreating(true);
    setError(null);
    try {
      const group = await api.groups.create({ name });
      setGroupName("");
      await refreshGroups();
      router.push(`/groups/${group.id}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Group could not be created");
    } finally {
      setCreating(false);
    }
  }

  function openRoom(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const code = roomCode.trim().toUpperCase();
    if (code) router.push(`/room/${encodeURIComponent(code)}`);
  }

  return (
    <main className="min-h-screen">
      <SiteHeader />
      <div className="mx-auto max-w-7xl px-5 pb-20 pt-10 sm:px-8 sm:pt-14">
        <div className="mb-9 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="section-label">Your workspace</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">Dashboard<span className="text-indigo-300">.</span></h1>
            <p className="mt-2 max-w-xl text-sm leading-relaxed text-slate-400">
              Organize group expenses, scan a receipt, or jump into a shared claim room.
            </p>
          </div>
          <DemoLaunchButton className="btn-primary justify-center px-5 py-3" />
        </div>

        <div className="grid gap-5 lg:grid-cols-[1.4fr_.8fr]">
          <section className="glass-card p-5 sm:p-6">
            <div className="mb-5 flex items-center justify-between gap-3">
              <div>
                <p className="section-label">Groups</p>
                <h2 className="mt-1 text-lg font-semibold">Recent activity</h2>
              </div>
              <span className="rounded-full border border-white/10 px-3 py-1 text-xs text-slate-500">{groups.length} total</span>
            </div>
            {error && <p role="alert" className="mb-4 rounded-xl border border-rose-400/20 bg-rose-400/[0.06] p-3 text-sm text-rose-200">{error}</p>}
            {loading ? (
              <div className="flex items-center gap-2 py-10 text-sm text-slate-500"><LoaderCircle size={16} className="animate-spin" /> Loading groups…</div>
            ) : groups.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-white/10 px-5 py-10 text-center">
                <Users className="mx-auto text-slate-600" size={24} />
                <p className="mt-3 font-medium">No groups yet</p>
                <p className="mt-1 text-sm text-slate-500">Create a group or launch the demo to get started.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {groups.map((group) => (
                  <Link key={group.id} href={`/groups/${group.id}`} className="group flex items-center justify-between gap-4 rounded-xl border border-white/[0.06] bg-white/[0.02] px-4 py-4 transition hover:border-indigo-300/25 hover:bg-indigo-300/[0.035]">
                    <span className="min-w-0">
                      <span className="block truncate font-medium">{group.name}</span>
                      <span className="mt-1 flex items-center gap-1.5 text-xs text-slate-500"><Users size={12} /> {group.member_count} members · {group.currency}</span>
                    </span>
                    <ArrowRight size={17} className="shrink-0 text-slate-600 transition group-hover:translate-x-1 group-hover:text-indigo-200" />
                  </Link>
                ))}
              </div>
            )}
            <form onSubmit={createGroup} className="mt-5 flex flex-col gap-2 border-t border-white/[0.06] pt-5 sm:flex-row">
              <label htmlFor="new-group-name" className="sr-only">New group name</label>
              <input id="new-group-name" value={groupName} onChange={(event) => setGroupName(event.target.value)} maxLength={200} required placeholder="e.g. Weekend in Goa" className="min-w-0 flex-1 rounded-xl border border-white/10 bg-white/[0.035] px-4 py-3 text-sm outline-none placeholder:text-slate-600 focus:border-indigo-300/40" />
              <button type="submit" disabled={!groupName.trim() || creating} className="btn-secondary justify-center disabled:opacity-50">
                {creating ? <LoaderCircle size={15} className="animate-spin" /> : <Plus size={15} />} New group
              </button>
            </form>
          </section>

          <div className="space-y-5">
            <ReceiptUploadForm groupId={selectedGroupId || null} />
            {groups.length > 0 && (
              <label className="block text-xs text-slate-500">
                Upload into
                <select value={selectedGroupId} onChange={(event) => setSelectedGroupId(event.target.value)} className="mt-2 w-full rounded-xl border border-white/10 bg-[#0d1222] px-3 py-3 text-sm text-slate-200 outline-none focus:border-indigo-300/40">
                  {groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}
                </select>
              </label>
            )}
            <section className="glass-card p-5">
              <div className="flex items-start gap-3">
                <span className="rounded-xl bg-indigo-400/10 p-2.5 text-indigo-200"><ReceiptText size={18} /></span>
                <div>
                  <h2 className="font-semibold">Join a claim room</h2>
                  <p className="mt-1 text-sm text-slate-500">Enter the room code shared by your group.</p>
                </div>
              </div>
              <form onSubmit={openRoom} className="mt-4 flex gap-2">
                <label htmlFor="room-code" className="sr-only">Room code</label>
                <input id="room-code" value={roomCode} onChange={(event) => setRoomCode(event.target.value.toUpperCase())} maxLength={12} required placeholder="ROOM CODE" className="min-w-0 flex-1 rounded-xl border border-white/10 bg-white/[0.035] px-4 py-3 font-mono text-sm tracking-widest outline-none placeholder:text-slate-600 focus:border-indigo-300/40" />
                <button type="submit" className="btn-secondary px-4" aria-label="Open room"><ArrowRight size={17} /></button>
              </form>
            </section>
          </div>
        </div>
      </div>
    </main>
  );
}
