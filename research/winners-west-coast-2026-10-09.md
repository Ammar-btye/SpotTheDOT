# Winners: West Coast collegiate hackathons (LA Hacks, Hacktech, SB Hacks, HackDavis, Citrus Hack, DiamondHacks, HackSC)
_Researched 2026-10-09 · sources: Devpost project galleries and project pages (winner badges and prize lists), Devpost hackathon search API_

## 1. Scope
**Method.** WebFetch returned 403 on Devpost, so I pulled the gallery pages with curl. From each gallery I kept the projects that carry the `class="winner"` badge, then parsed every winning project page for its prize list, "Built With" tags and "Try it out" links. That covers **435 badge-confirmed winning projects across 25 galleries**. The table below is a 30-project selection, mostly overall and grand-prize winners plus notable sponsor and track wins. The stack statistics in section 3 cover all 435.

**Galleries visited (all at `<url>project-gallery`):**
- LA Hacks: https://la-hacks-2023.devpost.com/ , https://la-hacks-2024.devpost.com/ , https://la-hacks-2025.devpost.com/ , https://la-hacks-2026.devpost.com/
- Hacktech (Caltech): https://hacktech-2023.devpost.com/ , https://hacktech2024.devpost.com/ , https://hacktech2025.devpost.com/ , https://hacktech-by-caltech-2026.devpost.com/
- SB Hacks (UCSB): https://sb-hacks-ix.devpost.com/ (2023), https://sb-hacks-x.devpost.com/ (2024), https://sb-hacks-xi.devpost.com/ (2025), https://sb-hacks-xii.devpost.com/ (2026)
- HackDavis: https://hackdavis2023.devpost.com/ , https://hackdavis-2024.devpost.com/ , https://hackdavis-2025.devpost.com/ , https://hackdavis-2026.devpost.com/
- Citrus Hack (UCR): https://citrus-hack-2023.devpost.com/ , https://citrus-hack-2025.devpost.com/ , https://citrus-hack-2026.devpost.com/
- DiamondHacks (UCSD): https://diamondhacks-2024.devpost.com/ , https://diamondhacks-2025.devpost.com/ , https://diamondhacks-2026.devpost.com/ (https://diamondhacks2024.devpost.com/ is a second 2024 listing with no winners)
- HackSC (USC): https://hacksc-2023.devpost.com/ , https://hackscx.devpost.com/ (Nov 2023)

**Skipped:** Cal Hacks and TreeHacks (another agent covers them). Also skipped: SD Hacks, whose last Devpost event was 2022 (out of range), Citrus Hack 2024 (no Devpost event found) and the online 2025 "HackSC x Lovable" event. I also left out same-name projects other agents already logged ("Mira" at TreeHacks, "Lumos AI" at Hacklytics). The projects below are different ones with those names.

