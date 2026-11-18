"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, LoaderCircle, ReceiptText, RefreshCw } from "lucide-react";
import AvatarPill from "@/components/AvatarPill";
import CopilotDrawer from "@/components/CopilotDrawer";
import DebtGraph from "@/components/DebtGraph";
import ManualExpenseWorkspace from "@/components/ManualExpenseWorkspace";
import ReceiptUploadForm from "@/components/ReceiptUploadForm";
import SiteHeader from "@/components/SiteHeader";
import UPISettleModal from "@/components/UPISettleModal";
import { api } from "@/lib/api";
import type {
  GroupBalance,
  GroupDetail,
  GroupBalancesResponse,
  ManualExpense,
  Receipt,
  Settlement,
  SimplifiedDebtResult,
} from "@/lib/types";
import { paiseToCurrency } from "@/lib/currency";

export default function GroupView({ groupId }: { groupId: string }) {
  const [group, setGroup] = useState<GroupDetail | null>(null);
  const [balances, setBalances] = useState<GroupBalancesResponse | null>(null);
  const [debts, setDebts] = useState<SimplifiedDebtResult | null>(null);
  const [receipts, setReceipts] = useState<Receipt[]>([]);
  const [expenses, setExpenses] = useState<ManualExpense[]>([]);
  const [selectedSettlement, setSelectedSettlement] = useState<Settlement | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (background = false) => {
    if (background) setRefreshing(true);
    else setLoading(true);
    try {
      const [groupData, balanceData, debtData, receiptData, expenseData] = await Promise.all([
        api.groups.get(groupId),
        api.groups.balances(groupId),
        api.groups.simplified(groupId),
        api.receipts.forGroup(groupId),
        api.groups.expenses(groupId),
      ]);
      setGroup(groupData);
      setBalances(balanceData);
      setDebts(debtData);
      setReceipts(receiptData);
      setExpenses(expenseData);
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Group data could not be loaded");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [groupId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  if (loading) {
    return (
      <main className="min-h-screen">
        <SiteHeader backHref="/dashboard" />
        <div className="mx-auto flex max-w-7xl items-center gap-3 px-5 py-20 text-sm text-slate-400 sm:px-8">
          <LoaderCircle size={17} className="animate-spin" /> Loading group…
        </div>
      </main>
    );
  }

  if (error || !group || !balances || !debts) {
    return (
      <main className="min-h-screen">
        <SiteHeader backHref="/dashboard" />
        <div className="mx-auto max-w-3xl px-5 py-20 sm:px-8">
          <div role="alert" className="rounded-2xl border border-rose-400/20 bg-rose-400/[0.07] p-5 text-rose-200">
            {error ?? "Group not found"}
          </div>
          <Link href="/dashboard" className="mt-5 inline-flex text-sm text-indigo-200 hover:text-white">Return to dashboard →</Link>
        </div>
      </main>
    );
  }

  const balanceRows: GroupBalance[] = balances.balances;
  const totalOwed = balanceRows
    .filter((balance) => balance.net_balance_paise > 0)
    .reduce((sum, balance) => sum + balance.net_balance_paise, 0);

  return (
    <main className="min-h-screen">
      <SiteHeader backHref="/dashboard" />
      <div className="mx-auto max-w-7xl px-5 pb-24 pt-9 sm:px-8 sm:pt-12">
        <div className="mb-8 flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
          <div className="min-w-0">
            <p className="section-label">Group overview</p>
            <h1 className="mt-2 truncate text-3xl font-semibold tracking-tight sm:text-4xl">{group.name}<span className="text-indigo-300">.</span></h1>
            <p className="mt-2 text-sm text-slate-500">Invite code <span className="ml-1 rounded-md border border-white/10 bg-white/[0.035] px-2 py-1 font-mono text-slate-300">{group.invite_code}</span></p>
          </div>
          <button type="button" onClick={() => void refresh(true)} disabled={refreshing} className="btn-secondary self-start md:self-auto">
            <RefreshCw size={15} className={refreshing ? "animate-spin" : ""} /> Refresh balances
          </button>
        </div>

        <ManualExpenseWorkspace
          groupId={groupId}
          currency={group.currency}
          members={group.members.map((member) => member.user)}
          expenses={expenses}
          onChanged={() => refresh(true)}
        />

        <div className="grid gap-3 sm:grid-cols-3">
          {[
            ["Members", group.member_count.toString()],
            ["Open settlements", debts.simplified_transactions.toString()],
            ["Net outstanding", paiseToCurrency(totalOwed, group.currency)],
          ].map(([label, value]) => (
            <article key={label} className="glass-card p-5">
              <p className="text-xs text-slate-500">{label}</p>
              <p className="mt-2 text-2xl font-semibold tracking-tight">{value}</p>
            </article>
          ))}
        </div>

        <section className="glass-card mt-5 p-5 sm:p-6">
          <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="section-label">Debt simplifier</p>
              <h2 className="mt-1 text-lg font-semibold">Who settles with whom</h2>
            </div>
            <span className="text-xs text-slate-500">
              {debts.original_transactions} ledger entries → {debts.simplified_transactions} payments
            </span>
          </div>
          {debts.zero_sum_verified === false && (
            <p role="alert" className="mb-4 rounded-xl border border-rose-400/20 bg-rose-400/[0.06] p-3 text-sm text-rose-200">
              Group balances do not reconcile. Refresh or contact support before settling.
            </p>
          )}
          <DebtGraph balances={balanceRows} settlements={debts.settlements} />
          {debts.settlements.length > 0 && (
            <div className="mt-5 flex flex-wrap gap-2">
              {debts.settlements.map((settlement) => (
                <button key={`${settlement.from_user_id}-${settlement.to_user_id}`} type="button" onClick={() => setSelectedSettlement(settlement)} className="btn-primary px-4 py-2.5">
                  Settle {settlement.from_display_name} <ArrowRight size={14} /> {settlement.to_display_name}
                </button>
              ))}
            </div>
          )}
        </section>
        <ReceiptUploadForm groupId={groupId} />
        <section className="glass-card mt-5 p-5 sm:p-6">
          <div className="mb-5 flex items-center justify-between gap-3">
            <div>
              <p className="section-label">Receipts</p>
              <h2 className="mt-1 text-lg font-semibold">Scanned bills</h2>
            </div>
            <ReceiptText size={17} className="text-slate-500" />
          </div>
          {receipts.length === 0 ? (
            <p className="rounded-xl border border-dashed border-white/10 p-5 text-center text-sm text-slate-500">
              No uploaded receipts yet. You can still add and split expenses above.
            </p>
          ) : (
            <div className="grid gap-3 md:grid-cols-2">
              {receipts.map((receipt) => (
                <Link key={receipt.id} href={`/room/${encodeURIComponent(receipt.room_code)}`} className="rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4 transition hover:border-indigo-300/25">
                  <span className="flex items-start justify-between gap-4">
                    <span className="min-w-0">
                      <span className="block truncate font-medium">{receipt.merchant_name ?? "Receipt"}</span>
                      <span className="mt-1 block font-mono text-xs text-slate-500">{receipt.room_code} · {receipt.line_items.length} items</span>
                    </span>
                    <span className="shrink-0 text-right">
                      <span className="block font-mono text-sm">{paiseToCurrency(receipt.total_paise, group.currency)}</span>
                      <span className={`mt-1 inline-block text-[10px] ${receipt.status === "READY_FOR_CLAIMS" ? "text-teal-200" : "text-slate-500"}`}>{receipt.status.replaceAll("_", " ")}</span>
                    </span>
                  </span>
                  <span className="mt-3 flex flex-wrap gap-1.5">
                    {Array.from(new Map(receipt.line_items.flatMap((item) => item.claims.map((claim) => [claim.user.id, claim.user] as const))).values()).slice(0, 5).map((person) => (
                      <AvatarPill key={person.id} person={person} compact />
                    ))}
                    {receipt.line_items.every((item) => item.claims.length === 0) && (
                      <span className="text-xs text-slate-600">No item claims</span>
                    )}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </section>
      </div>
      <CopilotDrawer groupId={groupId} />
      <UPISettleModal
        groupId={groupId}
        groupName={group.name}
        settlement={selectedSettlement}
        onClose={() => setSelectedSettlement(null)}
        onSettled={() => void refresh(true)}
      />
    </main>
  );
}
