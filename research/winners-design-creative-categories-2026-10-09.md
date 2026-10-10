# Winners: Craft categories (Most Useful, Game, First-Time, Design, Creative, Technical, Funniest, People's Choice)
_Researched 2026-10-09 · sources: Devpost galleries for Knight Hacks VII/VIII, SwampHacks XI, Hackabull 2025, ShellHacks 2024, HackDavis 2025, HackHarvard 2025, HackUTD 2025, HackTX 2024, HackPrinceton S25, HackIllinois 2025, nwHacks 2025, UofTHacks 13, SpartaHack X, MHacks 2024, plus devpost.com/software project pages_

## 1. Scope
- **Method.** I fetched each gallery's pages 1–2 with curl, which works where WebFetch returns 403 on subdomains. I took every entry with a Winner ribbon (about 390 projects), then parsed each devpost.com/software page for the prize text, Built With tags and GitHub links. I kept only prizes judged on craft or on the main track.
- **Galleries visited (all `<slug>.devpost.com/project-gallery`):** knight-hacks-vii, knighthacksviii, swamphacks-xi, hackabull-2025, shellhacks2024, hackdavis-2025, hackharvard-2025, hackutd-2025, hacktx-2024, hackprinceton-spring-2025, hackillinois-2025, nwhacks-2025, uofthacks-13, spartahack-x, mhacks-2024, boilermake-xii, hackrice-15, cuhackit-2025. The last three had no craft-category prizes. I logged only GoHelpMe (CUhackit Wild Card) in Patterns.
- **Knight Hacks VII/VIII rows** went to winners-knighthacks-history-2026-10-09.md, which logged them in parallel, so I don't duplicate them here. I verified them myself and cite them by name in Patterns: Restful Knights, FLITE, Crimson Brawl, Virtual Foosball, EchoAI, FinTerra ("Prettiest Hack"), Kinexis, Chat, Clip That! ("Usefulness" Prize), Kitty Does Warfare, Shipwreck Showdown, Formify, GuitAR and SensAi.
- **Skipped, already logged elsewhere:** CookQuest (KH VIII Most "Useful" + Vultr) is in mlh-sponsor-prizes. SignHero (SwampHacks XI Overall + Best Game Design) and Pocket Money (SwampHacks "Least Vibecoded") are in florida. I also skipped sponsor and MLH prizes, which belong to other agents.

