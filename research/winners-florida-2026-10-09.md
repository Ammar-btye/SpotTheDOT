# Winners: Florida hackathons (ShellHacks, SwampHacks, HackUSF, Hackabull), 2023–2026

_Researched 2026-10-09 · sources: Devpost galleries and project pages for ShellHacks 2023–2026, SwampHacks IX/X/XI/XII, HackUSF 2025/2026 and Hackabull 2023/2025. Every win below was confirmed by the "Winner" label on the project's Devpost page._

## 1. Scope

**Galleries scraped.** I pulled every project with a Winner badge, then read each project page for its prize names, "Built With" tags and "Try it out" links.
- ShellHacks (FIU): https://shellhacks-2026.devpost.com (Sep 25–27, 2026, 29 winners) · https://shellhacks2025.devpost.com (29) · https://shellhacks2024.devpost.com (41) · https://shellhacks-2023.devpost.com (38) · https://shellhacks2022.devpost.com (31; not used in the table)
- SwampHacks (UF): https://swamphacks-xi.devpost.com (Jan 2026, 22) · https://swamphacksx.devpost.com (Jan 2025, 13) · https://swamphacks-ix.devpost.com (Jan 2023, 8) · https://swamphacks-xii.devpost.com (**Oct 16–18, 2026, still to come**; prize list only)
- HackUSF (GDG at USF): https://hackusf-2026.devpost.com (Mar 2026, 16) · https://hackusf.devpost.com (Apr 2025, 8)
- Hackabull (USF SHPE): https://hackabull-2025.devpost.com (10) · https://hackabull-2023.devpost.com (12) · https://hackabull-2022.devpost.com (7; not used)

**Skipped.** The only Devpost page for MangoHacks is the 2019 event at https://mangohacks.devpost.com, which is outside the date range. I couldn't find a Devpost page for HackFSU or HackMiami (see §4). Five ShellHacks 2026 winners of MLH-only prizes were left out because `winners-mlh-sponsor-prizes` already logs them: Public City Announcements, Clarity, transPEAKtation, MomentumX and Hurricane Week. The other 2026 MLH and AWS winners (T-Cell, Grep, Shaadiest, Budgie On A Budget) are confirmed in the gallery but not logged here.

**About ShellHacks 2025/2026 placings.** Devpost groups first through third place into a single prize called "1st, 2nd, & 3rd Best Overall", so the exact placing isn't public.

## 2. Winners table

