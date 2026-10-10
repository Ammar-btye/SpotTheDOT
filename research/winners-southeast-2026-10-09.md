# Winners: Southeast collegiate hackathons (GA, NC, TN), 2023–2026

_Researched 2026-10-09 · sources: Devpost galleries and project pages (each project page lists its prizes as "Winner" labels); Devpost hackathon search API used to find event slugs_

## 1. Scope

I scraped the Devpost galleries below, kept entries with a "Winner" badge, then opened each project page to confirm the prize name, the "Built With" tags and the "Try it out" links.

- HackGT 13: Seaside Market (Sep 25–27, 2026): https://hackgt13.devpost.com/project-gallery
- HackGT 12: Midnight at the Museum (2025): https://hackgt-12.devpost.com/project-gallery
- HackGT 11: Circus of Inventions (Sep 2024): https://hackgt-11-circus-of-invention.devpost.com/project-gallery
- HackGT X: Journal of Memories (2023): https://hackgt-x.devpost.com/project-gallery
- Hacklytics 2026: Golden Byte (Feb 2026): https://hacklytics-2026.devpost.com/project-gallery
- Hacklytics 2025: Jurassic Age (Feb 2025): https://hacklytics2025.devpost.com/project-gallery
- VandyHacks X, XI and XII (2023–2025): https://vandyhacks-xii.devpost.com/project-gallery, plus -xi and -x
- HackNC 2023, 2024 and 2025: https://hacknc-2025.devpost.com/project-gallery, plus -2024 and -2023
- Pearl Hacks 2024, 2025 and 2026: https://pearlhacks2026.devpost.com/project-gallery, plus 2025 and 2024
- UGAHacks X and 11 (2025–2026): https://ugahacks-11.devpost.com/project-gallery
- HackDuke: Code for Good 2023: https://hackduke2023.devpost.com/project-gallery

**Skipped:** Florida events (out of scope). I didn't log 2024–2025 winners from Pearl Hacks, VandyHacks XI/X, HackNC 2024/2023 or UGAHacks X. Their galleries do show winners, but I ran out of room, and they're listed in §4. Three MLH-prize winners from HackGT 12/13 (Hey Buddy, Rescu, Grindstone) are already in `winners-mlh-sponsor-prizes-2026-10-09.md`. The Guardian Angel in `winners-northeast-midatlantic` is a different project (HackNYU) from the UGAHacks project logged here.

## 2. Winners table