## 2. Winners table
| Name | Hackathon | Prize/track | What it does | Stack | Repo | Source URL |
|---|---|---|---|---|---|---|
| codebreaker | LA Hacks 2026 | 1st Overall; Cognition Company Challenge | AI-native security agents that detect, validate and fix vulnerabilities, with their own benchmark | Devin, Modal, Cloudflare, React, TypeScript | https://github.com/KevinWu098/codebreaker | https://devpost.com/software/codebreaker-la |
| RIIS | LA Hacks 2026 | 2nd Overall; Fetch.ai Best Use of ASI:One | Robot that enters collapsed buildings, finds survivors, and gives remote medics eyes and voice (Gaussian-splat VR reconstruction) | Raspberry Pi, PyTorch, FastAPI, Fetch.ai, React | https://github.com/srinisriram/RIIS | https://devpost.com/software/riis |
| Autopsy | LA Hacks 2026 | 3rd Overall; Cognition Company Challenge | Records an AI coding agent's actions, graphs why its failures happened and feeds the lessons into its next attempt | Claude, Codex, Devin, Gemma, pgvector, FastAPI, Next.js, Cloudflare | https://github.com/balebbae/Autopsy | https://devpost.com/software/autopsy-zq5d84 |
| Polaris | LA Hacks 2026 | Best Social Impact Hack | Agentic hospital paging system for critical patient care | Fetch.ai ASI:One, FastAPI, Next.js, AWS, shadcn/ui | https://github.com/angelinawwu/lahacks26 | https://devpost.com/software/polaris-mh7rd8 |
| NeighborFridge | LA Hacks 2026 | Figma Make Challenge; Best UI/UX | Tracks groceries from receipts, predicts when they expire and gamifies reducing waste | Figma Make, Django, React, AWS, SQLite | https://www.github.com/sinaghadimi9081/LaHacks2026 | https://devpost.com/software/neighborfridge |
| Alto | LA Hacks 2025 | Overall 1st; Fetch.ai AI Agents League | Agents that find, fix and deploy mobile bug fixes on their own | Fetch.ai uAgents, ASI-1, Gemini, Instabug, Maestro, React Native, Slack | https://github.com/NLNHSR/AgentAlto | https://devpost.com/software/alto |
| Lumos | LA Hacks 2025 | Overall 2nd; Fetch.ai AI Agents League | AI glasses (Snap Spectacles) that help Alzheimer's patients recognize loved ones and follow routines | Snap Spectacles, Fetch.ai, DAIN, Melissa, MongoDB, React Native | https://github.com/pb2323/Lumos | https://devpost.com/software/lumos-f8h0mn |
| MarkedDown | LA Hacks 2024 | First Place | Multi-factor digital watermarking that proves image ownership and catches copyright infringement | SvelteKit, Python, Gemini, Fetch.ai | https://github.com/kushhansagarwal/markeddown/tree/cdn | https://devpost.com/software/markeddown |
| FormFixer | LA Hacks 2024 | Second Place | Computer-vision coach that checks your gym form one rep at a time | YOLO, Flask, React Native/Expo, Docker | https://github.com/theamandawang/FormFixer | https://devpost.com/software/formfixer-a7txz8 |
| Soundscape | LA Hacks 2024 | Third Place; Intel Company Challenge | Real-time generative music landscapes based on where you are | Flutter, Vertex AI, Hugging Face, Intel, Modal, MongoDB, Fetch.ai | https://github.com/matth101/lahacks24 | https://devpost.com/software/soundscape-u19mo7 |
| DataGuardian | LA Hacks 2023 | First Place | Legal agent that files data-privacy rights requests for you | OpenAI, Cohere, Flask, React, Chrome extension | https://github.com/tonyjiang02/DataGuardian-Frontend | https://devpost.com/software/dataguardian |
| SkyNet | Hacktech 2026 | Best Creativity; Ironsite Cash Prize; Palohouse hacker-house stay + $20k SAFE | Model that predicts where humans look in a scene, trained on a hand-labeled gaze dataset | Python, PyTorch | https://github.com/Lasereyepop/hacktech26 | https://devpost.com/software/skynet-a461oz |
| Recruitt | Hacktech 2026 | YC Interview; Sideshift Cash Prize + Interview | AI agents that fill out job applications for you "without making stuff up" | TypeScript | — | https://devpost.com/software/recruit-h3lc2r |
| Renaissance Research | Hacktech 2025 | Best Finance Project; Best Use of AI | Scrapes overlooked papers and theses and judges whether their ideas would work today | AWS Bedrock, Gemini, Next.js, BeautifulSoup | https://github.com/anshll/renaissance-research | https://devpost.com/software/renaissance-research |
| Memento | Hacktech 2025 | Best Health Project | Multimodal agent on AR glasses (Aria) that guides dementia patients through their day | Aria glasses, Llama/Together AI, OpenAI, Flutter, Firestore | — | https://devpost.com/software/memento-cxntj0 |
| Hey Host! | SB Hacks XII (2026) | Grand Prize 1st | Wake word ("Hey Host!") lets you ask a podcast questions and hear answers in the host's style of voice | ElevenLabs, Whisper, Porcupine, Python, TypeScript | https://github.com/nacsoprog/HeyHost | https://devpost.com/software/hey-host |
| Lumenta | SB Hacks XII (2026) | Grand Prize 2nd | Multi-camera video monitoring that detects incidents and acts on them | YOLOv8, ONNX, Gemini, MCP, Next.js | https://github.com/BhargavJakkaraju/Lumenta | https://devpost.com/software/lumenta |
| Barracua | SB Hacks XII (2026) | Grand Prize 3rd | Voice-driven browser agent that helps blind people use the web | Playwright, Deepgram, Gemini, Chrome extension | https://github.com/ryunzz/sb_hacks | https://devpost.com/software/baracua |
| SnapSell | SB Hacks XI (2025) | Grand Prize 1st | Automates resale from photo to listing to pickup in one workflow | Claude, Gemini, Selenium, Flask, Supabase | https://github.com/CollinQ/sbhacks2025 | https://devpost.com/software/snapsell |
| Hey, Chef! | SB Hacks XI (2025) | Grand Prize 2nd | Conversational voice cooking assistant | LiveKit, Deepgram, OpenAI, Perplexity, SingleStore | https://github.com/laurelin60/hey-chef | https://devpost.com/software/hey-chef |
| Agentic | SB Hacks X (2024) | Grand Prize | Turns natural language into browser actions, built for accessibility | Next.js, Selenium, Prisma, Kinde | https://github.com/laurelin60/Agentic | https://devpost.com/software/agentic |
| SODIUM | DiamondHacks 2026 | 1st Overall | Voice-first "Jarvis for seniors" with a browser agent for web tasks and a caregiver dashboard | LangChain, Svelte, Python, TypeScript | — | https://devpost.com/software/sodium |
| MedSurge AI | DiamondHacks 2026 | 2nd Overall | Upload a diagnosis and get drug and surgery prices, a travel plan and calendar bookings automatically | Browser Use, Composio, Groq, GCP, Google Calendar/Places | https://github.com/d3pant/diamond-hacks | https://devpost.com/software/medsurge-ai |
| Scamurai | DiamondHacks 2025 | 1st Overall | Chrome extension that flags scam texts and emails | Gemini, Flask, React, Chrome extension | https://github.com/AryenSinghal/Scamurai | https://devpost.com/software/scamurai-a5ng7f |
| Travel Safe | DiamondHacks 2024 | 1st Overall | Real-time mixed-reality safety overlay for travelers | Unity, VR, YOLO, WebSockets, Python | https://github.com/laurelin60/diamondhacks | https://devpost.com/software/travel-safe |
| Mira | Citrus Hack 2026 | Best Overall 1st | Companion robot that detects distress or falls in dementia patients and alerts caregivers | Arduino, Claude, Gemini, Python | — | https://devpost.com/software/mira-dementia-robot-companion |
| Scenetic | Citrus Hack 2025 | 1st Place | Mobile tool that helps cinematographers find the best shot quickly | OpenCV, PyTorch, Gemini, React Native/Expo, Firebase | https://github.com/bradwco/Scenetic. | https://devpost.com/software/scenatic |
| BrailleOut | HackDavis 2026 | Best Hack for Social Good; Best Use of DAC Materials | Low-cost device that scans any text and outputs physical Braille | Arduino, C++, OpenCV, Gemini, Anthropic | https://github.com/varunpalanisamy/Braille | https://devpost.com/software/brailleout |
| Aggie Street Smart | HackDavis 2026 | Best Hack for Social Good; Best Use of DAC Materials | Bike-safety routing for Davis ("bike safer, not speedier") | Gemini, Mapbox, Next.js | https://github.com/TheLickIn13Keys/hackdavis26 | https://devpost.com/software/aggie-street-smart |
| WakeMate | HackDavis 2025 | Best Hack for Social Good | Real-time driver-drowsiness detection with voice alerts to keep the driver awake | OpenCV, dlib, PyTorch, Gemini, ElevenLabs, Flask | https://github.com/Michaelhamaty/WakeMate | https://devpost.com/software/wakemate |