| Name | Hackathon | Prize/track | What it does | Stack | Repo | Source URL |
|---|---|---|---|---|---|---|
| Pointr | ShellHacks 2026 | Best Overall (top 3) | AI overlay in Chrome that walks users through tasks in the browser, step by step | Chrome MV3, Amazon Bedrock/Nova, Claude, Gemini, Whisper, React | https://github.com/edwin-luu/pointr | https://devpost.com/software/pointr-0ce2gh |
| Paradise | ShellHacks 2026 | Best Overall (top 3) | Haptic and voice navigation guidance ("Feel the guidance") using on-device vision | Grounding-DINO, Depth-Anything-v2, CLIP, YOLOv10, transformers.js/WebGPU, Joy-Con WebHID, OSRM, Gemini | https://github.com/Akhileshreddym/Paradise | https://devpost.com/software/paradise-n0i7of |
| Clench | ShellHacks 2026 | Best Overall (top 3) | Turns muscle and EEG signals plus gaze into speech, messages and browsing for ALS users | Muse 2, BrainFlow, MNE, EyeDid SDK, Gemini, ElevenLabs, Twilio, Kotlin/Android | https://github.com/abhay-dronavalli/clench-muse-als | https://devpost.com/software/clench-ifdrmc |
| Common Ground | ShellHacks 2026 | Sperry Tech ($5k track) | Cross-utility platform that finds overlapping construction plans and optimizes fleet routes | three.js, MongoDB Atlas, Python, multi-LLM (Claude/Gemini/GPT) | https://github.com/fradicus/Shellhacks-2026 | https://devpost.com/software/common-ground-a6rfoc |
| UtiliTies | ShellHacks 2026 | Sperry Tech | AI agents read utilities' public filings, map planned projects and flag overlaps between neighbors | FastAPI, Next.js, MapLibre, Overpass/OSM, TimescaleDB, Claude, Gemini | — | https://devpost.com/software/utilities-utility-coordination |
| Halo | ShellHacks 2026 | Waymo; State Farm | Smart-helmet safety system ("Protection beyond the helmet") | Arduino, Raspberry Pi 5, OpenCV, Google ADK, Swift | https://github.com/billpquach/halo | https://devpost.com/software/halo-1q59hf |
| Mind Your Prompt | ShellHacks 2026 | Assurant | Browser extension that spots and masks private data before you send it to an AI | BERT on ONNX/transformers.js, WXT, Next.js, Snowflake Cortex | https://github.com/krishnatejasai/ShellHacks_2026 | https://devpost.com/software/mind-your-prompt-prompt-shield |
| CADVision | ShellHacks 2026 | Microsoft | Brings SolidWorks assemblies into 3D/VR with an AI assistant for design review | Unity, C#, Meta Quest, Gemini, ElevenLabs | https://github.com/BAAA-Hacks/cad-vision | https://devpost.com/software/cadvision |
| benchlog | ShellHacks 2026 | INIT National | Version control for hardware benches, using CV snapshots of builds | ESP32, OpenCV/ArUco, FastAPI, React, Typer CLI | https://github.com/Jrodd1203/benchlog | https://devpost.com/software/benchlog |
| PortfolioFit | ShellHacks 2026 | Blackstone | Chat with your portfolio to understand holdings and find new investments | Next.js, Finnhub, FRED, Yahoo Finance, OpenAI, ElevenLabs | — | https://devpost.com/software/portfoliofit |
| A.N.R (Agentic Nuclear Reactor) | HackUSF 2026 | Best Overall 1st; Google Cloud ADK | Self-healing multi-agent controller for a (demo) reactor, driving hardware over serial | Google ADK, Gemini, FastAPI, pyserial, React | https://github.com/morallyearlgrey/demo-fusion-reactor | https://devpost.com/software/regenerative-agentic-nuclear-reactor |
| Recall | HackUSF 2026 | Best Overall 2nd | AI smart glasses that log memories passively and answer questions, for people with cognitive impairment | ESP32, YOLOv8, ChromaDB, Gemini, ElevenLabs, Next.js | https://github.com/sebastian-noel/Recall | https://devpost.com/software/recall-oswlh3 |
| Guido | HackUSF 2026 | Most Innovative Hack | Assistive navigation robot/guide | Jetson, LiDAR, ROS 2, Arduino, Google ADK, ElevenLabs, Vosk | https://github.com/kwaiidev/guido/ | https://devpost.com/software/guido-k7f5ei |
| T.I.T.A.N. | HackUSF 2026 | Google Cloud ADK | Parallel AI agents for Tampa flood and road emergencies, with a self-correcting QA loop | Google ADK, MCP, GCP, Python, TypeScript | — | https://devpost.com/software/t-i-t-a-n-tampa-intelligent-threat-analysis-network |
| Use Protechtion | HackUSF 2026 | NextEra Energy malware challenge | Upload a malware sample and get automated sandboxed AI analysis | E2B sandbox, Docker, VirusTotal, Claude, Gemini, FastAPI, Next.js | https://github.com/KushagraKatiyar06/useprotech.tion | https://devpost.com/software/use-protech-tion |
| ReStory | SwampHacks XI (2026) | Best Overall (Vobile, top 3) | Wearable that links faces and voices to identities for people with Alzheimer's | Raspberry Pi 5, WhisperX, SpeechBrain, ChromaDB, OpenCV, Gemini | https://github.com/retromonos/SwampHacks11FIH | https://devpost.com/software/restory |
| SignHero | SwampHacks XI | Best Overall (top 3); Best Game Design | Rhythm game for learning ASL | MediaPipe, OpenCV, Next.js (T3), MongoDB | https://github.com/MsMarion/ASL-Fun-Training | https://devpost.com/software/signhero |
| OffTrails | SwampHacks XI | Best Overall (top 3) | Off-trail pathfinding over USGS elevation, vegetation and water data | Python, rasterio, Leaflet, OSM | https://github.com/blohse8/OffTrails | https://devpost.com/software/offtrails |
| CaseForwardAI | SwampHacks XI | Morgan & Morgan "Tender for Lawyers" | AI round-table orchestrator that triages emails, uploads and transcripts into legal next steps | Next.js, Gemini, MongoDB, Auth0, Cloudflare | https://github.com/kofki/CaseForwardAI | https://devpost.com/software/caseforwardai |
| Pay Pals | SwampHacks XI | Best Finance Hack (Capital One) | Social savings goals with friends | FastAPI, Capital One Nessie, Gemini, MongoDB, Solana | https://github.com/GridGxly/PayPals | https://devpost.com/software/project-c1nomzfei7a0 |
| Pocket Money | SwampHacks XI | Hidden: "Least Vibecoded Project" (CISE professor) | Savings app, rewarded for clean, maintainable code | React Native, Supabase, Gemini, UPCitemdb | https://github.com/anduytran/pocketmoney | https://devpost.com/software/pocket-money-bhrtio |
| Lumi Lens | ShellHacks 2025 | Best Overall (top 3) | Gamified social and reading support for neurodivergent users on a Pi camera | Raspberry Pi, DeepFace, Gemini, Swift | https://github.com/jennixi/LumiLens.git | https://devpost.com/software/magical-girl-os |
| FloodGuard | ShellHacks 2025 | Best Overall (top 3) | AI agents predict and detect floods and coordinate the response | Google ADK + A2A, Gemini, Neon Postgres, Prisma, React | https://github.com/heyubaidullah/floodguard | https://devpost.com/software/floodguard-okgzty |
| EcoSort | ShellHacks 2025 | Best Overall (top 3); Wix/Base44 | Sustainability and recycling-sorting helper, built on Base44 with a Wokwi hardware sim | Base44, JavaScript, Wokwi | https://github.com/base44dev/eco-sort-1ff5770b.git | https://devpost.com/software/ecosort-ofyuie |
| VL-ADK | ShellHacks 2025 | Waymo; NVIDIA; Microsoft | "Pseudo" vision-language-action driving model built from a fleet of ADK agents | Jetson Orin, YOLO, Google ADK, Gemini, React | — | https://devpost.com/software/vl-adk |
| Agent Zero | ShellHacks 2025 | Capital One | Multi-agent accounts-payable pipeline that catches false and duplicate invoices | Gemini, BigQuery, FastAPI, TensorFlow, React | http://github.com/BonelessWater/shellHacks_1 | https://devpost.com/software/agentzero-tnh9p3 |
| Rubbish | SwampHacks X (2025) | 1st Overall | Smart bin that classifies items to prevent contaminated recycling | Arduino, YOLOv11, OpenCV, Flask, Flutter | https://github.com/AsztiC/rubbish | https://devpost.com/software/rubbish-bx5tai |
| Atmosphere | SwampHacks X | 2nd Overall | Environmental and UV exposure insights on a map | Next.js, Gemini, Google Maps, OpenUV, TensorFlow | https://github.com/maxrross/atmosphere | https://devpost.com/software/atmosphere-jd583o |
| ESPER | ShellHacks 2024 | Best Overall (1st); Assurant | Extension that smooths flashing video brightness to prevent epileptic seizures | Chrome ext, Java/Vert.x, Snowflake Snowpark, Streamlit, DigitalOcean | https://github.com/LumaDevelopment/ESPER | https://devpost.com/software/esper-fy6xeh |
| ARSL | ShellHacks 2024 | Second Best Overall; Microsoft; Google | Learn ASL in AR with computer-vision hand tracking (custom hardware) | Unity, Meta XR, OpenCV, PyTorch, embedded C | https://github.com/AugustDruzgal/ShellHacks2024 | https://devpost.com/software/arsl-vr-asl-learning |

