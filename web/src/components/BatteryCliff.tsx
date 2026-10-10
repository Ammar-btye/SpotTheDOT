import { Panel } from "./Panel";
import type { BatteryBand } from "@/lib/types";

/* Battery bands, drawn with plain CSS rather than a chart library — at this size a
   library costs a client bundle and a hydration boundary for no benefit.
   Recharts is installed if a later chart needs tooltips or axes.

   Every value is printed under its bar, so the chart is readable without
   relying on bar height or colour alone. */
export function BatteryCliff({
  bands,
  caption,
  delay,
}: {
  bands: BatteryBand[];
  /** The takeaway sentence, generated from the same numbers as the bars. */
  caption: string;
  delay?: number;
}) {
  return (
    <Panel
      title="Action success by battery level"
      className="h-full"
      delay={delay}
    >
      <div className="flex flex-1 items-end gap-3" style={{ minHeight: 160 }}>
        {bands.length === 0 && <p className="text-sm text-muted">No action reliability data yet.</p>}
        {bands.map((b) => {
          // The lowest band is the story: call it out in red.
          const isCliff = b.band === "≤25";
          return (
            <div key={b.band} className="flex flex-1 flex-col items-center gap-2">
              <span className="nums font-mono text-sm font-semibold text-ink">
                {b.successRate}%
              </span>
              <div
                className={`w-full rounded-sm ${isCliff ? "bg-bad" : "bg-ok"}`}
                style={{ height: `${Math.max(b.successRate, 2)}%` }}
                role="img"
                aria-label={`${b.band} battery: ${b.successRate}% success across ${b.sampleSize} actions`}
              />
            </div>
          );
        })}
      </div>

      <div className="mt-2 flex gap-3 border-t border-line pt-2">
        {bands.map((b) => (
          <div key={b.band} className="flex-1 text-center">
            <p className="nums font-mono text-xs font-medium text-ink">{b.band}</p>
            <p className="nums font-mono text-[11px] text-muted">n={b.sampleSize}</p>
          </div>
        ))}
      </div>

      <p className="mt-3 text-xs leading-snug text-muted">{caption}</p>
    </Panel>
  );
}