## 3. Patterns
**Stack frequency across all 435 winners.** Python 230, React 160, TypeScript 130, **Gemini 108 (about 25%)**, Node 68, Flask 67, FastAPI 64, Next.js 89 (two tag spellings combined), MongoDB 54, OpenCV 32, ElevenLabs 31, OpenAI 30, Claude 26, Fetch.ai 23 (plus 13 Agentverse), Arduino 23. Within prize names, Fetch.ai appears in 14 and Gemini/Google in 22, followed by MongoDB, Auth0, Vultr, Solana, .Tech and ElevenLabs (MLH staples).

1. **Agents that take real actions beat chatbots.** Overall winners from 2024 to 2026 nearly all close a loop: Alto ships the bug fix, SnapSell posts the listing, MedSurge AI books the calendar, Barracua and Agentic drive the browser, Recruitt submits the application, DataGuardian files the legal request. Browser automation (Selenium, Playwright, Browser Use) is a recurring enabler.
2. **Agents for developers won LA Hacks 2026.** 1st place (codebreaker) and 3rd place (Autopsy) were both tools for AI coding agents and both also won the Cognition (Devin) challenge. Alto (LA Hacks 2025, 1st) is the same genre. codebreaker shipped its own benchmark, and judges rewarded that kind of evaluation rigor.
3. **Care for vulnerable people is the top theme.** Dementia and elderly care appears in Lumos, Memento, SODIUM and Mira; blind users in Barracua and BrailleOut; drivers and cyclists in WakeMate and Aggie Street Smart; scam victims in Scamurai; hospitals in Polaris and RIIS. HackDavis awards are organized entirely around social good and named local nonprofits (NAMI Yolo, Fourth and Hope, Wellspring), so builds for a real local organization pay off.
4. **Physical and multimodal demos win overall placements.** Winners used AR or smart glasses (Lumos, Memento), robots (RIIS, Mira), Arduino Braille output (BrailleOut), mixed reality (Travel Safe) and live camera computer vision (FormFixer, Lumenta, WakeMate). Hardware and live CV make the demo memorable.
5. **Voice is the default interface in 2025–26.** Hey Host!, Hey, Chef!, SODIUM, Barracua and WakeMate all use voice (ElevenLabs, Deepgram, LiveKit, Whisper, Porcupine wake word).
6. **Sponsor stacking is normal.** Winners collect an overall prize plus a sponsor prize: Alto and Lumos won Fetch.ai, codebreaker and Autopsy won Cognition, Soundscape won Intel, and SkyNet won three Hacktech prizes including a $20k SAFE. LA Hacks 2026 even had a "High Quality Sponsormaxxing" award (Nimbus). Fetch.ai sponsored the agent track at LA Hacks 2024, 2025 and 2026 and at DiamondHacks 2025 and 2026.
7. **Repeat winners show that execution compounds.** GitHub user `laurelin60` won SB Hacks X (Agentic, Grand Prize), DiamondHacks 2024 (Travel Safe, 1st) and SB Hacks XI (Hey, Chef!, 2nd). Polished, focused demos keep winning.

