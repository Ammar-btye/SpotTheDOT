import { Fragment } from "react";

/* Renders text one character at a time on load.
 *
 * ACCESSIBILITY CONTRACT: the output is entirely aria-hidden, because a
 * screen reader walking 26 single-character spans announces them as 26
 * fragments. The caller MUST give the wrapping element an accessible name —
 * `aria-label={text}` on the heading — or the text does not exist for
 * assistive tech at all. Labelling the parent rather than shipping a
 * visually-hidden second copy keeps the string out of the DOM twice, so
 * selecting the heading doesn't copy it two times.
 *
 * No "use client": this is a Server Component. The animation is CSS, so the
 * effect costs nothing at runtime and starts on first paint instead of
 * waiting for hydration.
 */
export function TypeIn({
  text,
  startDelay = 0,
  step = 34,
}: {
  text: string;
  /** ms before the first character lands. */
  startDelay?: number;
  /** ms between characters. 34 reads as brisk typing, not a loading bar. */
  step?: number;
}) {
  const words = text.split(" ");

  // The space between words consumes a tick too, so the rhythm matches how
  // the line would actually be typed rather than speeding up at every gap.
  const groups: { word: string; start: number }[] = [];
  let cursor = 0;
  for (const word of words) {
    groups.push({ word, start: cursor });
    cursor += word.length + 1;
  }

  return (
    <span aria-hidden="true">
      {groups.map(({ word, start }, w) => (
        <Fragment key={w}>
          {w > 0 ? " " : null}
          {/* inline-block stops a word breaking between its own characters.
              The plain space between groups is the only break opportunity,
              which is exactly where a line should break. */}
          <span className="inline-block">
            {[...word].map((char, c) => (
              <span
                key={c}
                className="anim-type"
                style={{
                  animationDelay: `${startDelay + (start + c) * step}ms`,
                }}
              >
                {char}
              </span>
            ))}
          </span>
        </Fragment>
      ))}
      <span
        className="anim-caret"
        style={{ animationDelay: `${startDelay + cursor * step}ms` }}
      />
    </span>
  );
}
