# Synthesis: what wins, and how we win Knight Hacks IX

_v3, 2026-10-09. Built from all 31 research files (30 research tasks; Knight Hacks history is split across two files): about 880 logged winners chosen from several thousand badge-confirmed winners scanned, with about 1,800 source URLs.
Every claim traces to a `winners-*.md` file; open that file for the source URLs. Update this file in place as we learn more._

## 1. The event (verified on mlh.com)
- **Knight Hacks IX**, Oct 9–11, 2026, in person in Orlando. Sponsor challenges are revealed at the opening ceremony.
- **Main prizes:** Best Overall 1st–3rd ($3,600 / $2,000 / $1,240 plus hardware), Most "Useful" Hack, Best Embedded, Best AI, Best Game Dev, Best First-Time Hacker.
- **MLH prizes:** ElevenLabs, Gemini API, Tiger Data (new), Solana, Presage, Vultr, GoDaddy Registry domain, DEV Writing Challenge.
- **Logistics:** the Devpost deadline is **Sun 10:00 AM** (code freeze 11 AM), and a public repo and demo video are required. Judging runs 12–4 PM (see §5b for the 3-min vs 6-min format question). Missing your appointment disqualifies you from that challenge and from the general tracks.
- **Rubric (same as VIII):** Originality, **Technical Understanding** (explicitly rewards naming which AI tools you used and what you learned), Functionality, Design, Wow Factor.
- **IX sponsor challenges, per the Hacker's Guide** (winners-knighthacks-history):
  - **Returning, with challenges confirmed:** AMD (Gold; ROCm/HIP/Developer Cloud, loaner hardware; won 5× in 2025), NextEra (2024 energy efficiency, 2025 drone-inspection routing with OR-Tools), BNY (2024 fraud detection, 2025 inventory "Scrumbot"), OneEthos (AI for financial empowerment, now solar financing).
  - **New:** Full Sail (Platinum; Overall 1st adds a full-ride), Hugging Face (Gold), Databricks, NVIDIA (**Jetson hardware pickup Friday**), Encompass.
  - **New general tracks:** Figma "Best Design" and Adobe "Prettiest Hack".
  - **Not running challenges this year:** Morgan & Morgan (tabling only), ServiceNow, Google Cloud.
- **Other Florida repeat sponsors** (winners-florida): Waymo, Assurant, State Farm, Capital One, Microsoft. These are less likely here, since they aren't on the IX list.

