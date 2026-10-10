import { AlertOctagon, CircleDot, Info, TriangleAlert } from "lucide-react";
import type { Severity } from "@/lib/types";

/* Status is never carried by colour alone: every badge is colour + icon +
   word. That is a WCAG requirement, and it's the thing Orbit gets wrong — its
   bare coloured dots are unreadable to a colourblind operator and ambiguous to
   everyone else.

   The colour tokens resolve per theme, so these stay AA on white and on
   near-black without the component knowing which it's on. */
const styles: Record<
  Severity,
  { icon: typeof AlertOctagon; text: string; border: string }
> = {
  CRITICAL: { icon: AlertOctagon, text: "text-bad", border: "bg-bad" },
  HIGH: { icon: TriangleAlert, text: "text-warn", border: "bg-warn" },
  MEDIUM: { icon: Info, text: "text-info", border: "bg-info" },
  LOW: { icon: CircleDot, text: "text-faint", border: "bg-faint" },
};

export function severityAccent(severity: Severity) {
  return styles[severity].border;
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  const { icon: Icon, text } = styles[severity];

  return (
    <span
      className={`inline-flex items-center gap-1.5 text-xs font-semibold tracking-wide ${text}`}
    >
      <Icon size={13} strokeWidth={2.5} aria-hidden="true" />
      {severity}
    </span>
  );
}
