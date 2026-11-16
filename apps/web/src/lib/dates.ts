export type TimeFilter = "today" | "tomorrow" | "7d" | "14d" | "30d";

export const TIME_FILTERS: { key: TimeFilter; label: string }[] = [
  { key: "today", label: "Today" },
  { key: "tomorrow", label: "Tomorrow" },
  { key: "7d", label: "Next 7 Days" },
  { key: "14d", label: "Next 14 Days" },
  { key: "30d", label: "Next 30 Days" },
];

const DAY_MS = 86_400_000;

function isoDate(date: Date): string {
  return date.toISOString().split("T")[0];
}

/**
 * The API compares these values as UTC calendar days. The end date is inclusive,
 * so a "7 day" window is today .. today + 6.
 */
export function dateRangeForFilter(filter: TimeFilter): {
  date_from: string;
  date_to: string;
} {
  const now = new Date();
  const today = new Date(
    Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()),
  );

  if (filter === "today") {
    return { date_from: isoDate(today), date_to: isoDate(today) };
  }
  if (filter === "tomorrow") {
    const tomorrow = new Date(today.getTime() + DAY_MS);
    return { date_from: isoDate(tomorrow), date_to: isoDate(tomorrow) };
  }

  const days = filter === "7d" ? 7 : filter === "14d" ? 14 : 30;
  const end = new Date(today.getTime() + (days - 1) * DAY_MS);
  return { date_from: isoDate(today), date_to: isoDate(end) };
}

export function formatKickoff(iso: string) {
  const date = new Date(iso);
  return {
    date: date.toLocaleDateString("en-GB", {
      weekday: "short",
      day: "numeric",
      month: "short",
    }),
    time: date.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" }),
  };
}