**Takeaways for our Knight Hacks project**
1. Build an agent that finishes a real task end to end (submit, book, fix, file), and show that action live on stage instead of a chat window.
2. Choose a specific vulnerable user (seniors, blind users, patients, scam targets) and give the demo a tangible piece: a camera, glasses, a small Arduino build or voice.
3. Plan from the start to stack the main track with one or two sponsor prizes: Gemini (used by a quarter of winners), an agent platform like Fetch.ai if offered, and MLH's ElevenLabs, MongoDB or .Tech add-ons.
4. If we build developer or AI tooling, add a small benchmark or evaluation (as codebreaker did) so the impact is measurable.
5. Use voice as the interface (ElevenLabs or Deepgram plus a wake word); it is cheap to add and shows well in demos.

## 4. Open questions / next searches
- WebFetch returns 403 for Devpost, so all verification here came from curl'd HTML. Two LA Hacks 2026 projects matched my first, loose gallery filter but list no prize on their project pages: Superblock (https://devpost.com/software/a-decentralized-urban-nervous-system) and Karuna (https://devpost.com/software/winner-jcq1td). I excluded both.
- I found no Devpost gallery for Citrus Hack 2024 or SD Hacks after 2022. UCSD's spring event now runs as DiamondHacks.
- Full prize lists per event (around 400 more confirmed winners) can be re-derived from the galleries above. LA Hacks 2026 alone has 67 winners across Cognition, Figma Make, Cloudinary, Zetic, Arista, ROBLOX, World and ASUS challenges: https://la-hacks-2026.devpost.com/project-gallery
- Deep dives to do once Knight Hacks sponsors are known:
  - Fetch.ai agent-track winners: https://la-hacks-2025.devpost.com/project-gallery and https://diamondhacks-2026.devpost.com/project-gallery (AgenticHire, Kaimon, Boomer Browse).
  - TwelveLabs and Deepgram API challenge winners at SB Hacks XII: https://sb-hacks-xii.devpost.com/project-gallery
  - Hacktech 2026 YC, Sideshift and Lovable winners: https://hacktech-by-caltech-2026.devpost.com/project-gallery
  - HackDavis nonprofit-partner prizes as a model for local-impact tracks: https://hackdavis-2025.devpost.com/project-gallery