## 2. The winning formula (the same signal in every regional file)
0. **At Knight Hacks itself, hardware + AI for health or accessibility won Best Overall three years running:** Tacti-sight (2023, ESP32 haptic vision), Formify (2024, Arduino + MediaPipe rehab), Restful Knights (2025, ESP32 EEG/SpO2 sleep screening on AMD ROCm). The only pure-software Overall winner was Emergent (2025, a Gemini ADK disaster-simulation multi-agent system).
1. **A specific, sympathetic user with high stakes.** The pattern holds across nearly every grand prize: blind navigation (Shepherd, NaVox, iPalo), dementia (Lumos, Recall), ALS (Clench), 911 dispatch (Dispatch AI), medication safety (Argus), and a narrow clinical moment (TapChart's "Parkinson's mistaken for stroke"). Generic "AI assistant" or "ChatGPT for studying" pitches win sponsor prizes at most.
2. **A physical or multimodal "wow" in the demo.** Only about 5–8% of winners use hardware, yet hardware projects take a much larger share of grand prizes. Examples: TreeHacks 2024–26 (4 of 7 grand placings), every HackGT 13 top-3 project (Sep 2026), and 7 of 12 recent Florida top-3 overall slots. Cheap ways to get there: ESP32 or Pi sensors, a phone camera running MediaPipe/YOLO, phone LiDAR, AR or glasses.
3. **AI that visibly *does* something.** The action is the climax of the demo: Alto opens the bug fix, Bye! Buy! lists and negotiates, FaceTimeOS texts back a screenshot. A plain computer-use agent (Jarvis) won only an MLH prize. The same idea through a novel channel (FaceTime) won 1st Overall at Cal Hacks.
4. **A non-chat interface, usually voice.** ElevenLabs, Deepgram or Vapi voice is near-standard in 2025–26 winners. Other novel channels that won: SMS, phone calls, FaceTime, glasses, haptics.
5. **One hard part built by hand.** Winners wrote their own inverse kinematics, LiDAR steering with smoothing, or a custom pipeline, and said so in "How we built it". Judges reward depth over API glue. Florida judges have even created anti-AI-slop prizes ("Least Vibecoded", GitHub "Ship It").
6. **A reliability or eval layer is the new differentiator.** LA Hacks 2026: 1st place (codebreaker) built its own benchmark and 3rd (Autopsy) learns from agent failures. A success rate over N runs, a trace viewer, or a verify-then-act step all set a project apart from the many "agent that does X" entries.
7. **Named multi-agent architecture.** Two to four named agents (Scout, Triage, Comms) make the system easy to follow in 3 minutes and map neatly onto sponsor prizes such as Google ADK + A2A or Fetch.ai.
8. **Offline / on-device survives the venue and impresses judges.** Every placer in Kaggle's judged Gemma hackathons ran on a phone, a Pi 5 or a Jetson. Voice and vision demos that survived venue WiFi ran locally. SurviveX won partly because "not a lot of people were able to get their model working without WiFi" (winners-kaggle, winners-voice-vision-multimodal, winners-playbook-judging).
9. **Domain-specific shapes that keep winning.** Health: clinical documentation, i.e. speech in and a real standard out (SOAP, ICD-10) (winners-health). XR: Quest XR + AI took Knight Hacks 2nd Overall in 2023 *and* 2024 (winners-ar-vr-gaming). Game: unusual input or colocated multiplayer, e.g. Crimson Brawl (EEG) and Shipwreck Showdown (4-player) at Knight Hacks (winners-design-creative-categories). Education: AI inside the live lecture beats a solo study chatbot (winners-education). Climate: address-level storm or heat risk beats a carbon tracker (winners-sustainability-climate).
10. **Real public data, especially Florida data.** FloodGuard, hurrycane and T.I.T.A.N. won with NOAA, USGS and FEMA flood and hurricane data. Hacklytics winners used FBI NIBRS and HDX data, shown on a map or globe rather than in a notebook.

## 3. Prize strategy for Knight Hacks IX
- **Each project wins at most one MLH prize.** Across 95 MLH wins scanned, none took two MLH categories at the same event. Realistic ceiling: **main prize + 1 MLH + 1 sponsor challenge**, plus the free extras. Past Knight Hacks examples: CookQuest (Vultr + Most Useful), KnightSource (Gemini + Google ADK challenge).
- **Free extras:** register a punny **GoDaddy Registry domain** (about 15 minutes; the name doubles as the live URL, e.g. which.courses, amicooked.us) and post the write-up to the **DEV Writing Challenge** after the event.
- **Choosing the MLH category:** Gemini and ElevenLabs are the most crowded. To win ElevenLabs, voice must *be* the product (iPalo, Hey Buddy). **Presage** (camera vitals/emotion) and **Tiger Data** (time-series: hypertables plus a continuous-aggregate dashboard) have small fields and fit health, sensor or city-data hacks. **Solana** only wins with a real-world on-chain flow, not a bolted-on token.
- **Main-track fit:** a hardware + AI accessibility or health build competes for Best Overall, Best Embedded, Best AI *and* Most Useful at once. That's four doors from one build.
- **Sponsor challenges: answer the prompt literally and use the provided data.** NextEra's drone winners all used OR-Tools, and ServiceNow's winners used the CSVs provided. Sponsor tracks often have 3 winner slots, with fewer entrants than Overall.
- **The best sponsor bet is AMD** (Gold sponsor, won 5× in 2025 across Restful Knights, Lawgorithm, Scenergy, CloseCalls and Sora2Detector, with loaner GPUs and Developer Cloud). Make ROCm/HIP load-bearing, for example by running the model on AMD. EchoAI won Best AI + AMD, and Lawgorithm won AMD + Morgan & Morgan. **NVIDIA Jetson** is a natural fit for an embedded build (Best Embedded).
- **How technical sponsors (AMD, NVIDIA, Databricks) judge: they want measured gains, not polish** (winners-taikai-hackerearth-enterprise, winners-lablab-ai). AMD winners showed benchmark numbers (RadeonFlow, "3B beats 120B") or fully offline demos. Databricks winners used 4–5 platform features. Put a before/after number on screen, such as latency, throughput or cost on ROCm vs baseline, and build on the sponsor's *newest* product.
- **Corporate sponsors favour tools for their own staff and operations** over consumer apps (winners-texas, winners-orlando-industry). Read BNY, NextEra and Encompass prompts as "solve our internal problem literally".
- **Polish counts twice:** Figma "Best Design" and Adobe "Prettiest Hack" are separate prizes, and Design is a rubric line.

## 4. Idea scorecard (apply when the tracks drop)
Score each candidate 0–2 on each line. Build the highest scorer that we can actually finish.

| # | Criterion | 2 points looks like |
|---|---|---|
| 1 | Named user + stakes | "Blind UCF students crossing Gemini Blvd", not "people" |
| 2 | Visible real action | The system calls, books, alerts or moves something live on stage |
| 3 | Physical/multimodal wow | A sensor, camera, AR or voice moment a judge can touch or hear |
| 4 | Hard core we build | One non-trivial piece we wrote and can explain |
| 5 | Prize stack | Fits Best Overall + 1 main category + 1 sponsor + 1 MLH (+ domain) |
| 6 | Finishable | Works end to end in a 3-minute demo, built in about 30 hours, with a recorded fallback |
| 7 | Real data / proof | A real dataset, a measured result ("1/20th the cost", "92% over 50 runs") |

## 5. Anti-patterns (seen losing, or capped at minor prizes)
- **Another blind-navigation cane or haptic walking aid.** The category is saturated (winners-hardware-iot). Knight Hacks alone has had iPalo (2025), EchoAI (2025) and SensAi, and judges will have "seen this before" (Originality). Keep the *assistive hardware + AI* formula but pick an under-served user or sense, as Restful Knights did with sleep screening and Clench with ALS.
- **Another sign-language translator** is also overdone (winners-social-good-accessibility). Knight Hacks has no social-good or accessibility prize, so an impact story has to win through Most Useful, Best Overall or a sponsor prize.
- A chat window as the main UI. A generic assistant with no named user.
- Scattering across 6 sponsor logos. Judges noticed ("sponsormaxxing").
- The second "Cursor for X" at the same event.
- A token bolted onto an app to chase Solana.
- Scope that doesn't work live. "Completion: a working prototype, not a concept" is an explicit criterion at SwampHacks.

## 5b. Judging reality (winners-playbook-judging)
- **Judges stack-rank.** MLH recommends that each judge give their personal top 3 points of 3/2/1, so being *memorable* beats being merely solid. End the demo on one unmistakable wow moment.
- **Format conflict, so prepare both versions:** the IX Hacker's Guide describes appointment slots (2 min setup + **6 min** present and Q&A). The KH VIII Devpost page and MLH describe science-fair table visits of about **3 min**. Have a 3-minute core pitch with 3 minutes of depth or Q&A on top.
- **Pitch shape:** a one-sentence opener ("X for Y that does Z"), then **straight to the live demo** (no slides), ending on the wow. Then the tech in one breath plus the sponsor tools, then "what breaks at scale". Judges ask "Who specifically is this for?" and "What did you build this weekend?"
- **Technical Understanding:** judges may question the quietest teammate, so everyone must be able to explain every part. Openly credit the AI tools used.
- **Devpost:** **sponsor prizes must be ticked manually.** Every teammate must be on the submission, or they get no prize. Video under 3 min (aim for about 2), YouTube set to "Not made for kids". Start the write-up Saturday evening.
- **Milestones:** happy path working end to end by **Saturday noon**. Feature freeze about 4 hours before the deadline, then fixes, hardcoded fallbacks and seeded demo data only. Keep a backup demo video on a laptop at the table.
- The full timed checklist is in `winners-playbook-judging-2026-10-09.md` §3C.

## 6. Pre-ceremony checklist (today)
- [ ] Get the NVIDIA Jetson (pickup is Friday) and AMD loaner hardware or Developer Cloud access. **Bring your own boards, sensors, cables and power.** The MLH lab is small (about 9 Pis and 12 Arduinos) and holds your ID (winners-hardware-iot). Sponsor-hardware tracks (NVIDIA, ROS2, drones) draw few entrants.
- [ ] Winning embedded shape: **ESP32/Pi sensor + AI brain + live dashboard**.
- [ ] Note the workshops: AMD "Your First GPU Kernel: HIP" (useful for the AMD prize), NextEra "Spot the Dog: Robot Vision at Nuclear Plants" (hints at NextEra's prompt), BNY "Prompt Wars: attack and defend AI chatbots" (hints at BNY's prompt).
- [ ] Create API keys and accounts: Gemini, ElevenLabs, Vultr credits, Presage SDK, Tiger Cloud, GoDaddy claim code.
- [ ] Set up the repo skeleton (frontend + FastAPI/Node backend + deploy target), so hour 1 goes into the idea, not setup.
- [ ] At the ceremony, write down every sponsor prompt verbatim into `research/knighthacks-ix-tracks.md`, then score ideas against §4.
- [ ] Assign roles: hardware/CV, backend/agents, frontend/demo polish, pitch/Devpost/video owner.
- [ ] Plan backwards from **Sun 10 AM**: Devpost draft and video recorded by about 8 AM Sunday, with the repo public. Rehearse the 6-minute pitch and name every AI tool used (Technical Understanding).

## 7. Evidence-backed directions to test against the tracks (not decisions)
These are starting points that score well on §4. Pick one only after reading the actual sponsor prompts.
- **Embedded health or assist device on Jetson or AMD:** a sensor + on-device model + live dashboard for an *under-served* condition (not blind navigation or ASL). Targets Overall, Best Embedded, Best AI, NVIDIA/AMD with a benchmark number, plus Presage or ElevenLabs.
- **Voice agent that takes a real action for a Florida user**, such as a hurricane-prep or utility-outage caller or a claims or appointment phone agent, with a visible eval/success-rate panel. Targets Best AI, Most Useful, ElevenLabs, and fits NextEra or a finance prompt if worded that way.
- **Sponsor-literal internal tool** (BNY, NextEra, Encompass, OneEthos): solve their ops problem with their data, show a measured result, and polish the UI for Figma/Adobe.
- **XR + AI for an everyday task** (the CookQuest and GuitAR lineage) for Best Game Dev or Most Useful, with a no-headset fallback.

## 8. Where to dig deeper
`INDEX.md` lists every file by category. The most useful for this weekend:
- Knight Hacks winners, IX sponsors and their past prompts: `winners-knighthacks-history-2026-10-09.md`
- Timed checklist and pitch script: `winners-playbook-judging-2026-10-09.md`
- MLH prize requirements and past winners: `winners-mlh-sponsor-prizes-2026-10-09.md`
- AMD/NVIDIA/Databricks-style judging: `winners-taikai-hackerearth-enterprise-2026-10-09.md`
- Agent and voice patterns: `winners-ai-agents-2025-2026-…`, `winners-voice-vision-multimodal-…`