| Name | Hackathon | Prize/track | What it does | Stack | Repo | Source URL |
|---|---|---|---|---|---|---|
| Sky-C2 | HackGT 13 (2026) | Best Overall, 1st | AR heads-up display that identifies aircraft overhead from live ADS-B data | Python, FastAPI, TypeScript, Vite, Grok, adsb.lol | https://github.com/jaiden-lee/ar-plane-identifier | https://devpost.com/software/sky-c2 |
| FlyBy | HackGT 13 | Best Overall, 2nd | Search-and-rescue ground control that steers drones with a fly-brain (FlyVis) vision model | Python, FastAPI, Three.js, MongoDB Atlas, xAI API, WebSockets | https://github.com/monishramj/flyby | https://devpost.com/software/flyby-fdxcua |
| VIGIL | HackGT 13 | Best Overall, 3rd | Assistive eyewear for the visually impaired, paired with an autonomous DJI Tello scout drone | ESP32-CAM, Arduino Nano, YOLO11/YOLO-World, ToF sensors, 3D printing, OpenCV | https://github.com/parthm667/vigil | https://devpost.com/software/vigil-assistive-eeywear-with-an-autonomous-aerial-scout |
| Synesthesia | HackGT 13 | The Shipyard track, 1st | Shows sounds in AR for deaf and hard-of-hearing users | ESP32, RPi Pico, TF Lite (YAMNet), MediaPipe, Web Bluetooth, WebAssembly | https://github.com/RishabhK12/Synesthesia | https://devpost.com/software/synesthesia-b1p9r3 |
| Fourteenth Floor | HackGT 13 | Lighthouse Laboratory track, 1st | A 3D/WebXR "office" where you watch and manage AI agents | Three.js, WebXR, MCP, Codex, Node, Blender | https://github.com/Pudging/fourteenth-floor | https://devpost.com/software/fourteenth |
| TapChart | HackGT 13 | Aramco: A Marina's Mission, 1st | Stores a Parkinson's patient's motor baseline behind an NFC tap so responders don't mistake symptoms for a stroke | NFC, MediaPipe, OpenCV, scikit-learn, Supabase, Vercel, Claude | https://github.com/alana170/TapChart | https://devpost.com/software/tapchart |
| ATP – Accessible to Prescription | HackGT 13 | Impiricus HCP Engagement, 1st; Notability prize | AI voice agent that calls insurers to speed up prior authorizations | OpenAI, ElevenLabs | https://github.com/notvasub/ATP-Access-to-Prescription | https://devpost.com/software/atp |
| Dose | HackGT 12 (2025) | Best Overall, 1st | IoT pill bottle that weighs doses, with a web dashboard | ESP32, TAL220 load cell, 3D printing, Next.js, Supabase | https://github.com/dawsonp2003/HackGT12-Dose | https://devpost.com/software/dose-ebmo9z |
| RefNet | HackGT 12 | Best Overall, 2nd | Research-paper search with AI insights and citation graphs | Flask, React, D3.js, OpenAlex, Cedar | https://github.com/Shreyas765/RefNet | https://devpost.com/software/refnet-c04g9n |
| vibesB2B | HackGT 12 | Best Overall, 3rd | Reads the room on Zoom sales calls and pushes signals to the CRM and Slack | Electron, MediaPipe, OpenCV, Gemini, Mastra, Recall.ai, Attio | https://github.com/atoniolo76/vibeb2b | https://devpost.com/software/vibesb2b |
| Vertex A11y | HackGT 12 | Best Emerging (beginner), 1st | Chrome extension that audits website accessibility and suggests fixes | JavaScript, Node, Chrome, OpenAI | https://github.com/karandeol-26/vertex_A11y | https://devpost.com/software/vertex-a11y |
| VisionNav | HackGT 12 | The Curator's Cause (social good), 1st | iOS app that guides visually impaired users with sound | Swift, YOLO, Gemini, text-to-speech | https://github.com/jaeheonshim/VisionNav | https://devpost.com/software/vision-app |
| Atlas | HackGT 12 | Cedar: Best Use of CedarOS; Ergo: Best Mastra Agent | Shared memory across your AI tools, plus codebase visualization | Electron, Mastra, CedarOS, Composio, Gemini, OpenAI, Three.js | — | https://devpost.com/software/atlas-tlfpkz |
| Noma | HackGT 11 (2024) | Best Overall, 1st | Telemedicine with real-time 3D views to cut Mohs-surgery errors | Flask, React, Three.js, RAG, RunPod, AWS | https://github.com/Shrey1306/mona | https://devpost.com/software/noma-ug9qxn |
| Fight and Furious | HackGT 11 | Best Overall, 2nd | AI self-defense trainer using pose estimation | MediaPipe, OpenCV, FastAPI, React, Streamlit | https://github.com/maechen/HackGTFinal2024 | https://devpost.com/software/fight-and-furious |
| prompt+ | HackGT 11 | Best Overall, 3rd | Improves LLM prompts and makes them more token-efficient | Flask, React, LangChain, OpenAI, spaCy, tiktoken, Firebase | https://github.com/promptplusGT/promptplus | https://devpost.com/software/prompt-sf7drq |
| OncoAI | HackGT 11 | Carnival for a Cause, 1st | Multimodal cancer diagnostics combining scRNA-seq, mammograms, blood tests and pathology slides, with an LLM layer | PyTorch, TensorFlow, Next.js, Postgres, Groq, Gemini, Mistral | https://github.com/kevinw93/hackgt12 | https://devpost.com/software/oncoai |
| ScribeAI | HackGT X (2023) | Best Overall | OCR and AI turn paper medical documents into HIPAA-minded electronic health records | Spring/Java, Next.js, Tesseract, OpenAI, Postgres, Docker, Kubernetes | https://github.com/michaelhyi/scribeai | https://devpost.com/software/scribeai |
| Neuraphonic | HackGT X | 2nd Overall; MATLAB Best Use | Screens for Parkinson's from voice samples | MATLAB, PyTorch, scikit-learn, Praat, Flask, Twilio | https://github.com/neuraphonic/neuraphonic | https://devpost.com/software/neuraphonic |
| Alleaf | Hacklytics 2026 | Best Overall, 1st | Relief and wellness platform with ESP32 sensing and an ML model | ESP32, Next.js, Firebase, Gemini, scikit-learn, Actian VectorDB | https://github.com/Gustavo-Galvao-e-Silva/Alleaf | https://devpost.com/software/alleaf |
| Lumos AI | Hacklytics 2026 | 2nd Overall | Safety-aware routing built on crime, weather and event data, with a voice agent | React, FastAPI, XGBoost, FBI NIBRS/Census APIs, Gemini, Vapi, ElevenLabs, Twilio | https://github.com/hxxtsxxh/lumos.ai | https://devpost.com/software/lumos-ai |
| Crisis Averted | Hacklytics 2026 | 3rd Overall | 3D globe that maps gaps in humanitarian funding, with an AI voice guide | Databricks, Kafka, Delta Lake, Next.js, react-globe.gl, ElevenLabs, Actian | https://github.com/GodlyDonuts/Hacklytics-GoldenByte | https://devpost.com/software/crisis-averted |
| BraceML | Hacklytics 2026 | First in Sports; Figma Make Most Creative Data Viz | Injury-risk and fatigue detection in the browser from any camera | YOLO11, TensorRT, FastAPI, Next.js 15, Three.js, Gemini, ElevenLabs | https://github.com/jiekaitao/BRACE | https://devpost.com/software/braceml |
| Vigil | Hacklytics 2026 | First in Healthcare | Wearables plus computer vision detect medical emergencies at large events | Flutter, Wear OS, Raspberry Pi, YOLOv8, FastAPI, Gemini | https://github.com/aishanibal/hacklytics2026 | https://devpost.com/software/vigil-b8uatr |
| PayBack | Hacklytics 2026 | Best Use of Actian VectorAI DB | AI agent that disputes your hospital bill | LangGraph, FastAPI, MongoDB, React, Actian | https://github.com/Itz-Viggy/payBack | https://devpost.com/software/payback-tnauqm |
| ProteinAI | Hacklytics 2025 | Best Overall Hack | Predicts protein–protein interactions with ESM-2 and AlphaFold embeddings | PyTorch, CUDA, ESM-2, Django, Biopython, UniProt/RCSB | https://github.com/Oscar11800/ProteinAI.git | https://devpost.com/software/proteinai |
| thera_pixel | Hacklytics 2025 | 2nd Place Hack | Gamified physical therapy with real-time form feedback | MediaPipe, OpenCV, Flask, SciPy | https://github.com/vehnil/PTplay.git | https://devpost.com/software/rehab-fv6j1l |
| Wonder | VandyHacks XII (2025) | 1st Place; MLH Best Use of ElevenLabs | AI-native DAW, pitched as "the Cursor for music" | Gemini, ElevenLabs, LanceDB, MongoDB Atlas, Snowflake, librosa | https://github.com/Korirussell/wonder | https://devpost.com/software/wonder-092csj |
| Nana's Helper | VandyHacks XII | 2nd Place | Wearable and voice assistant that reminds and protects elderly relatives | Swift, Next.js, FastAPI, MongoDB, OpenAI, ElevenLabs | https://github.com/theVedanta/Nanas-Helper | https://devpost.com/software/nana-s-helper |
| InterviewArcade | HackNC 2025 | General, 1st | Live mock technical interviews with an AI voice interviewer | React, FastAPI, Gemini, ElevenLabs | https://github.com/coopersizemore/InterviewArcade | https://devpost.com/software/interview-arcade |
| Localized | HackNC 2025 | General, 2nd; Capital One Best Personal Finance | Rewards app for local Chapel Hill businesses | SwiftUI, FastAPI, AWS RDS, JWT | https://github.com/alexandramarum/localized/ | https://devpost.com/software/localized |
| Quiet Table | Pearl Hacks 2026 | First Place; MLH Best Use of MongoDB Atlas | Matches strangers for a shared meal, with no feed or followers | Next.js, MongoDB, Gemini, Google Maps | https://github.com/betsygeo/quiet-table | https://devpost.com/software/quiet-table |
| Guardian Angel | UGAHacks 11 (2026) | Best Overall Hack | Detects falls for seniors, records a clip and alerts caregivers | MediaPipe, OpenCV, Flutter, MongoDB, AWS, Telegram | https://github.com/saachivar/guardian-angel-ugahacks11 | https://devpost.com/software/guardian-angel-kzlehw |
| Patient Watch | HackDuke Code for Good 2023 | Healthcare (Patient Safety) track | Camera-based patient monitoring for nurses | Raspberry Pi, Arduino, OpenCV, Flask, nginx | https://github.com/mbryant2025/HackDuke2023 | https://devpost.com/software/car-watch |

