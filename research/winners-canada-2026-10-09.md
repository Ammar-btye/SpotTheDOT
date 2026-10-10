# Winners: Canadian hackathons (Hack the North, UofTHacks, nwHacks, McHacks, Hack the 6ix, DeltaHacks, Hack Western, QHacks)

_Researched 2026-10-09 · sources: Devpost project galleries and project pages (each win confirmed by the "Winner" badge and the prize list on the project page)_

## 1. Scope

**Method.** WebFetch returns HTTP 403 on Devpost, so I fetched the galleries and project pages with curl. For each gallery I pulled every project with a Winner badge, then parsed its project page for the exact prize names at that event, the "Built With" tags and the "Try it out" links. Across 14 events I parsed about 290 winning projects. 30 are logged below: mostly overall podiums and finalists, plus a few standout track wins. Stack tallies in §3 cover the 222 winners from the first 11 galleries.

**Galleries parsed in full (winners plus project pages):**
- Hack the North 2023 / 2024 / 2025 / 2026: https://hackthenorth2023.devpost.com/project-gallery (and the `2024`, `2025` and `2026` subdomains)
- UofTHacks 13 (Jan 2026): https://uofthacks-13.devpost.com/project-gallery
- nwHacks 2025 / 2026: https://nwhacks-2025.devpost.com/project-gallery, https://nwhacks-2026.devpost.com/project-gallery
- McHacks 12 (2025) / McHacks 13 (2026): https://mchacks-12.devpost.com/project-gallery, https://mchacks13.devpost.com/project-gallery
- Hack the 6ix 2025 / 2026: https://hackthe6ix2025.devpost.com/project-gallery, https://hackthe6ix2026.devpost.com/project-gallery
- DeltaHacks 12 (Jan 2026): https://deltahacks-12.devpost.com/project-gallery
- Hack Western 12 (Nov 2025): https://hack-western-12.devpost.com/project-gallery
- QHacks 2026: https://qhacks-2026.devpost.com/project-gallery

**Galleries that loaded but where I didn't parse project pages (time):** uofthacks-x, uofthacks-11, nwhacks-2023, nwhacks-2024, mchacks10, mchacks-11, hackthe6ix2023, hackthe6ix2024, deltahacks-x, deltahacks-xi, hack-western-10, qhacks-2023/2024/2025.

**Skipped:** Tango (HTN 2025 finalist) is already logged in `winners-ai-agents-2025-2026`. Most MLH "Best Use of X" wins are skipped too, because the MLH sponsor-prize file covers them.

## 2. Winners table

