import { ChevronRight } from "lucide-react";
import { Panel } from "./Panel";
import { SeverityBadge, severityAccent } from "./SeverityBadge";
import type { Flag } from "@/lib/types";

/* The priority queue is the product: it answers "what do I check first?".
   Rows are buttons rather than divs so the whole list is keyboard-navigable.

   TODO: navigate to /missions/[id]?action=[id] once the detail page exists. */

/* A flag carries every rule that fired — often eight or nine — because the
   score has to be reconstructible from them. A row can't show eight bullets
   and still be scannable, so it shows the heaviest few and says how many it
   is holding back. The count matters: without it the visible bullets look
   like they should add up to the score, and they don't. */
const REASONS_SHOWN = 4;

function QueueRow({ flag }: { flag: Flag }) {
  const shown = flag.reasons.slice(0, REASONS_SHOWN);
  const hidden = flag.reasons.length - shown.length;

  return (
    <button
      type="button"
      className="group relative w-full cursor-pointer border-b border-line px-4 py-3 pl-5 text-left transition-colors last:border-0 hover:bg-surface-2"
    >
      {/* A severity-coloured spine, so the shape of the backlog is legible
          from across the room before any text is read. */}
      <span
        aria-hidden="true"
        className={`absolute inset-y-0 left-0 w-0.5 ${severityAccent(flag.severity)}`}
      />

      <div className="flex items-baseline gap-3">
        <SeverityBadge severity={flag.severity} />
        <span className="nums font-mono text-xs text-muted">
          score {flag.score}
        </span>
        <ChevronRight
          size={16}
          aria-hidden="true"
          className="ml-auto shrink-0 self-center text-faint transition-colors group-hover:text-ink"
        />
      </div>

      <p className="mt-1.5 leading-snug font-medium text-ink">{flag.title}</p>
      <p className="mt-0.5 text-sm text-muted">
        {flag.assetName} · {flag.locationName}
      </p>

      <ul className="mt-2 space-y-1">
        {shown.map((reason) => (
          <li
            key={reason.rule}
            className="flex gap-2 text-sm leading-snug text-muted before:text-faint before:content-['•']"
          >
            {reason.detail}
          </li>
        ))}
        {hidden > 0 && (
          <li className="pl-4 text-xs text-faint">
            +{hidden} more signal{hidden > 1 ? "s" : ""}
          </li>
        )}
      </ul>
    </button>
  );
}

export function PriorityQueue({
  flags,
  delay,
}: {
  flags: Flag[];
  delay?: number;
}) {
  return (
    <Panel
      title="Needs attention"
      aside={`${flags.length} flagged`}
      bodyClassName=""
      className="h-full"
      delay={delay}
    >
      {flags.length === 0 ? (
        <p className="px-4 py-8 text-center text-sm text-muted">
          Nothing flagged. Every action in the last run completed cleanly.
        </p>
      ) : (
        /* Bounded, not h-full: the real queue is dozens of rows deep, and an
           unbounded list would set the height of the whole dashboard grid and
           drag the chart beside it down with it. The list scrolls inside the
           panel instead. */
        <div className="max-h-[min(70vh,44rem)] overflow-y-auto">
          {flags.map((flag) => (
            <QueueRow key={flag.id} flag={flag} />
          ))}
        </div>
      )}
    </Panel>
  );
}