## 3. Patterns

- **Hardware plus computer vision tends to take Best Overall at HackGT.** Every HackGT 13 top-3 project has a physical or AR element: Sky-C2 (AR), FlyBy (drones) and VIGIL (eyewear plus drone). So does Dose (ESP32 load cell), the 2025 winner. Other hardware winners include TreePlenish (Raspberry Pi, HackGT X 3rd) and Guardian Angel (UGAHacks 11). Judges remember something they can hold or watch move.
- **Healthcare is the most crowded field, and it still wins.** Winners include Noma, OncoAI, ScribeAI, Neuraphonic, TapChart, ATP, Vigil, PayBack, ProteinAI, thera_pixel and Patient Watch. The winning angle is a narrow clinical moment, not "an AI doctor": Parkinson's mistaken for a stroke (TapChart), prior-auth phone calls (ATP), Mohs surgery errors (Noma).
- **Accessibility shows up again and again:** VisionNav, Vertex A11y, Synesthesia, VIGIL, SignSpeak and EyeCode (both on VandyHacks XII / HackNC 2025 galleries).
- **Voice agents are the 2025–26 signature.** ElevenLabs, Vapi or Twilio voice features in Wonder, Nana's Helper, InterviewArcade, Lumos AI, Crisis Averted, ATP and BraceML. Gemini is the default LLM at Pearl Hacks, HackNC and VandyHacks, partly because of the MLH prizes for using it.
- **Many winners stack prizes**, taking a main track plus a sponsor or MLH prize: Wonder (1st + ElevenLabs), Quiet Table (1st + MongoDB), Localized (2nd + Capital One), BraceML (Sports + Figma), Neuraphonic (2nd + MATLAB), Atlas (Cedar + Mastra). Sponsor tools like Actian VectorAI, Mastra and CedarOS had their own prizes with few competitors.
- **Data-heavy events reward real datasets:** Hacklytics winners use public data (FBI NIBRS, HDX humanitarian data, UniProt) and pipelines (Databricks/Kafka), then show the result as a polished 3D or map view (Crisis Averted's globe, Lumos's routing map).
- **Agent and dev-tool projects win sponsor tracks more than Best Overall.** Fourteenth Floor, Atlas, Orion and CommitSense won tracks or sponsor prizes; prompt+ (HackGT 11 3rd) is the exception.