| Name | Hackathon | Prize/track | What it does | Stack | Repo | Source URL |
|---|---|---|---|---|---|---|
| Orbis Engine | Hack the North 2026 | Finalist; OpenAI API Prizes | Turns any filmed footage into explorable 4D (Gaussian-splat) scenes, viewable in WebXR | Python, PyTorch, gsplat, World Labs Marble, Modal, three.js, WebXR, Meta Quest, OpenAI API | https://github.com/dtpu/OrbisEngine | https://devpost.com/software/temp-jcyltx |
| Reflex | Hack the North 2026 | Finalist | "AI writes skills for us": an agent generates robot skills and trains or simulates them on a real arm | ROS2, LeRobot, SmolVLA, MuJoCo, MCP, Anthropic API, ESP32/STM32, Next.js | https://github.com/ZechariahWang/htn-2026/ | https://devpost.com/software/reflex-e0jkih |
| CADEX | Hack the North 2026 | Finalist | Natural language to manufacturable CAD for people with no CAD experience | CadQuery, OpenAI/Codex, Hono, Node, React, Vite | https://github.com/justinbaduaa/htn2026 | https://devpost.com/software/cadex |
| punching-face | Hack the North 2026 | Finalist; Sentry Best Use of Sentry | Webcam-driven 3D face-punching game with real-time 3D reconstruction | MediaPipe, Open3D, COLMAP, three.js, WebRTC, LiveKit, OpenAI, Sentry | https://github.com/akashngb/punching-face | https://devpost.com/software/punchface |
| Settlers of Solana | Hack the North 2026 | Finalist; Solana Best Use of Solana | A swarm of AI agents simulates a free-market economy on Solana | Rust, Solana, Claude, OpenAI/Codex, Baseten | https://github.com/leakyhose/agent-economy | https://devpost.com/software/_solanasim |
| Praxis | Hack the 6ix 2026 | 1st Place; QNX Best Use of QNX | QNX rehab device that scores a patient's tracing exercise for accuracy and stability with AI | QNX, Raspberry Pi, C++, Python, Claude, Gemini, MongoDB | https://github.com/n1mk1/ht6 | https://devpost.com/software/praxis-41b68v |
| TraceLoop | Hack the 6ix 2026 | 2nd Place | "Cursor for firmware": an agent writes, simulates (Renode), tests and explains embedded code | Zephyr, Renode, Modal, Inngest, tRPC, Supabase, React, Vercel | https://github.com/Hostileoracle0606/TraceLoop | https://devpost.com/software/traceloop |
| MIRL – Minecraft IRL | Hack the 6ix 2026 | 3rd Place | Play Minecraft with your body: real sword, shield and bow via IMU sensors plus CV | ESP32, MPU6050, OpenCV, Java (Fabric mod), C++ | https://github.com/Solaror0/HT62026-MIRL | https://devpost.com/software/mirl-minecraft-irl |
| McGill Go | McHacks 13 (2026) | First Place | Finds exchange-semester courses abroad that count toward your McGill degree | FastAPI, Next.js, MongoDB, Selenium, Gemini, Claude | https://github.com/yufei002/McHacks-13 | https://devpost.com/software/exchange-v1hmq8 |
| WaterYouDoin | McHacks 13 (2026) | Second Place | Nudges you about AI over-reliance by showing the water cost of your prompts | TypeScript, Node, Vite, Vitest | https://github.com/memoud0/WaterYouDoin | https://devpost.com/software/wateryourdoin |
| Identity Matrix | UofTHacks 13 (2026) | Overall 1st; Best "UofT" Hack | Multiplayer world where your avatar becomes a stateful AI agent that keeps living after you log off | React, Phaser.js, FastAPI, Supabase, Gemini, OpenAI, OpenRouter | https://github.com/qiuethan/UofTHacks-Project | https://devpost.com/software/temp-sqyptg |
| Project Horizon | UofTHacks 13 (2026) | Overall 2nd; Backboard.io; TwelveLabs | Converts third-person sports video into a realistic first-person POV | Python, React, TypeScript, Gemini, OpenAI, Backboard | — | https://devpost.com/software/project-horizon-8iodp2 |
| Shop-A-Sketch | UofTHacks 13 (2026) | Overall 3rd | Draw what you imagine and get matching products to shop | React, Vite, Tailwind, Node, Python, Gemini, Docker, Render | https://github.com/clairez308/uofthacks26 | https://devpost.com/software/shop-a-sketch |
| Quota | DeltaHacks 12 (2026) | First Place | "First linter for your budget": real-time cloud and API cost intelligence in your IDE | VS Code ext, tree-sitter, LangChain, Gemini, Next.js, MongoDB | https://github.com/dwseoh/Quota | https://devpost.com/software/quota-fg4pzi |
| deltawash | DeltaHacks 12 (2026) | Second Place | Camera rig that checks clinicians follow the full WHO handwashing procedure | Raspberry Pi, ESP8266, PiCam, PyTorch, TensorFlow, React | https://github.com/Goldenstar2660/DeltaWash | https://devpost.com/software/deltawash |
| ReelJobs | DeltaHacks 12 (2026) | Third Place | TikTok-style reels feed of job postings, with AI-generated video | React Native/Expo, Python, MongoDB Atlas, Gemini, Whisper, Vultr, Playwright | https://github.com/Scr4tch587/DeltaHacks12 | https://devpost.com/software/reeljobs |
| Orca | QHacks 2026 | First Place | Hum or describe a melody and an agent composes it into real music | Next.js, FastAPI, Gemini, ElevenLabs, Hugging Face, MCP | https://github.com/Beebdoles/qhacks-2026 | https://devpost.com/software/orca-4po0nm |
| Atlas | QHacks 2026 | Second Place | Pick any place and era, then explore an AI-generated 3D world with voice guidance | React, three.js, Globe.gl, World Labs, Gemini, Gradium, FastAPI, WebSockets | https://github.com/MatthewLones/QHacks-2026 | https://devpost.com/software/atlas-m8yot1 |
| SpeakCode | nwHacks 2026 | Finalist | Mock technical interviews that grade both your code and how you explain it out loud | Node.js, Passport.js | https://github.com/armanchinai/nwHacks2026 | https://devpost.com/software/speakcode-mxv98c |
| Rehabify | nwHacks 2026 | Finalist | AI physical-therapy coach with real-time form correction and voice | MediaPipe, Vapi, Deepgram, ElevenLabs, React, Neon, Vercel | https://github.com/obro79/Rehabify | https://devpost.com/software/rehabify-y2f5mu |
| Trojan | nwHacks 2026 | [1Password] Best Security Hack | Agentic security testing for vibe-coded apps before you ship | LangGraph, OpenAI, Next.js, Supabase, WebSockets | https://github.com/jkuo630/Trojan | https://devpost.com/software/trojan |
| Vril | Hack Western 12 (2025) | First Place Overall; [MLH] Best Use of Gemini | AI product-design studio: idea to 3D model of a physical product | Next.js, three.js, TRELLIS, Gemini, FastAPI, Redis, Docker | https://github.com/akuwuh/Vril | https://devpost.com/software/vril |
| FlowBoard | Hack Western 12 (2025) | Second Place Overall | Draw rough storyboard sketches on a canvas and turn them into video | tldraw, React, Vite, Gemini, Redis, Python | https://github.com/austinjiann/FlowBoard | https://devpost.com/software/flowboard-bdpqzg |
| komo | Hack Western 12 (2025) | Third Place Overall | Unified search across Slack, Notion and GitHub to find "that file" | Next.js, Express, SQLite, Gemini, Slack/Notion/GitHub APIs | https://github.com/aircon2/komo | https://devpost.com/software/komo-4lrjdg |
| TurretGuard | Hack the 6ix 2025 | 1st Place; Best Hardware Hack | AI turret that detects drowning in real time and launches an inflatable buoy | Raspberry Pi, Arduino, Edge Impulse, PyTorch, 3D printing | https://github.com/pekachoo/TurretGuard_hackthe6ix | https://devpost.com/software/turretguard |
| IntelliDrive | Hack the 6ix 2025 | 2nd Place | An LLM drives hardware from natural language via MCP, with no CV pipeline | QNX, MCP, Gemini, Flask, Next.js | https://github.com/jindal013/intellisense | https://devpost.com/software/intelli-drive |
| hermes | Hack the 6ix 2025 | 3rd Place | Phone-calling agent that books reservations and haircuts and handles calls for you | Claude, OpenAI, Next.js, Python | — | https://devpost.com/software/hermes-vfeob3 |
| DUM-E | Hack the North 2025 | Finalist | Robotic arm that follows spoken commands, using CV and fast (Groq) inference | Raspberry Pi, Arduino, OpenCV, Groq, Python, C++ | https://github.com/pekachoo/htn-DUM-E | https://devpost.com/software/dum-e-kgx6at |
| Puppeteer | Hack the North 2025 | Finalist; Warp Best Developer Tool | LLM attaches runtime probes to your app and fakes data on the fly (for example, a missing backend) | Python, React, SQLite, Cohere, Gemini, Martian | https://github.com/BrianLi23/puppeteer | https://devpost.com/software/puppeteer-7429qv |
| PathSense | Hack the North 2024 | Finalist; Cohere Best Use of Cohere | Real-time voice guidance for blind users navigating indoors | YOLO, Detectron2, Mappedin, Cohere, Groq, Whisper, Convex, React | https://github.com/akjadhav/hackthenorth-2024 | https://devpost.com/software/pathsense-athy2r |

