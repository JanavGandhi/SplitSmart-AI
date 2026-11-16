"use client";

import { Check, Users } from "lucide-react";
import type { LineItem } from "@/lib/types";
import { paiseToCurrency } from "@/lib/currency";
import AvatarPill from "@/components/AvatarPill";

export default function ReceiptCard({
  item,
  currentUserId,
  disabled = false,
  onToggle,
}: {
  item: LineItem;
  currentUserId: string | null;
  disabled?: boolean;
  onToggle: (itemId: string) => void;
}) {
  const isClaimed = item.claims.some((claim) => claim.user.id === currentUserId);
  const quantityLabel = item.quantity > 1 ? ` · ${item.quantity} items` : "";

  return (
    <button
      type="button"
      disabled={disabled}
      onClick={() => onToggle(item.id)}
      aria-pressed={isClaimed}
      className={`w-full rounded-2xl border p-4 text-left transition ${
        isClaimed
          ? "border-indigo-400/40 bg-indigo-400/[0.09]"
          : "border-white/[0.08] bg-white/[0.025] hover:border-white/20 hover:bg-white/[0.045]"
      } disabled:cursor-not-allowed disabled:opacity-60`}
    >
      <span className="flex items-start justify-between gap-4">
        <span className="min-w-0">
          <span className="block truncate font-medium text-slate-100">{item.item_name}</span>
          <span className="mt-1 block text-xs text-slate-500">
            {item.category ?? "Receipt item"}{quantityLabel}
          </span>
        </span>
        <span className="flex shrink-0 items-center gap-3">
          <span className="font-mono text-sm text-slate-200">
            {paiseToCurrency(item.total_price_paise)}
          </span>
          <span
            className={`flex h-7 w-7 items-center justify-center rounded-lg border ${
              isClaimed
                ? "border-indigo-300 bg-indigo-400 text-white"
                : "border-white/15 text-transparent"
            }`}
          >
            <Check size={15} />
          </span>
        </span>
      </span>
      {item.claims.length > 0 && (
        <span className="mt-3 flex flex-wrap items-center gap-1.5 border-t border-white/[0.06] pt-3">
          <Users size={13} className="mr-1 text-slate-500" />
          {item.claims.map((claim) => (
            <AvatarPill key={claim.id} person={claim.user} compact />
          ))}
        </span>
      )}
    </button>
  );
}