**Takeaways for our Knight Hacks project**
1. Give the demo a physical or spatial "wow" moment: an ESP32 or Pi sensor, a phone camera running MediaPipe/YOLO, or AR. Keep the core software simple enough to finish.
2. Choose one narrow, high-stakes user moment (health, safety or accessibility) and name it in the tagline, as TapChart and ATP did.
3. Add a voice layer (ElevenLabs or Vapi plus Gemini) where it really helps. It wins MLH prizes and makes the demo memorable.
4. Plan to stack prizes: one main track plus 2–3 sponsor or MLH tools you actually use (MongoDB Atlas, Gemini, ElevenLabs, a sponsor's data API). Sponsor tools that few teams use, as Actian, Mastra and Cedar were, are the easiest wins.
5. If there's a data track, use a real public dataset and a visual front end (map or globe) rather than a notebook.

## 4. Open questions / next searches

- **Hacklytics 2024** (https://hacklytics-2024.devpost.com/project-gallery) returned no gallery entries over curl, and **Hacklytics 2023** (hacklytics23.devpost.com) returned 403. Results weren't checked.
- **HackDuke 2024 and 2025** (held Feb 2025) aren't on Devpost under any slug I tried. HackDuke may have moved off Devpost. Check https://hackduke.org or its socials.
- **Winners I confirmed but didn't log** (each gallery shows winner badges):
  - Pearl Hacks 2025: NEST, FridgeFresh. Pearl Hacks 2024: PublicEye.
  - VandyHacks XI: Spyder, CourseCoach. VandyHacks X: ChatEDU, AEyes.
  - HackNC 2024: Unplugged, Car Thang, fairLends. HackNC 2023: foodBuddy, wellSpent.
  - UGAHacks X: TalkStar, MedMonitor. HackDuke 2023: SaveSamurai, CodeLingo, EcoQuest.
  - Hacklytics 2026: GrowthFactor, Databricks and finance-track winners (Veritais, BlindSpot, Nexus, CitySpot).
- **Leads once sponsor tracks drop:** if Knight Hacks has an Impiricus, Aramco, Capital One, Actian or Mastra track, the HackGT 12/13 and Hacklytics 2026 winners above are the closest precedents. Check each event's prize list at https://hackgt13.devpost.com/prizes and https://hacklytics-2026.devpost.com/prizes.
- **Other Southeast events not covered:** CUhackit 2024/2025 (cuhackit-2025.devpost.com), VTHacks 12/13 and HackViolet 2025 (Virginia, borderline in scope). Their slugs resolve but I didn't scan them.
