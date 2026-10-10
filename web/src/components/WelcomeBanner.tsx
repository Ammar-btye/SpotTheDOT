import { ArrowRight, Radar } from "lucide-react";
import { BannerControls } from "./BannerControls";
import { TypeIn } from "./TypeIn";

/* The shift-start banner. It exists to state the thesis in one sentence
   before any number is read — an operator (or a judge) who reads only this
   still knows what the console is claiming.

   The background is .hero-gradient in globals.css, next to the tokens it
   reads — see the note there for why it is not an inline style. By default
   the ramp cycles slowly through the four named presets; BannerControls can
   pin it to any one of them, and the theme-aware default takes over when
   motion is reduced. The scrim over them is load-bearing, not decoration: white
   text clears 4.5:1 on the blue and purple stops unaided but only reaches
   2.98:1 on the warm end, and which stop the text sits over depends on the
   viewport width. Its strength is per-preset, so the worst case stays above
   4.5:1 on every ramp rather than only on the one this was first tuned
   against.

   MOTION. The card arrives (12px rise), the headline types itself in, and the
   claim and the action float up behind it. Read order and arrival order are
   the same, which is the only reason a stagger is worth anything.

   The headline types; the paragraph does not. At 26ms a character the
   headline lands in under 700ms, but the paragraph is ~210 characters — five
   seconds of someone else typing while you wait to read it. Typing is for the
   line short enough to be a hook.

   The whole page is settled by ~1.3s. That ceiling is the real constraint: a
   console someone opens at the top of every shift cannot make them wait
   through an intro. Everything below is timed backwards from it.

   The mark deliberately has no motion of its own. Animating it would mean
   writing motion for a specific glyph, and that work would be thrown away
   with the placeholder. Dropping real art into the slot below gets the card's
   entrance for free, and whatever motion it deserves can be decided once it
   exists and has a shape worth moving. */
const HEADLINE = "What should I check first?";

/** The claim in the body copy is passed in, not written here: the numbers come
    from the kit, so the sentence stays true if the data changes under it. */
export function WelcomeBanner({
  hiddenFailures,
}: {
  hiddenFailures: { count: number; ofCompleted: number };
}) {
  return (
    <section
      aria-labelledby="banner-heading"
      className="hero-gradient anim-rise relative overflow-hidden rounded-panel px-6 py-6 sm:px-8 sm:py-7"
    >
      <BannerControls />

      {/* PLACEHOLDER ART — swap the child for the real logo; the wrapper holds
          the position and size so nothing else has to change. Decoration only:
          aria-hidden, and the banner reads fine without it. */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -right-10 -bottom-16 size-[220px]"
      >
        <Radar
          size={220}
          strokeWidth={1}
          className="absolute inset-0 text-white/20"
        />
      </div>

      <div className="relative max-w-2xl pt-8 sm:pt-0">
        {/* aria-label is load-bearing, not belt-and-braces: TypeIn's output is
            aria-hidden, so this is the heading's only accessible name. */}
        <h2
          id="banner-heading"
          aria-label={HEADLINE}
          className="text-2xl font-semibold tracking-tight text-white sm:text-3xl"
        >
          <TypeIn text={HEADLINE} startDelay={140} step={26} />
        </h2>
        <p className="anim-rise mt-2 text-sm leading-relaxed text-white/90 [--rise:6px] [animation-delay:760ms] sm:text-base">
          SPOTlight reads every inspection mission SPOT ran and ranks what an
          operator should look at next. {hiddenFailures.count} of the{" "}
          {hiddenFailures.ofCompleted} missions marked{" "}
          <span className="font-medium text-white">COMPLETED</span> hid at
          least one failed action, the status field alone won’t tell you that.
        </p>

        <a
          href="#queue"
          className="anim-rise group mt-5 inline-flex h-9 cursor-pointer items-center gap-2 rounded bg-accent px-4 text-sm font-semibold text-on-accent transition-colors [--rise:6px] [animation-delay:860ms] hover:bg-accent-hover"
        >
          Go to the priority queue
          {/* The arrow moves the way the click will: motion that means
              something, not decoration. */}
          <ArrowRight
            size={16}
            aria-hidden="true"
            className="transition-transform duration-(--dur-fast) ease-(--ease-settle) group-hover:translate-x-0.5"
          />
        </a>
      </div>
    </section>
  );
}
