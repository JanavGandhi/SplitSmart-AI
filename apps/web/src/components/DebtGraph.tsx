"use client";

import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import type { GroupBalance, Settlement } from "@/lib/types";
import { paiseToCurrency } from "@/lib/currency";

const POSITIONS = [
  { x: 90, y: 62 },
  { x: 340, y: 62 },
  { x: 90, y: 204 },
  { x: 340, y: 204 },
  { x: 215, y: 132 },
  { x: 215, y: 250 },
];

export default function DebtGraph({
  balances,
  settlements,
}: {
  balances: GroupBalance[];
  settlements: Settlement[];
}) {
  const byId = new Map(balances.map((person) => [person.user_id, person]));
  const connectedIds = new Set(
    settlements.flatMap((settlement) => [
      settlement.from_user_id,
      settlement.to_user_id,
    ]),
  );
  const people = balances.filter((person) => connectedIds.has(person.user_id));
  const positions = new Map(
    people.map((person, index) => [person.user_id, POSITIONS[index % POSITIONS.length]]),
  );

  if (settlements.length === 0) {
    return (
      <div className="flex min-h-52 flex-col items-center justify-center rounded-2xl border border-dashed border-white/10 text-center">
        <div className="mb-2 rounded-xl bg-teal-400/10 p-3 text-teal-300">✓</div>
        <p className="font-medium">Everyone is settled</p>
        <p className="mt-1 text-sm text-slate-500">No payments are needed right now.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="overflow-x-auto rounded-2xl border border-white/[0.07] bg-[#090d1a]">
        <svg
          viewBox="0 0 430 290"
          role="img"
          aria-label="Diagram of simplified payments between group members"
          className="mx-auto min-w-[380px] max-w-full"
        >
          <defs>
            <marker
              id="debt-arrow"
              viewBox="0 0 10 10"
              refX="8"
              refY="5"
              markerWidth="5"
              markerHeight="5"
              orient="auto-start-reverse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#7585ff" />
            </marker>
          </defs>
          {settlements.map((settlement, index) => {
            const from = positions.get(settlement.from_user_id) ?? POSITIONS[0];
            const to = positions.get(settlement.to_user_id) ?? POSITIONS[1];
            const labelX = (from.x + to.x) / 2;
            const labelY = (from.y + to.y) / 2 - 8 - (index % 2) * 7;
            return (
              <g key={`${settlement.from_user_id}-${settlement.to_user_id}`}>
                <line
                  x1={from.x}
                  y1={from.y}
                  x2={to.x}
                  y2={to.y}
                  stroke="#7585ff"
                  strokeOpacity=".56"
                  strokeWidth="2"
                  markerEnd="url(#debt-arrow)"
                />
                <rect
                  x={labelX - 37}
                  y={labelY - 11}
                  width="74"
                  height="22"
                  rx="8"
                  fill="#11182a"
                  stroke="#263251"
                />
                <text
                  x={labelX}
                  y={labelY + 4}
                  textAnchor="middle"
                  fill="#dbe4ff"
                  fontSize="10"
                  fontFamily="monospace"
                >
                  {paiseToCurrency(settlement.amount_paise)}
                </text>
              </g>
            );
          })}
          {people.map((person) => {
            const point = positions.get(person.user_id) ?? POSITIONS[0];
            return (
              <g key={person.user_id}>
                <circle cx={point.x} cy={point.y} r="25" fill="#171f35" stroke={person.avatar_color} strokeWidth="2" />
                <text
                  x={point.x}
                  y={point.y + 4}
                  textAnchor="middle"
                  fill="#f1f5f9"
                  fontSize="11"
                  fontWeight="600"
                >
                  {person.display_name.slice(0, 10)}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
      <ul className="mt-4 grid gap-2 sm:grid-cols-2">
        {settlements.map((settlement) => (
          <li
            key={`row-${settlement.from_user_id}-${settlement.to_user_id}`}
            className="flex items-center justify-between gap-3 rounded-xl border border-white/[0.06] bg-white/[0.02] px-4 py-3"
          >
            <span className="flex min-w-0 items-center gap-2 text-sm">
              <span className="truncate text-slate-300">{settlement.from_display_name}</span>
              <ArrowUpRight size={14} className="shrink-0 text-indigo-300" />
              <span className="truncate text-slate-300">{settlement.to_display_name}</span>
              {byId.has(settlement.from_user_id) && (
                <ArrowDownRight size={12} className="hidden text-slate-600 sm:block" />
              )}
            </span>
            <span className="shrink-0 font-mono text-sm text-teal-200">
              {paiseToCurrency(settlement.amount_paise)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
