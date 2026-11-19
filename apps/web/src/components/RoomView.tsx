"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Check, Copy, LoaderCircle, LockKeyhole, Radio, Users, WandSparkles } from "lucide-react";
import AvatarPill from "@/components/AvatarPill";
import ReceiptCard from "@/components/ReceiptCard";
import SiteHeader from "@/components/SiteHeader";
import { useRoomWebSocket } from "@/hooks/useRoomWebSocket";
import { api } from "@/lib/api";
import { paiseToCurrency } from "@/lib/currency";
import type { FinalizeResponse, Receipt, RoomEvent, UserPublic } from "@/lib/types";

interface StoredGuest {
  token: string;
  user: UserPublic;
}

export default function RoomView({ roomCode: rawRoomCode }: { roomCode: string }) {
  const roomCode = rawRoomCode.toUpperCase();
  const router = useRouter();
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [guest, setGuest] = useState<StoredGuest | null>(null);
  const [joining, setJoining] = useState(false);
  const [payerId, setPayerId] = useState("");
  const [finalizing, setFinalizing] = useState(false);
  const [finalizeResult, setFinalizeResult] = useState<FinalizeResponse | null>(null);
  const [copyState, setCopyState] = useState<"idle" | "copied" | "failed">("idle");
  const [liveTotals, setLiveTotals] = useState<Record<string, number> | null>(null);
  const finalizeKey = useRef<string | null>(null);
  const { state: connection, events, send } = useRoomWebSocket(roomCode, guest?.token ?? null);

  const refreshReceipt = useCallback(async () => {
    try {
      const current = await api.receipts.byRoomCode(roomCode);
      setReceipt(current);
      setError(null);
      setPayerId((selected) => selected || current.paid_by || "");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The room could not be loaded");
    } finally {
      setLoading(false);
    }
  }, [roomCode]);

  useEffect(() => {
    void refreshReceipt();
  }, [refreshReceipt]);

  useEffect(() => {
    if (!receipt || !["QUEUED", "PROCESSING"].includes(receipt.status)) return;
    const timer = window.setInterval(() => void refreshReceipt(), 2500);
    return () => window.clearInterval(timer);
  }, [receipt, refreshReceipt]);

  useEffect(() => {
    try {
      const stored = sessionStorage.getItem(`splitsmart.room.${roomCode}`);
      if (stored) {
        const parsed = JSON.parse(stored) as StoredGuest;
        if (parsed.token && parsed.user?.id) setGuest(parsed);
      }
    } catch {
      sessionStorage.removeItem(`splitsmart.room.${roomCode}`);
    }
  }, [roomCode]);

  useEffect(() => {
    const newest = events[events.length - 1];
    if (!newest) return;
    if (newest.event === "TAX_RECALCULATED") {
      setLiveTotals(newest.per_user_totals);
      void refreshReceipt();
    } else if (newest.event === "ITEM_CLAIM_TOGGLED" || newest.event === "RECEIPT_LOCKED") {
      void refreshReceipt();
    }
  }, [events, refreshReceipt]);

  const participants = useMemo(() => {
    const all = new Map<string, UserPublic>();
    receipt?.line_items.forEach((item) =>
      item.claims.forEach((claim) => all.set(claim.user.id, claim.user)),
    );
    if (guest) all.set(guest.user.id, guest.user);
    events.forEach((event) => {
      if (event.event === "PARTICIPANT_JOINED") {
        all.set(event.user_id, {
          id: event.user_id,
          display_name: event.display_name,
          avatar_color: event.avatar_color,
          is_guest: true,
        });
      }
    });
    return Array.from(all.values());
  }, [events, guest, receipt]);

  const totals = useMemo(() => {
    if (liveTotals) return liveTotals;
    const result: Record<string, number> = {};
    receipt?.line_items.forEach((item) =>
      item.claims.forEach((claim) => {
        result[claim.user.id] = (result[claim.user.id] ?? 0) + claim.calculated_final_paise;
      }),
    );
    return result;
  }, [liveTotals, receipt]);

  async function joinRoom(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = displayName.trim();
    if (!name) return;
    setJoining(true);
    setError(null);
    try {
      const result = await api.rooms.guestJoin(roomCode, name);
      const saved = { token: result.access_token, user: result.user };
      sessionStorage.setItem(`splitsmart.room.${roomCode}`, JSON.stringify(saved));
      setGuest(saved);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not join this room");
    } finally {
      setJoining(false);
    }
  }

  async function shareRoom() {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopyState("copied");
      window.setTimeout(() => setCopyState("idle"), 1800);
    } catch {
      setCopyState("failed");
    }
  }

  async function finalize() {
    if (!guest?.token || !payerId) return;
    setFinalizing(true);
    setError(null);
    try {
      finalizeKey.current ??= crypto.randomUUID();
      const result = await api.rooms.finalize(
        roomCode,
        { payer_user_id: payerId, idempotency_key: finalizeKey.current },
        guest.token,
      );
      setFinalizeResult(result);
      await refreshReceipt();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not finalize the split");
    } finally {
      setFinalizing(false);
    }
  }

  if (loading) {
    return (
      <main className="min-h-screen">
        <SiteHeader backHref="/dashboard" />
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-5 py-20 text-sm text-slate-400 sm:px-8">
          <LoaderCircle size={17} className="animate-spin" /> Finding your receipt…
        </div>
      </main>
    );
  }

  if (!receipt) {
    return (
      <main className="min-h-screen">
        <SiteHeader backHref="/dashboard" />
        <div className="mx-auto max-w-xl px-5 py-16 sm:px-8">
          <div role="alert" className="rounded-2xl border border-rose-400/20 bg-rose-400/[0.07] p-5 text-rose-200">{error ?? "Room not found"}</div>
          <Link href="/dashboard" className="mt-5 inline-flex text-sm text-indigo-200 hover:text-white">Return to dashboard →</Link>
        </div>
      </main>
    );
  }

  const isOpen = receipt.status === "READY_FOR_CLAIMS";
  const allItemsClaimed = receipt.line_items.length > 0 && receipt.line_items.every((item) => item.claims.length > 0);
  const lastError = [...events].reverse().find((event) => event.event === "ERROR") as Extract<RoomEvent, { event: "ERROR" }> | undefined;

  return (
    <main className="min-h-screen">
      <SiteHeader backHref="/dashboard" />
      <div className="mx-auto max-w-6xl px-5 pb-24 pt-8 sm:px-8 sm:pt-12">
        <div className="mb-7 flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <p className="section-label">Shared claim room</p>
              <span className={`rounded-full border px-2.5 py-1 text-[10px] ${isOpen ? "border-teal-300/20 bg-teal-300/[0.07] text-teal-200" : "border-white/10 bg-white/[0.04] text-slate-400"}`}>
                {receipt.status.replaceAll("_", " ")}
              </span>
            </div>
            <h1 className="mt-2 truncate text-3xl font-semibold tracking-tight sm:text-4xl">{receipt.merchant_name ?? "Receipt"}<span className="text-teal-300">.</span></h1>
            <p className="mt-2 flex flex-wrap items-center gap-2 text-sm text-slate-500">
              Room code <span className="font-mono tracking-widest text-slate-300">{roomCode}</span>
              <span>·</span> {receipt.line_items.length} items
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-2 text-xs ${connection === "connected" ? "border-teal-300/20 text-teal-200" : "border-white/10 text-slate-500"}`}>
              <Radio size={13} className={connection === "connected" ? "animate-pulse" : ""} /> {connection}
            </span>
            <button type="button" onClick={shareRoom} className="btn-secondary px-4 py-2.5">
              {copyState === "copied" ? <Check size={15} /> : <Copy size={15} />}
              {copyState === "failed" ? "Copy unavailable" : copyState === "copied" ? "Link copied" : "Share room"}
            </button>
          </div>
        </div>

        {error && <div role="alert" className="mb-5 rounded-xl border border-rose-400/20 bg-rose-400/[0.06] p-3 text-sm text-rose-200">{error}</div>}
        {lastError && <div role="alert" className="mb-5 rounded-xl border border-amber-300/20 bg-amber-300/[0.06] p-3 text-sm text-amber-100">{lastError.detail}</div>}

        {!guest && isOpen && (
          <form onSubmit={joinRoom} className="glass-card mb-5 flex flex-col gap-3 p-5 sm:flex-row sm:items-end">
            <div className="flex-1">
              <label htmlFor="guest-name" className="section-label">Join as a guest</label>
              <input id="guest-name" value={displayName} onChange={(event) => setDisplayName(event.target.value)} maxLength={100} required placeholder="Your name" className="mt-2 w-full rounded-xl border border-white/10 bg-white/[0.035] px-4 py-3 text-sm outline-none placeholder:text-slate-600 focus:border-indigo-300/40" />
            </div>
            <button type="submit" disabled={!displayName.trim() || joining} className="btn-primary justify-center disabled:opacity-50">
              {joining ? <LoaderCircle size={16} className="animate-spin" /> : <Users size={16} />} Join room
            </button>
          </form>
        )}

        <div className="grid gap-5 lg:grid-cols-[1.4fr_.8fr]">
          <section className="glass-card p-5 sm:p-6">
            <div className="mb-5 flex items-center justify-between gap-3">
              <div>
                <p className="section-label">Receipt items</p>
                <h2 className="mt-1 text-lg font-semibold">Tap what you shared</h2>
              </div>
              <span className="font-mono text-sm text-slate-300">{paiseToCurrency(receipt.total_paise)}</span>
            </div>
            {receipt.line_items.length === 0 ? (
              <div className="rounded-xl border border-dashed border-white/10 p-8 text-center text-sm text-slate-500">
                Receipt items are still being processed.
                <button type="button" onClick={() => router.refresh()} className="mt-3 block w-full text-indigo-200">Refresh receipt</button>
              </div>
            ) : (
              <div className="space-y-2">
                {receipt.line_items.map((item) => (
                  <ReceiptCard
                    key={item.id}
                    item={item}
                    currentUserId={guest?.user.id ?? null}
                    disabled={!guest || !isOpen || connection !== "connected"}
                    onToggle={(itemId) => { send({ event: "ITEM_CLAIM_TOGGLED", item_id: itemId }); }}
                  />
                ))}
              </div>
            )}
            {isOpen && guest && connection !== "connected" && (
              <p className="mt-3 text-xs text-amber-200/80">Reconnect to the live room before changing claims.</p>
            )}
          </section>

          <aside className="space-y-5">
            <section className="glass-card p-5">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <p className="section-label">Roommates</p>
                  <h2 className="mt-1 text-lg font-semibold">{participants.length} here</h2>
                </div>
                <Users size={17} className="text-slate-500" />
              </div>
              <div className="flex flex-wrap gap-2">
                {participants.length > 0 ? participants.map((person) => <AvatarPill key={person.id} person={person} active={person.id === guest?.user.id} compact />) : (
                  <p className="text-sm text-slate-500">Join to be the first in the room.</p>
                )}
              </div>
              <button type="button" disabled={connection !== "connected"} onClick={() => send({ event: "SIMULATE_FRIENDS" })} className="btn-secondary mt-4 w-full justify-center disabled:opacity-50">
                <WandSparkles size={15} /> Simulate 3 roommates
              </button>
              <p className="mt-2 text-center text-[10px] text-slate-600">Demo action: one guest appears every 2 seconds.</p>
            </section>

            <section className="glass-card p-5">
              <p className="section-label">Live totals</p>
              <div className="mt-3 space-y-2">
                {Object.entries(totals).length === 0 ? (
                  <p className="text-sm text-slate-500">Claim an item to see your split.</p>
                ) : Object.entries(totals).map(([id, amount]) => (
                  <div key={id} className="flex items-center justify-between gap-3 rounded-xl bg-white/[0.025] px-3 py-2.5">
                    <span className="truncate text-sm text-slate-300">{participants.find((person) => person.id === id)?.display_name ?? "Guest"}</span>
                    <span className="font-mono text-sm">{paiseToCurrency(amount)}</span>
                  </div>
                ))}
              </div>
              <div className="mt-4 flex justify-between border-t border-white/[0.07] pt-4 text-sm">
                <span className="text-slate-500">Receipt total</span>
                <span className="font-mono">{paiseToCurrency(receipt.total_paise)}</span>
              </div>
            </section>

            {isOpen && guest && (
              <section className="glass-card p-5">
                <p className="section-label">Ready to close?</p>
                <label htmlFor="payer-user" className="mt-3 block text-xs text-slate-500">Who paid the bill?</label>
                <select id="payer-user" value={payerId} onChange={(event) => setPayerId(event.target.value)} className="mt-2 w-full rounded-xl border border-white/10 bg-[#0d1222] px-3 py-3 text-sm text-slate-200 outline-none focus:border-indigo-300/40">
                  <option value="">Select a payer</option>
                  {participants.map((person) => <option key={person.id} value={person.id}>{person.display_name}</option>)}
                  {receipt.paid_by && !participants.some((person) => person.id === receipt.paid_by) && <option value={receipt.paid_by}>Original payer</option>}
                </select>
                <button type="button" onClick={finalize} disabled={!allItemsClaimed || !payerId || finalizing || !guest} className="btn-primary mt-3 w-full justify-center disabled:opacity-50">
                  {finalizing ? <LoaderCircle size={16} className="animate-spin" /> : <Check size={16} />}
                  Finalize split
                </button>
                {error && <p role="alert" className="mt-3 text-xs text-rose-300">{error}</p>}
                {!allItemsClaimed && <p className="mt-2 text-xs text-slate-600">Every receipt item needs at least one claimant.</p>}
              </section>
            )}

            {!isOpen && (
              <section className="rounded-2xl border border-white/[0.08] bg-white/[0.025] p-5">
                <div className="flex items-center gap-2 text-sm font-medium"><LockKeyhole size={16} className="text-teal-200" /> Room is read-only</div>
                <p className="mt-2 text-sm leading-relaxed text-slate-500">This receipt is {receipt.status.toLowerCase().replaceAll("_", " ")}. Claims can no longer be changed.</p>
              </section>
            )}

            {finalizeResult && (
              <section className="rounded-2xl border border-teal-300/20 bg-teal-300/[0.06] p-5">
                <h2 className="font-semibold text-teal-100">Split finalized</h2>
                <p className="mt-1 text-sm text-slate-400">{finalizeResult.settlements.length} ledger payment{finalizeResult.settlements.length === 1 ? "" : "s"} recorded.</p>
                <Link href={`/groups/${receipt.group_id}`} className="mt-3 inline-flex items-center gap-1 text-sm text-teal-200 hover:text-white">View group balances →</Link>
              </section>
            )}
          </aside>
        </div>
      </div>
    </main>
  );
}
