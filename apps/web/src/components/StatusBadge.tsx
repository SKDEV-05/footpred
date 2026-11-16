import { Badge, type BadgeProps } from "@/components/ui/badge";

/**
 * The API stores provider status values lower-case (`timed`, `in_play`, ...).
 * This is the single display mapping for both the list and the detail view.
 */
const STATUS: Record<string, { label: string; variant: BadgeProps["variant"] }> = {
  scheduled: { label: "Scheduled", variant: "info" },
  timed: { label: "Scheduled", variant: "info" },
  in_play: { label: "Live", variant: "danger" },
  paused: { label: "Paused", variant: "warning" },
  finished: { label: "Finished", variant: "success" },
  postponed: { label: "Postponed", variant: "warning" },
  suspended: { label: "Suspended", variant: "warning" },
  cancelled: { label: "Cancelled", variant: "default" },
  awarded: { label: "Awarded", variant: "default" },
};

export function statusInfo(status: string) {
  return STATUS[status] ?? { label: status, variant: "default" as const };
}

export function StatusBadge({ status }: { status: string }) {
  const info = statusInfo(status);
  return <Badge variant={info.variant}>{info.label}</Badge>;
}
