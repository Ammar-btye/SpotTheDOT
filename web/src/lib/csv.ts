// A small RFC 4180 CSV reader.
//
// The kit CSVs are a few hundred rows each and ship with the repo, so a parser
// dependency would be all cost and no benefit. This handles the parts of the
// spec that actually bite: quoted fields, embedded commas and newlines, and
// "" as an escaped quote — because a free-text `description` column is exactly
// where a naive `split(",")` starts silently shifting every later field.

/** Splits CSV text into rows of raw string cells. */
function parseRows(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let cell = "";
  let quoted = false;

  // Strip a UTF-8 BOM: it would otherwise become part of the first header name.
  const src = text.charCodeAt(0) === 0xfeff ? text.slice(1) : text;

  for (let i = 0; i < src.length; i++) {
    const char = src[i];

    if (quoted) {
      if (char !== '"') {
        cell += char;
      } else if (src[i + 1] === '"') {
        cell += '"'; // "" inside a quoted field is one literal quote.
        i++;
      } else {
        quoted = false;
      }
      continue;
    }

    if (char === '"') {
      quoted = true;
    } else if (char === ",") {
      row.push(cell);
      cell = "";
    } else if (char === "\n" || char === "\r") {
      // Close the row on CR, LF or CRLF, but never on the LF of a CRLF pair.
      if (char === "\r" && src[i + 1] === "\n") i++;
      row.push(cell);
      rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += char;
    }
  }

  // A file with no trailing newline still has one row left in hand.
  if (cell !== "" || row.length > 0) {
    row.push(cell);
    rows.push(row);
  }

  return rows;
}

/**
 * Parses CSV text into one object per data row, keyed by the header row.
 *
 * Every value stays a string: coercion belongs with the schema that knows what
 * each column means, not here. Blank lines are dropped so a trailing newline
 * doesn't become a row of empty strings.
 */
export function parseCsv(text: string): Record<string, string>[] {
  const rows = parseRows(text).filter(
    (row) => !(row.length === 1 && row[0].trim() === ""),
  );
  if (rows.length === 0) return [];

  const header = rows[0].map((name) => name.trim());

  return rows.slice(1).map((row) => {
    const record: Record<string, string> = {};
    header.forEach((name, i) => {
      record[name] = (row[i] ?? "").trim();
    });
    return record;
  });
}