That makes 30 confirmed winners. Other notable confirmed winners not in the table: Diffusion Earth (ShellHacks 2024, 3rd Overall), Token Whale (Hackabull 2025, 1st), Chess 10 (ShellHacks 2023, Best Overall), Muscle Memory (Hackabull 2023, 1st), Stroke Shield / Lazy3D / Skin Scan (HackUSF 2025, Best Overall Hack).

## 3. Patterns

**The same sponsors come back every year.** These are the most likely Knight Hacks sponsors too.
- **Waymo:** ShellHacks 2023–2026, with the same prompt every year: "use publicly available data to create a hack that improves transportation". Winners: Halo, VL-ADK, BirdsEye, hurrycane.
- **Assurant:** ShellHacks 2023–2026. "The Assurant Way" asks for tech that eases life in a connected world. The 2026 prompt was about AI privacy, spending and tool choice (Mind Your Prompt).
- **State Farm:** ShellHacks 2023–2026. "Make insurance easy for students". The 2026 prompt was auto-claims prep.
- **Capital One:** ShellHacks 2023–2025, SwampHacks XI, and SwampHacks XII ("Best Use of Nessie", $1k).
- **Microsoft:** an "AI 4 Good" or accessibility/education prompt, usually rewarding XR (ARSL, CADVision).
- **Google / Google Cloud:** ShellHacks 2025 ($4k, the Autonomous AI Agent Challenge built on ADK/A2A) and HackUSF 2026 ($1,750, "Self-Healing World" multi-agent with ADK + A2A).
- **One-off but high-value:** Sperry Tech ($5k, utility-construction coordination), Blackstone ($1.4k, portfolio understanding), Morgan & Morgan ($1k, a legal intake "AI orchestrator"), NextEra (malware analysis), Vanguard (financial literacy for underrepresented communities, 2023–24), Wolfram ($7k pool), NVIDIA, Netflix, Wix/Base44.
- **Vobile** is SwampHacks' co-host for XI and XII, sponsoring the $2.5k overall prize.
- **MLH defaults** appear everywhere: Gemini, ElevenLabs, Snowflake, MongoDB Atlas, DigitalOcean, GoDaddy, Solana and Auth0.

