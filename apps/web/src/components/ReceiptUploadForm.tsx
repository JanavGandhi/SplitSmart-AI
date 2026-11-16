"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { FileImage, LoaderCircle, Upload } from "lucide-react";
import { api } from "@/lib/api";
import { useReceiptSSE } from "@/hooks/useReceiptSSE";

export default function ReceiptUploadForm({
  groupId,
}: {
  groupId: string | null;
}) {
  const [sseUrl, setSseUrl] = useState<string | null>(null);
  const [roomCode, setRoomCode] = useState<string | null>(null);
  const [fileName, setFileName] = useState("");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { state: streamState, events } = useReceiptSSE(sseUrl);
  const latest = events[events.length - 1];

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const file = form.elements.namedItem("receipt-image");
    if (!(file instanceof HTMLInputElement) || !file.files?.[0] || !groupId) return;

    setError(null);
    setUploading(true);
    setSseUrl(null);
    setRoomCode(null);
    try {
      const body = new FormData();
      body.append("file", file.files[0]);
      body.append("group_id", groupId);
      const result = await api.receipts.upload(body);
      setSseUrl(result.sse_url);
      setRoomCode(result.room_code);
      setFileName(file.files[0].name);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Receipt upload failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <section className="glass-card p-5 sm:p-6">
      <div className="flex items-start gap-3">
        <span className="rounded-xl bg-teal-400/10 p-2.5 text-teal-200"><FileImage size={18} /></span>
        <div>
          <h2 className="font-semibold">Scan a receipt</h2>
          <p className="mt-1 text-sm text-slate-500">Upload a receipt photo and follow the OCR progress live.</p>
        </div>
      </div>
      {!groupId ? (
        <p className="mt-5 rounded-xl border border-amber-300/15 bg-amber-300/[0.05] p-3 text-sm text-amber-100/80">
          Create or choose a group before uploading a receipt.
        </p>
      ) : (
        <form onSubmit={submit} className="mt-5 space-y-3">
          <label htmlFor="receipt-image" className="flex cursor-pointer items-center justify-between gap-4 rounded-xl border border-dashed border-white/15 bg-white/[0.02] px-4 py-4 transition hover:border-teal-300/30">
            <span className="flex min-w-0 items-center gap-3">
              <Upload size={17} className="shrink-0 text-slate-400" />
              <span className="truncate text-sm text-slate-300">{fileName || "Choose a JPG, PNG, or WebP image"}</span>
            </span>
            <span className="shrink-0 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-400">Browse</span>
          </label>
          <input
            id="receipt-image"
            name="receipt-image"
            type="file"
            accept="image/jpeg,image/png,image/webp,image/gif,image/heic,image/heif"
            required
            className="sr-only"
            onChange={(event) => setFileName(event.target.files?.[0]?.name ?? "")}
          />
          <button type="submit" disabled={uploading} className="btn-primary w-full justify-center disabled:opacity-60">
            {uploading ? <LoaderCircle size={16} className="animate-spin" /> : <Upload size={16} />}
            {uploading ? "Uploading…" : "Upload & scan"}
          </button>
        </form>
      )}
      {error && <p role="alert" className="mt-3 text-sm text-rose-300">{error}</p>}
      {sseUrl && (
        <div className="mt-5 rounded-xl border border-white/[0.07] bg-white/[0.025] p-4">
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm font-medium">{latest?.message ?? "Waiting for receipt processing…"}</p>
            <span className={`shrink-0 text-[11px] ${streamState === "error" ? "text-rose-300" : "text-teal-200"}`}>
              {streamState}
            </span>
          </div>
          {typeof latest?.progress === "number" && (
            <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white/10">
              <div className="h-full rounded-full bg-gradient-to-r from-indigo-400 to-teal-300 transition-all" style={{ width: `${latest.progress}%` }} />
            </div>
          )}
          {roomCode && (
            <Link href={`/room/${encodeURIComponent(roomCode)}`} className="mt-3 inline-flex text-sm text-indigo-200 hover:text-white">
              Open room {roomCode} →
            </Link>
          )}
        </div>
      )}
    </section>
  );
}