## 2. Winners table
| Name | Hackathon | Prize/track | What it does | Stack | Repo | Source URL |
|---|---|---|---|---|---|---|
| Neuroview | SwampHacks XI | Best User Design | Interactive 3D brain visualization for neuroanatomy | Three.js, FastAPI, nibabel | https://github.com/CodingWithKantecki/NeuroView | https://devpost.com/software/neuroview |
| Siren | HackDavis 2025 | Best UI/UX Design | Mobile aid map and needs board for underserved communities | React Native, Expo | https://github.com/NickSulistio/HD2025 | https://devpost.com/software/siren-njz6x7 |
| SpendingWithSpendy | HackUTD 2025 | Best Design + Capital One | Kids' money-management app | React, Expo, Tailwind | https://github.com/brendanshen24/SpendWithSpendy | https://devpost.com/software/spendingwithspendy |
| Biodex | HackTX 2024 | Best Design | Photograph wildlife and get AI trading cards | React Native, Flask, Firebase, OpenAI, Google Maps | https://github.com/VincentDo8439/hacktx2024/tree/stable-version | https://devpost.com/software/biodex-3fyaxq |
| PeerUP | nwHacks 2025 | Best Design Project | Peer tutoring skill exchange and meetups | React, Firebase, Gemini, Tailwind | https://github.com/mhuang306/NwHacks2025 | https://devpost.com/software/peerup-study-pairing-with-care |
| EthicScope | HackDavis 2025 | Most Creative Hack | Scan products for ethical sourcing insights | Next.js, Flask, Cerebras, Tavily, MongoDB | https://github.com/marcus-leung/EthicScope | https://devpost.com/software/ethicscope |
| FocusPal | HackDavis 2025 | Most Technically Challenging Hack | CV focus tracker with real-time nudges | OpenCV, Gemini, Next.js, Flask, WebSockets | https://github.com/FocusPals | https://devpost.com/software/focuspal |
| AggieShare | HackDavis 2025 | Hacker's Choice Award | Campus donate-and-discover goods exchange | React, MongoDB, Gemini, Cloudinary | https://github.com/zrlck/AggieShare | https://devpost.com/software/aggieshare |
| Minti | HackIllinois 2025 | Fan Favorite Hack | Calendar-integrated AI financial advisor | Flask, FullCalendar, OpenAI, Nessie API | — | https://devpost.com/software/minti-9lb8kw |
| freak-cha | HackHarvard 2025 | Funniest Hack | Absurd "AI-proof" MFA CAPTCHA | Next.js, tRPC, Supabase, YOLOv8 | https://github.com/anselmlong/hackharvard | https://devpost.com/software/freak-cha |
| Scan-Craft | Hackabull 2025 | Funniest Hack | Minecraft-style crafting in the real-world apocalypse | Flask, Gemini, MongoDB, Tailwind | https://github.com/michaelbennieUFL/2025hackabull | https://devpost.com/software/asdf-56o8ej |
| 67Ranked | UofTHacks 13 | Ignobel Prize | "Brainrot" sub-minute body-controlled camera game with a global leaderboard | Next.js, MediaPipe, Supabase | — | https://devpost.com/software/67-ranked |
| ScrewYouIKEA.com | HackHarvard 2025 | Best First-Time Hack | Turns static assembly manuals into interactive 3D animations | Next.js, Three.js, Gemini 2.5, pdf.js, Vercel | https://github.com/donaragalstyan/ScrewYouIkea | https://devpost.com/software/screwyouikea |
| WiSPR | HackUTD 2025 | Best Beginner | Wearable hazard badge with silent vibration/LED alerts | Arduino, C++, React, Figma | https://github.com/ParisUNgo/HackUTD-WiSPR | https://devpost.com/software/wispr-wireless-safety-pulse-relay |
| Aegis | SwampHacks XI | Best Beginner Hack | CV gate that blocks workers missing PPE, with an OSHA audit trail | OpenCV, Gemini, React, Flask, MongoDB | https://github.com/AndrewFesenko/SwampHacksXI | https://devpost.com/software/aegis-axf8et |
| Croak Quest | nwHacks 2025 | Best Beginner Project | Sign-language 2D platformer using Leap Motion | Unity, C#, Leap Motion | https://github.com/Khaedra/nwHacks-2025.git | https://devpost.com/software/croak-quest |
| Tetrify | HackTX 2024 | Best Novice | Motion-controlled accessible Tetris | Pygame, OpenCV, MediaPipe | https://github.com/rizkyapratama100/ARES-HackTX-Project | https://devpost.com/software/ares-accessible-tetris |
| PantherPlates | ShellHacks 2024 | Best First-Time Hackers | Dining-hall meal planner for dietary needs | React, Flask, Selenium, MongoDB, OpenAI | https://github.com/tr4ce123/pantherplates | https://devpost.com/software/pantherplates |
| Commander Coco's Stellar Domination | ShellHacks 2024 | Best First-Time Hackers | Unity chase game | Unity, C# | — | https://devpost.com/software/commander-coco-s-stellar-domination |
| CoCo | HackPrinceton S25 | Best Game | CV hand-gesture sketch tool and co-composer with AI | Next.js, MediaPipe, OpenCV, Gemini, ElevenLabs | https://github.com/mohulshukla/CoCo | https://devpost.com/software/coco-5r8sft |
| WizViz | SpartaHack X | [Interactive Media] Best Game | Wizard duel cast with body gestures | Pygame, OpenCV, MediaPipe | https://github.com/knivier/WizViz | https://devpost.com/software/wizviz |
| EscapeMate | MHacks 2024 | Interactive Media & Gaming Track | AI-generated physical escape rooms | Raspberry Pi, Groq, Cartesia, React | https://github.com/wenbox360/MHacks-F24/ | https://devpost.com/software/escapemate |

## 3. Patterns
**Knight Hacks main categories (two years of data)**
- **Most Useful / "Usefulness"** went to a concrete everyday pain point with a working demo: CookQuest (a cooking helper in a Quest headset, KH VIII) and Chat, Clip That! (an auto-clipper for streamers built on ESP32 and a Raspberry Pi, KH VII). Neither is a "platform." Both solve one task end to end, and both included hardware or XR.
- **Best Game** never went to a plain browser game. Shipwreck Showdown was a 4-player networked Unity game with custom pixel art. Crimson Brawl was controlled by EEG. Novel input wins game prizes elsewhere too: WizViz and Tetrify used body gestures, Croak Quest used Leap Motion, 67Ranked used the camera, and EscapeMate used physical hardware. **An unusual controller is the strongest repeated signal.**
- **First-Time** winners are polished, scoped, single-purpose apps. FLITE is a mission-control UI built with React and MapLibre. Kitty Does Warfare is a Pygame game. ScrewYouIKEA is a Three.js manual animator. First-timers who use a game engine (Kitty Does Warfare, Commander Coco, Croak Quest) or one CV library (Tetrify, Aegis) win often. Most of these teams had no backend.
- **Overall** winners at KH are assistive or health projects combined with hardware or XR: Formify, GuitAR, SensAi and Restful Knights. EchoAI (Best AI) does LiDAR navigation for the blind.
- **Repeat builders win.** Jaehoonoo won KH VII (EcoSense, NextEra) and KH VIII (EchoAI). CodingWithKantecki won KH VIII (Kinexis) and SwampHacks XI (Neuroview), both medical tools with MediaPipe or 3D.