**What wins overall.**
1. **Assistive or health hardware paired with AI.** This is the dominant grand-prize pattern: Clench (ALS, EEG), Paradise (navigation), Recall and ReStory (memory-aid wearables), Lumi Lens (neurodivergent), ARSL (ASL), ESPER (epilepsy), Guido (navigation robot). Seven of the twelve top-3 overall slots at ShellHacks 2025/2026, SwampHacks XI and HackUSF 2026 went to assistive, health or safety builds, most with a physical device or a deep CV/biosignal pipeline: Paradise, Clench, Lumi Lens, ReStory, SignHero, Recall, and VigilEyes (trucker-fatigue detection, HackUSF 2026 3rd).
2. **Florida-specific climate and resilience stories.** Floods and hurricanes keep winning: FloodGuard, T.I.T.A.N., hurrycane, Hurricane Week, and the Climate Teach-In "Living by the water" track at HackUSF 2026.
3. **Multi-agent "orchestrator" architectures.** These won every agent-themed sponsor prize: FloodGuard, VL-ADK, Agent Zero, A.N.R, T.I.T.A.N., CaseForwardAI. Google ADK + A2A is the de facto stack for Google prizes.
4. **Prize stacking.** Many winners took two or three prizes with one project: ESPER (Overall + Assurant), ARSL (Overall + Microsoft + Google), VL-ADK (Waymo + NVIDIA + Microsoft), A.N.R (Overall + Google Cloud), Halo (Waymo + State Farm).
5. **Stacks have grown deep.** 2026 winners list 15–25 Built With tags: on-device models (ONNX/transformers.js/WebGPU), several LLMs, ElevenLabs voice, and real public datasets (USGS, OSM, FRED, NOAA). Gemini appears in most 2025–26 winners, and ElevenLabs voice output is now near-standard.
6. **Judging criteria.** ShellHacks lists Completion, Originality and Design. SwampHacks XII lists Technical Execution, Innovation, Impact, Clarity of Pitch, Completion (a working prototype, not a concept), and Track Relevance, with sponsor challenges judged only by sponsor judges. SwampHacks XI's hidden "Least Vibecoded" prize, and GitHub's "Ship It" prize (which rewards real PRs and issues), show judges pushing back on AI-generated code dumps.

**Takeaways for our Knight Hacks project**
1. **Build one project that hits several prizes.** Target the overall prize plus one recurring sponsor (Waymo transportation, Assurant, State Farm or Capital One) plus two MLH defaults, such as Gemini plus ElevenLabs or Snowflake. One build with three prize hooks is how ESPER, VL-ADK and Halo won.
2. **Give the project a visible human stake and a physical demo.** An assistive wearable or sensor with a live CV or biosignal loop beats a pure web app for the grand prize at Florida events.
3. **If Google sponsors, use ADK + A2A with clearly separated agents and a self-check loop.** That is exactly how the 2025–26 prompts are written.
4. **Use real Florida public data** (floods, hurricanes, traffic, utilities) to strengthen both impact and Waymo-style "use public data" prompts.
5. **Keep the repo clean and the commit history real.** Judges are starting to reward this (Least Vibecoded, GitHub Ship It), and a working prototype counts for more than scope.

## 4. Open questions / next searches

- **HackFSU, HackMiami, Hack@UCF:** I found no Devpost galleries. hackfsu.devpost.com returned 403 and the year-suffixed slugs returned 404. Next step: check hackfsu.com and HackFSU's social accounts for results.
- **MangoHacks:** the last Devpost event was 2019 (https://mangohacks.devpost.com). It may have stopped or moved platforms.
- **Exact ShellHacks 2025/2026 placings (1st vs 2nd vs 3rd):** Devpost doesn't show them. Check ShellHacks/FIU recap posts (e.g., https://cec.fiu.edu/news-events, https://refreshmiami.com).
- **SwampHacks XII (Oct 16–18, 2026)** runs a week after this research and overlaps the Knight Hacks season. Its prizes are Vobile overall ($2.5k), Capital One Nessie ($1k), DeepSpace credits, AI/ML, Hardware, Entertainment, and a Hidden Challenge. Watch https://swamphacks-xii.devpost.com/project-gallery for winners and sponsor overlap.
- **Deep dives for when tracks drop:** the ShellHacks 2026 prize list, with full Sperry Tech, Blackstone, Assurant and Microsoft prompts (https://shellhacks-2026.devpost.com/), and the HackUSF 2026 Google ADK, Oracle and NextEra prompts (https://hackusf-2026.devpost.com/).
- **More confirmed winners not logged here:** Hackabull 2023 (https://hackabull-2023.devpost.com/project-gallery), HackUSF 2025 (https://hackusf.devpost.com/project-gallery), ShellHacks 2022 and 2023 sponsor winners such as Vanguard, Schonfeld and LexisNexis (https://shellhacks-2023.devpost.com/project-gallery).
