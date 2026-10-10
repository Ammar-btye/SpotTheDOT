# Winners: How-to-Win Playbook (judging rubrics + winner post-mortems)
_Researched 2026-10-09 · sources: Knight Hacks IX/VIII Devpost overview pages, MLH Organizer Guide (judging plan), TreeHacks/Hack the North/HackGT Devpost pages, winner write-ups (personal blog, dev.to, Substack, university news), Devpost blog, judge-side dev.to posts_

## 1. Scope
**Visited (loaded):**
- https://knight-hacks-ix.devpost.com/ (overview; has the full judging criteria and submission rules) and https://knighthacksviii.devpost.com/ (fetched with curl; WebFetch returned 403)
- https://knight-hacks-ix.devpost.com/rules and https://knighthacksviii.devpost.com/rules: these contain only the code-of-conduct links
- https://2026.knighthacks.org/ (lists the tracks; no judging details)
- https://guide.mlh.com/general-information/judging-and-submissions/judging-plan.md
- https://treehacks-2025.devpost.com/, https://treehacks-2026.devpost.com/, https://hackthenorth2025.devpost.com/, https://hackgt-12.devpost.com/
- Winner write-ups: https://www.teach.cs.toronto.edu/ambassadors/blog/2023-hack-the-north/, https://cs.uic.edu/news-stories/nandana-sheri-takes-first-place-at-stanford-hackathon, https://dev.to/abdullahlko/we-won-best-use-of-snowflake-at-elementx-2026-mlh-hack-day-chj, https://getpushtoprod.substack.com/p/how-to-win-hackathons, https://sustained.substack.com/p/lessons-from-winning-five-hackathons, https://blog.dylanlu.com/cal-hacks-12/
- Judge and coach advice: https://dev.to/kurbaitaev/what-judges-actually-score-notes-from-a-year-of-hackathon-judging-3p4l, https://dev.to/jacklyn/how-to-make-your-devpost-submissions-not-suck-37i0, https://info.devpost.com/blog/6-tips-for-making-a-hackathon-demo-video, https://cua.ai/blog/hack-the-north
- Devpost project pages used to confirm wins: devpost.com/software/shiftytech, devpost.com/software/survivex

