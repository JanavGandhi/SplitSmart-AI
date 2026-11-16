"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { Check, Copy, ExternalLink, LoaderCircle, X } from "lucide-react";
import { api } from "@/lib/api";
import type { Settlement, UPIPayment } from "@/lib/types";
import { paiseToCurrency } from "@/lib/currency";

export default function UPISettleModal({
  groupId,
  groupName,
  settlement,
  onClose,
  onSettled,
}: {
  groupId: string;
  groupName: string;
  settlement: Settlement | null;
  onClose: () => void;
  onSettled: () => void;
}) {
  const [payment, setPayment] = useState<UPIPayment | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [copied, setCopied] = useState(false);
  const [settled, setSettled] = useState(false);

  useEffect(() => {
    if (!settlement) return;
    const controller = new AbortController();
    setPayment(null);
    setError(null);
    setLoading(true);
    api.ledger
      .upiPayment(
        {
          group_id: groupId,
          creditor_user_id: settlement.to_user_id,
          amount_paise: settlement.amount_paise,
        },
        controller.signal,
      )
      .then(setPayment)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : "Could not create UPI payment");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [groupId, settlement]);

  if (!settlement) return null;

  async function copyLink() {
    if (!payment) return;
    try {
      await navigator.clipboard.writeText(payment.uri);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setError("Clipboard access was denied. You can still open the UPI app directly.");
    }
  }

  async function markSettled() {
    const selected = settlement;
    if (!selected) return;
    setSaving(true);
    setError(null);
    try {
      await api.ledger.settle({
        group_id: groupId,
        from_user_id: selected.from_user_id,
        to_user_id: selected.to_user_id,
        amount_paise: selected.amount_paise,
        idempotency_key: crypto.randomUUID(),
      });
      setSettled(true);
      onSettled();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not record settlement");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 p-0 backdrop-blur-sm sm:items-center sm:p-5"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="settle-title"
        className="w-full max-w-md rounded-t-3xl border border-white/10 bg-[#0d1222] p-6 shadow-2xl sm:rounded-3xl"
      >
        <div className="flex items-start justify-between">
          <div>
            <p className="section-label">UPI settlement</p>
            <h2 id="settle-title" className="mt-1 text-xl font-semibold">Complete payment</h2>
          </div>
          <button type="button" onClick={onClose} aria-label="Close dialog" className="rounded-lg p-2 text-slate-400 hover:bg-white/10 hover:text-white">
            <X size={18} />
          </button>
        </div>

        <div className="mt-5 rounded-2xl border border-white/[0.08] bg-white/[0.025] p-4">
          <p className="text-sm text-slate-400">{settlement.from_display_name} pays {settlement.to_display_name}</p>
          <p className="mt-1 text-3xl font-semibold tracking-tight">{paiseToCurrency(settlement.amount_paise)}</p>
          <p className="mt-1 text-xs text-slate-500">{groupName}</p>
        </div>

        <div className="my-5 flex min-h-48 items-center justify-center rounded-2xl bg-white p-4">
          {loading && <LoaderCircle className="animate-spin text-slate-500" />}
          {!loading && payment && (
            <Image
              src={`data:image/svg+xml;base64,${payment.qr_base64}`}
              alt={`UPI payment QR for ${payment.payee_name}`}
              width={176}
              height={176}
              unoptimized
              className="h-44 w-44"
            />
          )}
          {!loading && !payment && (
            <p className="max-w-56 text-center text-sm text-slate-500">
              QR code isn&apos;t available for this member yet.
            </p>
          )}
        </div>

        {error && <p role="alert" className="mb-4 rounded-xl border border-rose-400/20 bg-rose-400/10 p-3 text-sm text-rose-200">{error}</p>}
        {settled ? (
          <div className="flex items-center justify-center gap-2 rounded-xl bg-teal-400/10 p-4 text-sm font-medium text-teal-200">
            <Check size={17} /> Settlement recorded
          </div>
        ) : (
          <div className="grid gap-3">
            {payment && (
              <a href={payment.uri} className="btn-primary w-full justify-center">
                Open UPI app <ExternalLink size={16} />
              </a>
            )}
            {payment && (
              <button type="button" onClick={copyLink} className="btn-secondary w-full justify-center">
                {copied ? <Check size={16} /> : <Copy size={16} />}
                {copied ? "Copied" : "Copy payment link"}
              </button>
            )}
            <button type="button" onClick={markSettled} disabled={saving} className="btn-accent w-full justify-center disabled:opacity-60">
              {saving ? <LoaderCircle size={16} className="animate-spin" /> : <Check size={16} />}
              I&apos;ve paid — record settlement
            </button>
          </div>
        )}
        <p className="mt-4 text-center text-[11px] leading-relaxed text-slate-600">
          Recording a settlement updates the group ledger; it does not verify a bank transfer.
        </p>
      </section>
    </div>
  );
}
