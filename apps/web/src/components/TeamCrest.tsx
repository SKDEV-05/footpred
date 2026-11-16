import type { TeamRef } from "@/types";

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

/**
 * Provider crest when it exists, otherwise a plain initials placeholder. The
 * placeholder is not a logo and is never presented as one.
 */
export function TeamCrest({ team, size = 28 }: { team: TeamRef; size?: number }) {
  if (team.crest_url) {
    // Third-party asset: a plain <img> avoids proxying provider media through Next.
    // eslint-disable-next-line @next/next/no-img-element
    return (
      <img
        src={team.crest_url}
        alt=""
        width={size}
        height={size}
        loading="lazy"
        className="object-contain shrink-0"
        style={{ width: size, height: size }}
      />
    );
  }

  return (
    <span
      aria-hidden="true"
      className="inline-flex items-center justify-center rounded-full bg-white/10 text-[10px] font-semibold text-zinc-300 shrink-0"
      style={{ width: size, height: size }}
    >
      {initials(team.name)}
    </span>
  );
}