**Skipped:**
- **Already logged by other agents:** FaceTimeOS (Cal Hacks 12.0) and SOTA Computer-Use Agent (Hack the North 2025). I still cite Dylan Lu's FaceTimeOS post-mortem in Patterns.
- **Not winners or not usable:** the dev.to MLH x DigitalOcean "Justicia Clew" post (the author says they didn't place), the dev.to "funded through a hackathon win" post (no hackathon or project named), Illinois Tech SafeTrack (a Pebble-era win, outside 2022–2026), and spam or SEO mirror sites (*.it.com and others) that claim TreeHacks criteria weights. Those weights are not used.

## 2. Winners table
| Name | Hackathon | Prize/track | What it does | Stack | Repo | Source URL |
|---|---|---|---|---|---|---|
| ShiftyTech | Hack the North 2023 | Best Hack Built on Replit | Turns dance poses in front of a webcam into executable Python code | TensorFlow MoveNet (Lightning→Thunder), Python, Next.js/TypeScript, Replit, GCP VM | https://github.com/ShiftyTech/shiftyTech | Post-mortem by team member Sarah Walker: https://www.teach.cs.toronto.edu/ambassadors/blog/2023-hack-the-north/ · Devpost: https://devpost.com/software/shiftytech |
| SurviveX | TreeHacks 2025 | Edge AI Prize: Most Creative On-Device AI Deployment (Devpost says "$10k Cash"; UIC news says $9,000, LiquidAI EdgeAI track) | Hands-free, fully offline voice assistant that gives step-by-step survival guidance (fire, wounds, navigation) | ExecuTorch, PyTorch/torchtune, Llama, Swift, visionOS (Vision Pro), NVIDIA Brev | https://github.com/rockuutree/SurviveX-Treehacks | Winner interview: https://cs.uic.edu/news-stories/nandana-sheri-takes-first-place-at-stanford-hackathon · Devpost: https://devpost.com/software/survivex |
| ResolveIQ | ELEMENTX 2026 (MLH Hack Day) | Best Use of Snowflake (MLH) | AI incident-response "command center" that produces root-cause analyses from runbooks and past tickets | Snowflake Cortex AI, Groq, FastAPI, LangChain, FAISS, Sentence Transformers, React/Vite/Tailwind | — | https://dev.to/abdullahlko/we-won-best-use-of-snowflake-at-elementx-2026-mlh-hack-day-chj |
| Alfred Robot Butler | AI Robotics Hackathon, San Francisco (~Mar 2026, self-reported) | Grand Prize | Robot butler (no further detail given) | — | — | https://getpushtoprod.substack.com/p/how-to-win-hackathons (John Kim says he has won 7–8 hackathons, roughly $40k in prizes) |

## 3. Patterns

### A. Judging rubrics (cited)
**Knight Hacks IX (this weekend).** These are verbatim category names from https://knight-hacks-ix.devpost.com/. The rubric is identical to Knight Hacks VIII's.
1. **Originality:** is the problem space unique, is the approach original, and "have you heard of/seen this solution before?"
2. **Technical Understanding:** "Do the presenters actually know what they're talking about?" and "If they can't explain something, do they successfully admit/callout the tools that helped them?" Judges also ask whether the team learned or grew, and whether it admitted its technical challenges. **This means AI-assisted code is fine, but every teammate must be able to explain it, and the team should say plainly what the AI tools did.**
3. **Functionality:** polished or still a proof of concept? Does it reliably work as advertised? Is it end-to-end or fragmented?
4. **Design:** visual appeal, UX, and whether the design looks intentional or random.
5. **Wow Factor:** does it give "hope for humanity"? Would a company acquire it and hire the team? Would you show it to friends or post it on social media?

**Knight Hacks format and hard requirements:**
- Judging is science-fair style: "you'll demo your project to judges who visit your table" (KH VIII page).
- Submit on Devpost by **Sunday Oct 11, 10:00 AM**. **Stop committing to GitHub by 11:00 AM.**
- A **demo video is required**, and the **public GitHub repo is required**. A private or missing repo means disqualification.
- One member creates the team and invites the others. Anyone missing from the submission gets no prize.
- Teams are auto-entered into the Tracks and Overall. **Sponsor prizes must be selected manually.**
- Screenshots and visuals plus a detailed write-up are "recommended… clear, detailed write-ups stand out to judges."
- Use your registration email on Devpost to receive post-event feedback.
- The IX tracks on knighthacks.org are Hello World, AI/ML, App Dev, Game Dev and Embedded. The Devpost prizes are Best Overall 1–3, Most "Useful", Best Embedded, Best AI, Best Game Dev and Best First-Time Hacker. MLH prizes listed so far: ElevenLabs, Gemini API, Tiger Data, Solana, Presage, Vultr and GoDaddy Registry domain. Sponsor challenges are "revealed at opening ceremony."

**MLH Organizer Guide, Judging Plan** (https://guide.mlh.com/general-information/judging-and-submissions/judging-plan.md):
- MLH recommends science-fair judging with teams at numbered tables.
- Each team gets **about 3 minutes** to present. Judges are budgeted 4 minutes per project, including walking and scoring.
- The judging window is 2–3 hours, and each project gets about **3 judge visits**.
- MLH recommends **stack ranking**: each judge gives their top three 3/2/1 points, which evens out lenient and harsh judges. **Practical impact: you need to be in a judge's personal top 3, not merely "good."**
- MLH suggests 2-minute demo videos, used as reference during deliberation.

**Other majors:**
- **TreeHacks 2025/2026** (Devpost): Creativity ("wonder why there was a box at all"), Technical Complexity, Social Impact.
- **Hack the North 2025** (Devpost): WOW factor, Technical ability, Originality ("even if it doesn't solve a problem"), Design (intuitive for the target audience). Sponsor tracks use their own rubrics, e.g. Warp: wow, technical difficulty, originality, design. Cua judged its track on a public benchmark score (OSWorld-Tiny), per https://cua.ai/blog/hack-the-north.
- **HackGT 12:** criteria were deferred to live.hexlabs.org, which didn't render. Teams submit to Devpost and then to expo.hexlabs.org.

**The common core across all of them:** wow/creativity, technical depth, a working end-to-end build, and design/UX. Impact or usefulness appears as its own prize at Knight Hacks ("Most Useful").

### B. What the winners and judges say got rewarded
- **Differentiate from the field, not just on quality.** The SurviveX team chose hardware and on-device AI "knowing that most of the other projects were likely to be software-focused." Their moat: "not a lot of people were able to get their model working without WiFi" (UIC).
- **Study past winners and the frontier.** Dylan Lu (FaceTimeOS, Cal Hacks 12.0 1st) reviewed earlier years' winners and a recent survey paper, and picked an underexplored area (computer-use agents). He looked for a balance of "novel specialty and general applicability."
- **One person owns the UI and demo.** Lu again: judges only see the presentation. He also used **hardcoded fallbacks**: when clicking was flaky, the demo used only keyboard actions. His team split the work into three streams joined by agreed REST interfaces so everyone could build in parallel. They finished the video **30 minutes before judging**.
- **Build a demo, not a product.** John Kim (Alfred Robot Butler, grand prize) says to polish the happy path relentlessly and mock everything else, and to make sure the "wow moment" really works. His roles are PM/presenter, deep-tech diver and generalist integrator. On sponsors: **"stack the tracks"** by building one project that qualifies for several sponsor prizes, and ask each sponsor directly what would win. Lead the pitch with problem and story, not the stack. Feature the sponsor tools prominently.
- **Sponsor prizes are marketing.** Ray Deck, who says he won 5 hackathons (none named): ask "would rewarding this make the sponsor look good?" He calls the video "paramount" and advises "cut bone to ship."
- **Sponsor-tech depth wins MLH "Best Use of" prizes.** ResolveIQ won Snowflake by making Cortex central to the product. The team says the real work was retrieving and grounding the right context, not just calling an LLM.
- **Pivot fast when the plan fails.** ShiftyTech's hardware-lottery parts weren't available, so they re-brainstormed while still in line. They iterated on a single core (upgrading the pose model from MoveNet Lightning to Thunder, plus fine-tuning) and used mentor tickets when stuck. They demoed to MLH, Hack the North judges and the Replit sponsor between 9 AM and noon.
- **Judge-side view (Kurbaitaev, MLH x DigitalOcean judge, 2026):**
  - What wins: a working end-to-end demo first, then a **one-sentence opener stating what the project is and who it's for**, then tight scope.
  - What he asks every team: "Who specifically is this for?", "What part did you build this weekend?" and "What breaks first at scale?" Honest answers about limitations raised credibility.
  - Slide decks and the choice of stack mattered little.
- **Write-up and video:**
  - Jacklyn Biggin (MLH coach, judged about 20 events): keep Devpost's template sections, start the write-up by Saturday evening, and front-load what a judge needs in 5 minutes. Map the write-up to the posted criteria, and name each sponsor product and why you used it.
  - Devpost blog: reserve 2–3 hours for the video. Script it in this order: intro, problem, components, demo, close. Keep it under 3 minutes and open with the elevator pitch. Record decent audio. Mark YouTube uploads "Not made for kids" so judges can view them.

### C. Checklist (timed to the Knight Hacks IX schedule)
**First 2 hours after tracks drop (Friday night, opening ceremony):**
- [ ] Photograph the sponsor-challenge slides. Make a sheet with every prize, its rubric and its required tech.
- [ ] Pick **one Knight Hacks track** (AI, Embedded, Game Dev or useful/App) plus **2–3 MLH or sponsor prizes** the same build can qualify for, i.e. stack the tracks.
- [ ] Spend 20 minutes talking to sponsor tables: "What would win your prize?" Pitch the idea in one sentence and note what they react to.
- [ ] Score each candidate idea against the KH rubric (Originality, Technical Understanding, Functionality, Design, Wow). Kill any idea you have seen before. Prefer ideas that differentiate from the likely field, such as hardware or real-time voice/vision.
- [ ] Write the one-liner ("X for Y that does Z") and the **wow moment** the demo will end on.
- [ ] Define the MUST path (one end-to-end flow) and the STUB/NEVER lists.
- [ ] Assign roles: presenter/PM (also owns Devpost and video), core-tech lead, integrator, and a UI/demo owner. Agree the API contracts between modules.
- [ ] Create the public GitHub repo and the Devpost draft now, with every teammate added.

**The build (Fri night to Sat evening):**
- [ ] Get the happy path working end-to-end by the **halfway point (~Saturday noon)**. Mock whatever isn't on it.
- [ ] Integrate the sponsor tech deeply enough that it's visible in the demo.
- [ ] The UI owner starts the design pass early, with intentional, consistent styling (the Design criterion).
- [ ] Keep a running log of challenges and of what AI tools wrote. It feeds Technical Understanding and the Devpost "Challenges" section.
- [ ] Use mentors as soon as you're stuck for 30+ minutes.
- [ ] Start the Devpost write-up by **Saturday evening**, using the template sections.

**Last 6 hours (~Sat 4 AM → Sun 10 AM deadline):**
- [ ] Freeze features about 4 hours before the deadline. From then on it's bug fixes, hardcoded fallbacks for flaky steps, and seeded demo data only.
- [ ] Record a **sub-2–3-minute video** (aim for about 2 minutes, matching MLH guidance): pitch → problem → live product → wow → stack/sponsors. Upload to YouTube as "Not made for kids."
- [ ] Finish Devpost: screenshots or a GIF, architecture diagram, a sponsor-by-sponsor "how we used X," honest limitations, every teammate added, and every sponsor prize ticked.
- [ ] Submit by **10:00 AM**. Push the final commit before **11:00 AM**. Confirm the repo is public.
- [ ] Record a backup video of the demo and keep it on a laptop for the table in case the Wi-Fi or hardware fails.

**Judging/demo (science-fair table, ~3 minutes per judge, about 3 judges):**
- [ ] 0:00–0:15: the one-liner (what it is and who it's for), then **go straight to the live demo**. Never open with slides.
- [ ] 0:15–2:00: live demo of the happy path, ending on the wow moment.
- [ ] 2:00–3:00: tech in one breath, sponsor tools, then **what you'd build next or what breaks at scale**.
- [ ] Every teammate can explain every part. Judges may question the quietest member. Name the AI tools you used.
- [ ] Prepare answers to "What did you build this weekend?" and "What was hardest?"
- [ ] Keep the table visually clear: the screen facing the judge, the hardware visible, and a QR code linking to Devpost.
- [ ] Re-pitch sponsor judges using their own rubric language.

### Takeaways for our Knight Hacks project
1. **Optimize for the KH rubric, which is unusual.** "Technical Understanding" rewards teams that can explain their code and openly credit their AI tools. Rehearse every teammate on the architecture.
2. **Stack ranking means being memorable beats being solid.** Design one unmistakable wow moment and put it at the end of a ≤3-minute live demo that opens with the one-liner.
3. **Pick a lane the field will under-serve.** Hardware or on-device work (Best Embedded) and real-time voice/vision both stand out. Combine them with 2–3 MLH sponsor prizes the same build qualifies for (e.g. ElevenLabs voice + Gemini).
4. **Hard deadlines:** Devpost at 10:00 AM Sunday, commit freeze at 11:00 AM, the video and public repo are mandatory, and sponsor prizes need manual opt-in. Start the write-up Saturday evening.
5. **Have the end-to-end path working by Saturday noon.** After that, polish, add fallbacks and rehearse. The working demo is the single largest differentiator.

## 4. Open questions / next searches
- **MLH's old "judging criteria" page is gone.** https://guide.mlh.com/general-information/judging-and-submissions/judging-criteria (redirected from guide.mlh.io) returns 404, so I could not confirm MLH's verbatim recommended criteria (technical difficulty / creativity / design / usefulness). Lead: the example sheet at https://hackp.ac/judgingexample, not fetched.
- **Knight Hacks judging timing is unknown.** https://knight-hacks.notion.site/knight-hacks-viii (the "Hacker's Guide") is a Notion page that rendered empty. Get the minutes per team, the finalist round, and judging start time from the Discord or the opening ceremony.
- **Pages that didn't load:**
  - https://hackthenorth.notion.site/2025-judging-instructions-faq (Notion, empty)
  - https://live.hexlabs.org/ (HackGT 12 criteria, empty)
  - https://medium.com/design-bootcamp/how-we-won-at-hackgt-22-5bec54a0a4d6 ("How we won at HackGT '22," 403 from Medium/Cloudflare; scribe.rip 404; archive.org blocked)
  - https://anubhav-gupta.medium.com/winning-hackathons-my-4-years-of-college-experience-af459c4fa99a (403)
  - https://hunter.cuny.edu/news/hunter-computer-science-undergraduate-team-places-first-in-hack-knight-hackathon (GreenByte, Hack Knight 2025 Health track; 403)
- **The TreeHacks percentage weights in search snippets are unverified.** They are creativity 35 / technical 25 / impact 25 / presentation 15, but appear only on spam mirror sites. Not used.
- **Medium posts not fetched:** https://medium.com/@1grace/my-mlh-major-league-hacking-top-50-experience-journey-cea4fda04195 (MLH Top 50) and https://medium.com/@eyal.shechtman/hack-the-hackathon-a-proven-formula-for-winning-231663ff00cc.
