import { Panel } from "./Panel";
import type { Stat } from "@/lib/types";

/* Grafana's stat panel: the title lives in the panel header, and the body is
   almost entirely the number. Mono digits because a row of these is read as a
   column of figures, and proportional digits make that ragged. */
export function StatTile({
  label,
  value,
  unit,
  note,
  delay,
}: Stat & { delay?: number }) {
  return (
    <Panel title={label} bodyClassName="px-4 py-3" delay={delay}>
      <p className="nums font-mono text-3xl leading-none font-semibold text-ink">
        {value}
        {unit ? (
          <span className="ml-1 text-lg font-normal text-muted">{unit}</span>
        ) : null}
      </p>
      <p className="mt-2 text-xs leading-snug text-muted">{note}</p>
    </Panel>
  );
}