## 3. Patterns

**1. Physical builds win podiums.** Of 61 top-tier winners from the 2023–2025 events (finalists and 1st–3rd places), 15 list hardware tags (Arduino, Raspberry Pi, ESP32, servos, EMG). The 2026 events lean even harder that way:
- Hack the 6ix 2026's entire podium is hardware or embedded: Praxis, TraceLoop and MIRL.
- So is the Hack the 6ix 2025 podium: TurretGuard and IntelliDrive.
- DeltaHacks 12's runner-up was deltawash.
- HTN finalists include DUM-E, Reflex and Keymaeleon.
- The same builder (GitHub `pekachoo`) won HT6 2025 1st with TurretGuard and made HTN 2025 finalist with DUM-E. Judges reward a live, physical "it moves" demo.

**2. An AI agent that acts in the world beats a chatbot.**
- hermes places real phone calls.
- IntelliDrive lets an LLM drive hardware over MCP.
- Reflex has AI write robot skills.
- Settlers of Solana runs an agent economy.
- Trojan attacks your app to find security holes.
- Identity Matrix's avatars keep acting after you log off.
- MCP shows up in 2025–26 winners (IntelliDrive, Orca, Reflex).

**3. Developer tools take overall prizes, not just the Warp track.** Quota (DeltaHacks 1st) is an IDE cost linter. TraceLoop (HT6 2nd) is "Cursor for firmware." Puppeteer (HTN finalist plus Warp) probes a running app. komo (Hack Western 3rd) searches workplace tools. Students judging students relate to their own pain. "X for Y" pitches ("Cursor for firmware," "linter for your budget," "Cursor for City Planning" from DeltaHacks' Cision) are common.

**4. Generative 3D, world and video is the 2025–26 "wow."** Orbis Engine (4D Gaussian splats from footage), Atlas (World Labs 3D worlds), Vril (TRELLIS product models), FlowBoard (sketch to video), CADEX (text to CAD) and Project Horizon (third-person to first-person video) all won.

**5. Theme fit decides events that have a theme.**
- UofTHacks 13's theme was identity, and all three podium projects pitch on it. Identity Matrix ("upload your identity") also took Best "UofT" Hack, Project Horizon says it "explores identity through perspective," and Shop-A-Sketch's pitch is "who you are."
- QHacks 2026's theme was "The Golden Age": Orca opens with "the golden age of creation," and the City of Kingston track paid three teams.

**6. Prize stacking is normal.** Many top winners also took a sponsor prize:
- Vril: 1st plus MLH Gemini.
- TurretGuard: 1st plus Best Hardware.
- Praxis: 1st plus QNX.
- Project Horizon: 2nd plus Backboard plus TwelveLabs.
- PathSense: finalist plus Cohere.

Sponsor prizes are often split across 3–6 teams (HTN 2023 "Best Use of Cohere" had three winners; nwHacks 2025 Aquareum had six), so they're high-odds add-ons.

**7. Stack frequency across 222 parsed winners (the 11 events before 2026 summer/fall):** Python leads, then React, TypeScript, Gemini, Node, FastAPI/Flask, Next.js, ElevenLabs, OpenAI, MongoDB and Cohere. Gemini is the most common LLM tag, ahead of OpenAI. Health and accessibility recur among finalists: PathSense, Rehabify, Praxis, deltawash, nwHacks 2025's Braillearn and HTN 2024's PulseGrip.

**Takeaways for our Knight Hacks project**
1. Build something with a live physical or real-world action, such as a robot, a sensor rig, a phone call or an agent that does a task. Demo it working on stage rather than describing it.
2. If Knight Hacks announces a theme, put it in the project name and the first line of the pitch, the way UofTHacks and QHacks winners did.
3. Design for prize stacking from hour 0: one overall-worthy core, plus Gemini/ElevenLabs/MongoDB (MLH) and the one sponsor API that fits naturally.
4. A sharp "X for Y" developer tool (IDE extension, CLI, firmware agent) is a proven overall winner with student judges and needs no hardware risk.
5. For visual wow, generative 3D or video (World Labs, TRELLIS, Gaussian splats) is the current frontier among winners.

## 4. Open questions / next searches

- **Galleries that returned 404:** uofthacks-12 (UofTHacks 12, 2025), deltahacks-9, deltahacks11, hack-western-11/hackwestern11, mchacks-10/mchacks-13 (the working slugs are `mchacks10` and `mchacks13`). UofTHacks 12 and Hack Western 11 need the right slug, so search Devpost.
- **Project pages that failed or parsed without prizes:** HTN 2026 Composition, Combadge, Concerto and Sham; HT6 2026 Claude Whip 9000, Buzzkill, Check-in Champions and Constant.; McHacks 13 Care Compass, Consensus Capital and Bloomscroll (likely McHacks 13 3rd place, but unconfirmed; the page came back truncated). Re-fetch these.
- **Pages beyond page 1:** HTN 2026 and HT6 2026 each showed 24 winners on page 1, so more may be on `?page=2`.
- **Hack the North doesn't rank finalists on Devpost.** Check HTN closing-ceremony posts for the grand-prize pick.
- **Leads once sponsor tracks drop:**
  - QNX prizes (HT6 2025/2026, HTN 2026) reward embedded and AI work: https://hackthe6ix2026.devpost.com/project-gallery
  - Warp "Best Developer Tool" appears at HTN, HT6, nwHacks and Hack Western.
  - Shopify "Hack Shopping with AI" appears at HTN 2026 and UofTHacks 13.
  - RBC "Signal in the Noise" (HTN 2026) and National Bank trading tracks (McHacks) are fintech leads.
  - Galleries not yet parsed for 2023–24 prize detail: https://uofthacks-11.devpost.com/project-gallery, https://deltahacks-x.devpost.com/project-gallery, https://nwhacks-2024.devpost.com/project-gallery
