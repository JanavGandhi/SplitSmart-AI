export interface AvatarPerson {
  id: string;
  display_name: string;
  avatar_color: string;
}

export default function AvatarPill({
  person,
  active = false,
  compact = false,
}: {
  person: AvatarPerson;
  active?: boolean;
  compact?: boolean;
}) {
  return (
    <span
      title={person.display_name}
      className={`inline-flex max-w-full items-center gap-2 rounded-full border border-white/10 bg-white/[0.035] ${
        compact ? "py-1 pl-1 pr-2 text-[11px]" : "py-1.5 pl-1.5 pr-3 text-xs"
      }`}
    >
      <span
        className="flex shrink-0 items-center justify-center rounded-full font-semibold text-slate-950"
        style={{
          width: compact ? 22 : 28,
          height: compact ? 22 : 28,
          backgroundColor: person.avatar_color,
        }}
      >
        {person.display_name.slice(0, 1).toUpperCase()}
      </span>
      <span className="truncate text-slate-300">{person.display_name}</span>
      {active && <span className="h-1.5 w-1.5 rounded-full bg-teal-300" />}
    </span>
  );
}
