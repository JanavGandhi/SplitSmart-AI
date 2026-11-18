"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { LoaderCircle, Plus, Users } from "lucide-react";
import { api } from "@/lib/api";
import { paiseToCurrency } from "@/lib/currency";
import type { ManualExpense, UserPublic } from "@/lib/types";

function parseAmountToPaise(value: string): number | null {
  const match = /^(\d+)(?:\.(\d{0,2}))?$/.exec(value.trim());
  if (!match) return null;

  const rupees = Number(match[1]);
  const paise = Number((match[2] ?? "").padEnd(2, "0"));
  const amount = rupees * 100 + paise;
  return Number.isSafeInteger(amount) && amount > 0 ? amount : null;
}

export default function ManualExpenseWorkspace({
  groupId,
  currency,
  members,
  expenses,
  onChanged,
}: {
  groupId: string;
  currency: string;
  members: UserPublic[];
  expenses: ManualExpense[];
  onChanged: () => Promise<void>;
}) {
  const initialized = useRef(false);
  const [displayName, setDisplayName] = useState("");
  const [upiId, setUpiId] = useState("");
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [payerId, setPayerId] = useState("");
  const [participantIds, setParticipantIds] = useState<string[]>([]);
  const [savingMember, setSavingMember] = useState(false);
  const [savingExpense, setSavingExpense] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (!initialized.current && members.length > 0) {
      setParticipantIds(members.map((member) => member.id));
      setPayerId(members[0].id);
      initialized.current = true;
    }
  }, [members]);

  async function addMember(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = displayName.trim();
    if (!name) return;

    setSavingMember(true);
    setError(null);
    setNotice(null);
    try {
      const membership = await api.groups.addMember(groupId, {
        display_name: name,
        ...(upiId.trim() ? { upi_id: upiId.trim() } : {}),
      });
      setParticipantIds((current) => [...current, membership.user.id]);
      setPayerId((current) => current || membership.user.id);
      setDisplayName("");
      setUpiId("");
      await onChanged();
      setNotice(`${name} added to the group.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not add this person");
    } finally {
      setSavingMember(false);
    }
  }

  async function addExpense(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const amountPaise = parseAmountToPaise(amount);
    if (!description.trim()) {
      setError("Enter a name for this expense.");
      return;
    }
    if (amountPaise === null) {
      setError("Enter an amount greater than zero with up to 2 decimal places.");
      return;
    }
    if (!payerId || participantIds.length === 0) {
      setError("Choose who paid and at least one person to split with.");
      return;
    }

    setSavingExpense(true);
    setError(null);
    setNotice(null);
    try {
      await api.groups.addExpense(groupId, {
        description: description.trim(),
        amount_paise: amountPaise,
        paid_by_user_id: payerId,
        participant_user_ids: participantIds,
      });
      setDescription("");
      setAmount("");
      await onChanged();
      setNotice("Expense added and group balances updated.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not add this expense");
    } finally {
      setSavingExpense(false);
    }
  }

  const memberNames = new Map(members.map((member) => [member.id, member.display_name]));

  return (
    <div className="mt-6 space-y-5">
      <div className="grid gap-5 lg:grid-cols-2">
        <section className="glass-card p-5 sm:p-6">
          <div className="mb-4 flex items-center gap-3">
            <Users size={18} className="text-indigo-300" />
            <div>
              <p className="section-label">Step 1</p>
              <h2 className="mt-1 text-lg font-semibold">Add people</h2>
            </div>
          </div>
          {members.length > 0 && (
            <div className="mb-4 flex flex-wrap gap-2">
              {members.map((member) => (
                <span
                  key={member.id}
                  className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5 text-sm text-slate-300"
                >
                  {member.display_name}
                </span>
              ))}
            </div>
          )}
          <form onSubmit={addMember} className="space-y-3">
            <label className="block text-xs text-slate-400" htmlFor="member-name">
              Person&apos;s name
              <input
                id="member-name"
                value={displayName}
                onChange={(event) => setDisplayName(event.target.value)}
                maxLength={100}
                required
                placeholder="e.g. Alex"
                className="mt-1.5 w-full rounded-xl border border-white/10 bg-white/[0.035] px-3 py-2.5 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-indigo-300/40"
              />
            </label>
            <label className="block text-xs text-slate-400" htmlFor="member-upi">
              UPI ID <span className="text-slate-600">(optional)</span>
              <input
                id="member-upi"
                value={upiId}
                onChange={(event) => setUpiId(event.target.value)}
                maxLength={100}
                placeholder="name@bank"
                className="mt-1.5 w-full rounded-xl border border-white/10 bg-white/[0.035] px-3 py-2.5 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-indigo-300/40"
              />
            </label>
            <button type="submit" disabled={!displayName.trim() || savingMember} className="btn-secondary w-full justify-center disabled:opacity-50">
              {savingMember ? <LoaderCircle size={15} className="animate-spin" /> : <Plus size={15} />}
              Add person
            </button>
          </form>
        </section>

        <section className="glass-card p-5 sm:p-6">
          <div className="mb-4 flex items-center gap-3">
            <span className="font-mono text-xs text-indigo-300">02</span>
            <div>
              <p className="section-label">Step 2</p>
              <h2 className="mt-1 text-lg font-semibold">Add an expense</h2>
            </div>
          </div>
          {members.length === 0 ? (
            <p className="rounded-xl border border-dashed border-white/10 p-4 text-sm text-slate-500">
              Add people first, then you can record and split an expense.
            </p>
          ) : (
            <form onSubmit={addExpense} className="space-y-3">
              <label className="block text-xs text-slate-400" htmlFor="expense-description">
                What was it for?
                <input
                  id="expense-description"
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  maxLength={200}
                  required
                  placeholder="e.g. Dinner"
                  className="mt-1.5 w-full rounded-xl border border-white/10 bg-white/[0.035] px-3 py-2.5 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-indigo-300/40"
                />
              </label>
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block text-xs text-slate-400" htmlFor="expense-amount">
                  Amount ({currency})
                  <input
                    id="expense-amount"
                    type="text"
                    inputMode="decimal"
                    value={amount}
                    onChange={(event) => setAmount(event.target.value)}
                    required
                    placeholder="0.00"
                    className="mt-1.5 w-full rounded-xl border border-white/10 bg-white/[0.035] px-3 py-2.5 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-indigo-300/40"
                  />
                </label>
                <label className="block text-xs text-slate-400" htmlFor="expense-payer">
                  Paid by
                  <select
                    id="expense-payer"
                    value={payerId}
                    onChange={(event) => setPayerId(event.target.value)}
                    required
                    className="mt-1.5 w-full rounded-xl border border-white/10 bg-[#0d1222] px-3 py-2.5 text-sm text-slate-200 outline-none focus:border-indigo-300/40"
                  >
                    {members.map((member) => (
                      <option key={member.id} value={member.id}>{member.display_name}</option>
                    ))}
                  </select>
                </label>
              </div>
              <fieldset>
                <legend className="mb-2 text-xs text-slate-400">Split equally between</legend>
                <div className="flex flex-wrap gap-2">
                  {members.map((member) => {
                    const checked = participantIds.includes(member.id);
                    return (
                      <label
                        key={member.id}
                        className={`cursor-pointer rounded-full border px-3 py-1.5 text-sm transition ${
                          checked
                            ? "border-indigo-300/40 bg-indigo-400/10 text-indigo-100"
                            : "border-white/10 text-slate-400 hover:border-white/20"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() =>
                            setParticipantIds((current) =>
                              checked
                                ? current.filter((id) => id !== member.id)
                                : [...current, member.id],
                            )
                          }
                          className="sr-only"
                        />
                        {member.display_name}
                      </label>
                    );
                  })}
                </div>
              </fieldset>
              <button
                type="submit"
                disabled={!description.trim() || !amount || participantIds.length === 0 || savingExpense}
                className="btn-primary w-full justify-center disabled:opacity-50"
              >
                {savingExpense ? <LoaderCircle size={15} className="animate-spin" /> : <Plus size={15} />}
                Add expense and update balances
              </button>
            </form>
          )}
        </section>
      </div>

      {(error || notice) && (
        <p
          role={error ? "alert" : "status"}
          className={`text-sm ${error ? "text-rose-300" : "text-teal-200"}`}
        >
          {error ?? notice}
        </p>
      )}

      <section className="glass-card p-5 sm:p-6">
        <div className="mb-4">
          <p className="section-label">Step 3</p>
          <h2 className="mt-1 text-lg font-semibold">Expenses</h2>
        </div>
        {expenses.length === 0 ? (
          <p className="text-sm text-slate-500">Your recorded expenses will appear here.</p>
        ) : (
          <div className="divide-y divide-white/[0.07]">
            {expenses.map((expense) => (
              <article key={expense.id} className="flex flex-col gap-2 py-4 first:pt-0 last:pb-0 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h3 className="font-medium text-slate-100">{expense.description}</h3>
                  <p className="mt-1 text-xs text-slate-500">
                    Paid by {memberNames.get(expense.paid_by_user_id) ?? "group member"} · split among {expense.participants.length}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {expense.participants.map((participant) => (
                      <span key={participant.user_id} className="text-xs text-slate-400">
                        {memberNames.get(participant.user_id) ?? "Member"}: {paiseToCurrency(participant.share_paise, currency)}
                      </span>
                    ))}
                  </div>
                </div>
                <span className="font-mono text-sm text-slate-200">{paiseToCurrency(expense.amount_paise, currency)}</span>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