**Design / UI-UX prizes** (Neuroview, Siren, Spendy, Biodex, PeerUP, FinTerra "Prettiest") went to consumer or mobile apps with a single clear persona, a playful identity (a mascot, trading cards, a named AI persona) and Expo/React Native or Three.js visuals. Spendy stacked Best Design with a Capital One prize. The design prize rewards whoever owns the Figma pass and a cohesive theme.

**Creative / Technical / Funniest / People's Choice**
- **Funniest and Ignobel:** irony in the name or premise (freak-cha, 67Ranked, Scan-Craft) plus a real working ML piece (YOLOv8, MediaPipe). The joke lands because the tech works.
- **Most Technically Challenging:** FocusPal combined real-time CV, WebSockets and an LLM. Judges reward a live multi-part pipeline over a CRUD app.
- **People's / Hacker's / Fan Favorite:** campus-relatable consumer apps such as AggieShare (UC Davis goods exchange) and Minti (student finance). Peers vote for what they would personally use. GoHelpMe won CUhackit's "Wild Card."

**Stacking evidence.** Single projects that took two prizes:
- CookQuest: Most Useful + MLH Vultr
- EchoAI: Best AI + AMD
- SignHero: Overall + Best Game Design
- Spendy: Best Design + Capital One
- QuizMe (SpartaHack X): Interactive Media track + YouLearn

Most projects win one prize, and two is the realistic ceiling. The working combination is **one main/craft category + one sponsor or MLH prize** that the stack already uses.

**Recurring tech** across the 35 craft and main-track winners reviewed, KH rows included: MediaPipe/OpenCV (8), Unity/C# (5), Next.js + Tailwind, React Native/Expo, Gemini, ESP32/Arduino, Meta Quest.

### Takeaways for our Knight Hacks project
1. **For Best Game, ship a novel input** (camera gestures, EEG, Leap, ESP32 controller, Quest). Make it multiplayer if possible, because both KH Game winners were 2–4 player.
2. **For Most Useful, pick one daily pain point** and show the full loop live. CookQuest and Chat, Clip That! show that adding hardware or XR helps it stand out.
3. **Spend 2–3 hours on visual identity** (mascot or persona, a consistent palette, a Figma mock). FinTerra won KH's "Prettiest" and design prizes recur everywhere, so this makes a design or Prettiest prize stackable if it is offered at IX.
4. **Plan exactly one stack:** main category + one sponsor or MLH prize your stack already uses (Gemini, ElevenLabs, Vultr, AMD). Don't chase five.
5. **If any teammate is a first-timer,** a scoped, polished single-purpose app (FLITE, ScrewYouIKEA) can take Best First-Time Hacker. Check eligibility rules at opening ceremony.

## 4. Open questions / next searches
- **KH VIII 2nd/3rd place.** The knighthacksviii gallery shows only one "Best Overall Hack" winner (Restful Knights), and I did not find 2nd/3rd overall: https://knighthacksviii.devpost.com/project-gallery
- **Knight Hacks IX prize page and judging criteria.** Not fetched: https://knight-hacks-ix.devpost.com/
- **Galleries returning 404** for the slugs I guessed: shellhacks-2025, swamphacks-x, hackmit, lahacks-2025, hackprinceton-fall-2024, deltahacks-11, rowdyhacks-2025, hackfsu. Leads for more Most Useful and Most Useless winners.
- **WebSearch for "Most Useful Hack" / "Most Useless Hack"** on devpost.com/software returned no Devpost results, so these exact category names are rare outside Knight Hacks. HackTCNJ (Funniest Hack) and Stupid Hackathon-style events are leads.
- **Repo unknown** for Minti, 67Ranked and Commander Coco. FocusPal's link is a GitHub org, not a repo.
