"use client";

import { useEffect, useRef, useState } from "react";
import { Check, ChevronDown, RotateCcw } from "lucide-react";

/* The classes that carry a load animation. Listed explicitly rather than
   matched on a prefix so a future `.animate-*` utility can't get swept up. */
const ANIMATED = ".anim-rise, .anim-float, .anim-type, .anim-caret";

/**
 * Restart every load animation on the page.
 *
 * Removing and re-adding the class is the restart that survives this
 * codebase's details: the stagger lives in inline `animation-delay` (set per
 * character by TypeIn and per panel by Panel), and anything that touches the
 * `animation` shorthand — the other common restart trick — would wipe those
 * delays and collapse the cascade into one flat pop.
 *
 * Classes come off every element first, then one forced reflow commits the
 * removal, then they go back on. Batching that way costs one layout instead
 * of one per element, and no paint happens in between, so there is no flash
 * of the un-animated state.
 */
function replayAnimations() {
  const els = Array.from(document.querySelectorAll<HTMLElement>(ANIMATED));
  const classes = els.map((el) =>
    Array.from(el.classList).filter((c) => c.startsWith("anim-")),
  );

  els.forEach((el, i) => el.classList.remove(...classes[i]));
  void document.documentElement.offsetWidth; // one reflow for the whole page
  els.forEach((el, i) => el.classList.add(...classes[i]));
}

/* "auto" is the absence of [data-hero]: the banner keeps the theme-aware
   default and shifts with light/dark. The named ramps are fixed moods and
   look the same in either theme. */
const HEROES = ["auto", "dawn", "noon", "dusk", "midnight"] as const;
type Hero = (typeof HEROES)[number];

const LABEL: Record<Hero, string> = {
  auto: "Auto",
  dawn: "Dawn",
  noon: "Noon",
  dusk: "Dusk",
  midnight: "Midnight",
};

/* The menu rows get a word about the ramp rather than a swatch each. A swatch
   would have to read --c-hero-*, and those resolve to whichever preset is
   *currently* applied — so five swatches would all paint the same gradient.
   Picking repaints the banner instantly anyway, which is a far better preview
   than a 12px chip could be. */
const HINT: Record<Hero, string> = {
  auto: "Follows light and dark",
  dawn: "Violet into amber",
  noon: "Bright blue into gold",
  dusk: "The dark-mode default",
  midnight: "Near-monochrome navy",
};

/* Transparent fill, visible edge. There is no fill at all now: these sit on
   artwork, and a ghost control should let it through, so the border carries
   the whole job of making them read as buttons.

   That is also why the border alpha is not up for negotiation. white/60 is
   the solved minimum for a 3:1 boundary, and the binding case is the
   *lightest* ramp rather than the darkest: over noon's warm end (#d9a520
   under its 0.42 scrim) it measures 3.24:1, with almost nothing spare.
   Softening it to white/40 drops the control to roughly 2.2:1 and leaves it
   identified by its label alone. The fill was the part that could go. */
const CHIP =
  "inline-flex h-7 cursor-pointer items-center gap-1.5 rounded border border-white/60 text-white transition-colors hover:bg-black/25 focus-visible:bg-black/25";

export function BannerControls() {
  const [hero, setHero] = useState<Hero>("auto");
  const [open, setOpen] = useState(false);

  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const optionRefs = useRef<(HTMLButtonElement | null)[]>([]);

  function choose(next: Hero) {
    setHero(next);
    // The ramp is a document-level concern — the tokens live on :root — so it
    // is set imperatively rather than threaded through a provider for one
    // attribute. Absence of the attribute *is* the "auto" state.
    const root = document.documentElement;
    if (next === "auto") root.removeAttribute("data-hero");
    else root.setAttribute("data-hero", next);

    setOpen(false);
    triggerRef.current?.focus();
  }

  // Pressing anywhere else closes. pointerdown rather than click, so the menu
  // is gone before the outside element reacts to its own press.
  useEffect(() => {
    if (!open) return;
    function onPointerDown(event: PointerEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  // Opening moves focus onto the current choice, which is where a keyboard
  // user and a screen reader both expect to land in a listbox. Selecting also
  // closes, so this never fights the focus return in `choose`.
  useEffect(() => {
    if (open) optionRefs.current[HEROES.indexOf(hero)]?.focus();
  }, [open, hero]);

  /** Roving focus inside the menu: the arrow keys move, they don't select. */
  function onMenuKeyDown(event: React.KeyboardEvent) {
    const delta =
      event.key === "ArrowDown" ? 1 : event.key === "ArrowUp" ? -1 : 0;

    if (delta !== 0) {
      event.preventDefault();
      const from = optionRefs.current.findIndex(
        (el) => el === document.activeElement,
      );
      optionRefs.current[(from + delta + HEROES.length) % HEROES.length]?.focus();
      return;
    }

    if (event.key === "Escape") {
      event.preventDefault();
      setOpen(false);
      triggerRef.current?.focus();
    }
  }

  return (
    <div
      ref={rootRef}
      className="absolute top-3 right-3 flex items-center gap-1.5"
    >
      <div className="relative">
        <button
          ref={triggerRef}
          type="button"
          onClick={() => setOpen((isOpen) => !isOpen)}
          onKeyDown={(event) => {
            if (event.key === "ArrowDown") {
              event.preventDefault();
              setOpen(true);
            }
          }}
          aria-haspopup="listbox"
          aria-expanded={open}
          aria-controls="hero-listbox"
          // The visible name is inside the accessible name, so the two agree
          // for anyone driving this by voice.
          aria-label={`Banner gradient: ${LABEL[hero]}`}
          className={`${CHIP} px-2`}
        >
          {/* The swatch reads the same custom properties the banner does, so it
              always shows the live ramp with nothing to keep in sync. */}
          <span
            aria-hidden="true"
            className="hero-swatch size-3 shrink-0 rounded-full border border-white/25"
          />
          <span className="text-[11px] font-medium">{LABEL[hero]}</span>
          <ChevronDown
            size={12}
            aria-hidden="true"
            className={`transition-transform duration-(--dur-fast) ${open ? "rotate-180" : ""}`}
          />
        </button>

        {open && (
          <ul
            id="hero-listbox"
            role="listbox"
            aria-label="Banner gradient"
            onKeyDown={onMenuKeyDown}
            /* The trigger is a ghost because it sits on artwork. A menu is a
               surface you read, so it gets the console's real panel tokens —
               opaque background, standard border and shadow — rather than
               more glass. */
            className="panel-shadow absolute top-full right-0 z-20 mt-1.5 w-44 overflow-hidden rounded border border-line bg-surface py-1"
          >
            {HEROES.map((option, i) => {
              const selected = option === hero;
              return (
                <li key={option} role="none">
                  <button
                    ref={(el) => {
                      optionRefs.current[i] = el;
                    }}
                    type="button"
                    role="option"
                    aria-selected={selected}
                    // Focus is managed by the listbox, so the options stay out
                    // of the page's tab order: Tab leaves the menu, it does
                    // not walk through five more stops inside it.
                    tabIndex={-1}
                    onClick={() => choose(option)}
                    className="flex w-full cursor-pointer items-center gap-2 px-2 py-1.5 text-left transition-colors hover:bg-surface-2 focus-visible:bg-surface-2"
                  >
                    {/* The check holds its slot whether or not it shows, so
                        the labels don't shift sideways as the choice moves. */}
                    <Check
                      size={13}
                      aria-hidden="true"
                      // accent-ink, not accent: this amber is on the panel
                      // surface, which is what that token is solved for.
                      className={`shrink-0 text-accent-ink ${selected ? "" : "invisible"}`}
                    />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-xs font-medium text-ink">
                        {LABEL[option]}
                      </span>
                      <span className="block truncate text-[11px] text-muted">
                        {HINT[option]}
                      </span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <button
        type="button"
        onClick={replayAnimations}
        aria-label="Replay the intro animation"
        title="Replay animation"
        className={`${CHIP} w-7 justify-center`}
      >
        <RotateCcw size={13} aria-hidden="true" />
      </button>
    </div>
  );
}
