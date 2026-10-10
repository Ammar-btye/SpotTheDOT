# Winners: Healthcare, medical and mental-health tracks

_Researched 2026-10-09 · sources: Devpost hackathon pages (prize lists), Devpost project galleries (Winner ribbons), Devpost project pages ("Submitted to" prize list, Built With, Try it out), lablab.ai blog_

## 1. Scope

**Method.** I used the Devpost hackathon API to resolve about 170 collegiate and online hackathons from 2023–2026. I scraped each one's prize list for health-related prize names. For 34 events that had a health prize, I pulled every Winner-ribboned project from the gallery and read each project page to confirm which prize it won. All rows below show the prize as listed on the project page.

**Galleries scanned:** TreeHacks 2023–2026 (`treehacks-202X.devpost.com`), Cal Hacks 10, HackPrinceton Fall 2025 and Spring '26, HackHarvard 2023 and 2024, HackDavis 2023–2025, DeltaHacks X, XI and 12, MHacks 2024, nwHacks 2024 and 2025, HackGT X, HackRice 14 and 15, SwampHacks X, ShellHacks 2024, HopHacks Fall 2024 and 2025, Bitcamp 2025, HackUMass XI, HackRU F23 and S24, DubHacks '23, UofTHacks 13, Hacklytics 2023 and 2025, HackMIT 2023. The URL pattern is `https://<slug>.devpost.com/project-gallery`.

**Prize lists checked with no health prize:** Knight Hacks VI, VII and VIII; LA Hacks 2023–2026; Hack the North 2023–2026; ShellHacks 2023, 2025 and 2026; SwampHacks IX; Hackabull 2023 and 2025.

**Skipped as already logged by other agents:**
- Shepherd (TreeHacks 2026 Grand Prize and Healthcare Track): `winners-calhacks-treehacks`
- ShadowGuard (TreeHacks 2026 Healthcare): `winners-security-devtools`
- Vigil, ScribeAI, Patient Watch: `winners-southeast`
- Fluxus, Fivi: `winners-northeast-ivy`
- healthNET, Guardian Angel, Align: `winners-northeast-midatlantic`

**Not used:** non-Devpost health hackathons such as NUS HealthHack and MIT Grand Hack, and online-only Devpost health challenges with very small fields.

## 2. Winners table

| Name | Hackathon | Prize/track | What it does | Stack | Repo | Source URL |
|---|---|---|---|---|---|---|
| RescueRX | TreeHacks 2026 | [OpenEvidence] Best Use of Clinical Information | Knowledge graph that finds shelved drugs to repurpose for other diseases | Python, ML, knowledge graph | https://github.com/Donglomur/TreeHacks | https://devpost.com/software/rescuerx |
| .dot | TreeHacks 2026 | [Zingage] Best Voice AI for Healthcare | Voice-first in-home care companion for the elderly: med records, pill-bottle scan, emergency calls | OpenAI Realtime, Claude, Jetson Nano, Arduino, React, Vercel | https://github.com/o-bm/dot | https://devpost.com/software/dot-bringing-humanity-to-in-home-care |
| Therms | TreeHacks 2025 | Healthcare Grand Prize (Terra) + Scrapybara Capy Prize | Thermoregulation wearable that heats or cools to hold core temperature, with AI insights | Terra API, Next.js, Firebase, OpenAI | https://github.com/arnavnc/therms-platform | https://devpost.com/software/therms-thermoregulation-wearables-with-ai-powered-insights |
| TherapEase.ai | TreeHacks 2024 | Health Grand Prize | PT telehealth with pose-similarity coaching and contactless heart rate (rPPG) | WebRTC, OpenCV, pose estimation, rPPG, Node | https://github.com/anshgupta1234/TherapEase/ | https://devpost.com/software/therapease-ai |
| Good Samaritan | TreeHacks 2024 | Most Impactful Hack + TerraAPI Health Prize + BGB Informed Physicians Prize | Vision Pro guides bystanders through first aid | Apple Vision Pro, SwiftUI, MediaPipe, OpenCV, Terra API | http://github.com/rayhotate/tree | https://devpost.com/software/good-samaritan-29zp5x |
| Health Story | TreeHacks 2023 | Healthcare Grand Prize | Hypertension record overview plus Speech2SOAP note generation for doctors | Vue, Flask, AWS Transcribe, GPT-3 | https://github.com/rajas1998/HealthStoryBackend | https://devpost.com/software/health-story |
| Amanuensis | TreeHacks 2023 | Big Idea: Best Technology-Enabled Patient Safety Solution ($2,000) | AI physician assistant that summarizes clinical records and generates questions | BioGPT, ChatGPT, Synthea, RedwoodJS, Postgres | https://github.com/ayushnoori/amanuensis | https://devpost.com/software/amanuensis |
| VITAL | HackPrinceton Spring '26 | Best Healthcare Hack | VLM and CV camera that monitors ER waiting rooms and flags deterioration (seizure, choking, stroke) | YOLOv8, MediaPipe, Claude, ElevenLabs, React | https://github.com/matnvd/HackPrincetonS26-VITAL | https://devpost.com/software/vital-ay4d5c |
| Asclepius | HackPrinceton Spring '26 | Best Overall Hack + Regeneron Clinical Trials + d_model | Local privacy proxy that strips PHI and IP before clinical-trial staff query cloud LLMs | Claude, Gemma, PyTorch, differential privacy, FastAPI, Supabase | https://github.com/Shiv-aurora/hackprincetonS26 | https://devpost.com/software/asclepius-4rthsu |
| Synovia | HackPrinceton Fall 2025 | Best Healthcare Hack (Daylight Health) | Predicts neurological deficits from planned brain-tissue removal ("flight sim for neurosurgery") | Gemini, FastAPI, Python, TypeScript | https://github.com/arishs24/HackPrinceton2025 | https://devpost.com/software/presurg |
| Patelloscope | DeltaHacks 12 | Best Health Hack | MRI/CT-based knee digital twin with FEA stress simulation for rehab | Gemini, Next.js, MongoDB, AWS, Vultr | https://github.com/arishs24/deltahacks12 | https://devpost.com/software/patelloscope |
| Spine Guard | DeltaHacks XI | Best Health Hack | Clip-on posture sensor that streams live to a dashboard | ESP32, MPU-6050, C++, Streamlit | https://github.com/hiatus770/deltahacks25 | https://devpost.com/software/spine-guard |
| DinoMind | DeltaHacks X | Best Health Hack | Student stress and journaling app with AI dino companions | React Native, Expo, Cloudflare, ML | https://github.com/derronli/DH10 | https://devpost.com/software/dinomind |
| MedRelay | HopHacks Fall 2025 | Best Healthcare Hack (Commure) + Best Overall Hack + MentorMates | Turns doctor-patient conversation into ICD-10/CPT-coded CMS-1500 form drafts | Flask, Gemini, Python | https://github.com/jackdeye/HopHacks | https://devpost.com/software/medrelay-ni7ypa |
| ReBloom | HopHacks Fall 2025 | AI + AR for Maternal Wellness (Orcava) | EXG sensor and AR coaching for postpartum core rehab | Arduino, EXG sensor, Unity, Langflow | https://github.com/tongxin-lily-li/ReBloom | https://devpost.com/software/rebloom |
| SurgiScan | HopHacks Fall 2024 | Patient Safety Technology Challenge | CV tracks surgical tools so none are left in the patient | YOLOv5, OpenCV, Python | https://github.com/ShauryaKumarr/SurgiScan | https://devpost.com/software/surgiscan |
| HealthIndia | HopHacks Fall 2024 | Telemedicine & AI in LMICs (CBID) | Multilingual phone-voice intake of medical histories for rural India | Twilio, OpenAI, TTS, Flask, React | https://github.com/nathanjzhao/healthindia.git | https://devpost.com/software/healthindia |
| NurseNotes | MHacks 2024 | Health Track Winner | Nurse audio notes become SOAP(IE) reports | Flask, OpenAI, JS | https://github.com/eteng2012/nurse_paperwork | https://devpost.com/software/nursenotes |
| Jarvis | Cal Hacks 10.0 | Hack for Health + MLH Most Creative Use of GitHub + Best Use of Milvus | Smartwatch and camera assistant that narrates surroundings for blind users | LLaVA, Hume, LangChain, Milvus, Zepp, Next.js | https://github.com/CalHacksJarvis | https://devpost.com/software/jarvis-wbfx7n |
| Flexy (And I Know It) | HackHarvard 2024 | AllHealth Track Prize | Gamified arthritis rehab: pose-matched exercises scored by cosine similarity | MediaPipe, OpenCV, Flask, React | https://github.com/Shameed4/Flexy | https://devpost.com/software/flexy-and-i-know-it |
| Gluchart | HackDavis 2023 | Best Healthcare Hack + Best Hack for Social Good | ML blood-glucose prediction for diabetics | Keras, scikit-learn, React, Azure | https://github.com/TimStewartJ/gluchart | https://devpost.com/software/gluchart |
| SkinScreen | HackDavis 2024 | Best Health Hack | AI skin-cancer screening app | PyTorch, Flutter, Flask, Intel GPU | https://github.com/simondgooden/SkinCancer | https://devpost.com/software/skinscreen |
| BreatheEasy | HackDavis 2025 | Best Medical Hack | Street-level air-quality sensor plus map and alerts for respiratory patients | ESP32, CCS811, Flutter, Firebase, Auth0 | https://github.com/harirakul/HackDavis2025 | https://devpost.com/software/breatheeasy-oay3l4 |
| Scout | HackGT X | [General] Best HEALTH 1001 Hack | Phone navigation for the visually impaired using object detection plus depth, with haptics | YOLOv8, MiDaS, ARCore, OpenCV, GCP | https://github.com/gn350/HackGTX/ | https://devpost.com/software/scout-c395ha |
| LidaCane | HackUMass XI | Best Healthcare Hack + Wolfram Award | Low-cost white cane with ToF LiDAR (8 m) and haptic/audio feedback | ESP32, LiDAR, Arduino, 3D printing | https://github.com/p0lyh3dron/lidacane | https://devpost.com/software/smart-lidar-cane |
| Better Gator | SwampHacks X | 1st – Health Track | iOS mental-health app built for UF students | SwiftUI, UIKit, api.ai | https://github.com/codeswift27/better-gator.git | https://devpost.com/software/better-gator-7angv3 |
| Medicine Dispensary | ShellHacks 2024 | Patient Safety Technology | Reminder and automatic pill dispenser | Raspberry Pi, MicroPython, Flask | https://github.com/Cantinadream/Big_Back_ShellHack2024 | https://devpost.com/software/bigback |
| RxBridge | HackRice 15 | Commure Healthcare Challenge | AI copilot for pharmacists handling drug shortages (scraping and substitution) | Gemini, FastAPI, Supabase, React, Railway | https://github.com/arnavjainpro/HackRice/tree/main | https://devpost.com/software/aaaa-h901oe |
| MIR.AI | Hacklytics 2025 | Third in Healthcare | Upscales 1.5T MRI scans to 3T-like quality | PyTorch, Colab, React | https://github.com/venkat1596/Hacklytics_Hackathon | https://devpost.com/software/ai-driven-efficient-mri-super-resolution |
| MindSight | lablab.ai Lōkahi Healthcare Accelerator (Jan 2025, online) | 1st place ($3,000) | AI tracker for therapy progress with emotion analysis for therapists and patients | — | — | https://lablab.ai/blog/lokahi-healthcare-accelerator-hack-summary |

## 3. Patterns

**1. Clinical documentation automation is the most repeated health winner.** It won across four straight years:
- Health Story (TreeHacks 2023, Speech2SOAP)
- NurseNotes (MHacks 2024, SOAP(IE))
- MedRelay (HopHacks 2025, ICD-10/CPT codes into CMS-1500 forms; it also took Best Overall)
- .dot (TreeHacks 2026, voice access to records)

The winners name the real standard they output (SOAP, ICD-10, CMS-1500). That makes a simple speech-to-LLM pipeline look clinically credible.

**2. Cheap hardware plus one sensor sweeps the mid-size health prizes.** The pattern is an ESP32, Raspberry Pi or Arduino with a single sensor and a live dashboard:
- Spine Guard (MPU-6050)
- BreatheEasy (CCS811)
- LidaCane (ToF LiDAR)
- Medicine Dispensary (Pi pill dispenser)
- ReBloom (EXG sensor)
- Therms (wearable)

At the top level, Shepherd (logged elsewhere) won the TreeHacks 2026 Grand Prize and the Healthcare Grand Prize with a motorized cane. The physical demo is the differentiator.

**3. Camera-based computer vision is the default "AI".** Examples:
- TherapEase: rPPG heart rate plus pose
- Flexy: MediaPipe with cosine similarity
- VITAL: YOLOv8 plus MediaPipe
- SurgiScan: YOLOv5
- Scout: YOLO plus MiDaS depth
- Good Samaritan: Vision Pro

None of them need patient data. A webcam, or the judges themselves, is the demo dataset.

**4. In 2026 the frame shifts to privacy and PHI.** Asclepius won Best Overall at HackPrinceton S26 as a local PHI-stripping proxy. ShadowGuard won TreeHacks 2026 Healthcare as a hospital PII firewall. Amanuensis (2023) used Synthea synthetic EHRs instead of real records. Winners avoid the "real patient data" problem by using synthetic data, public data (OpenFDA in MedX and Pillora, MRI datasets in MIR.AI), or the user's own sensors.

**5. Clinical depth reads as validity.** The same builder (GitHub `arishs24`) won Best Healthcare Hack at HackPrinceton F25 (Synovia) and Best Health Hack at DeltaHacks 12 (Patelloscope), both with MRI and FEA physics "digital twins". Asclepius reported a quantitative evaluation on a 1,200-document synthetic corpus. Formal clinical validation is rare. What wins is specific mechanism language: biomechanics, ε-DP, rPPG.

**6. Sponsors define many health prizes, often with several winners each.** Examples:
- Terra API wearables: TreeHacks 2024 and 2025, HackHarvard 2023
- Commure: HackRice 15, HopHacks 2025
- Regeneron clinical trials: HackPrinceton S26, 11 winning teams
- OpenEvidence and Zingage: TreeHacks 2026
- Zepp: Cal Hacks 10, 5 winners

A "Patient Safety Technology" challenge recurs at TreeHacks 2023, HackSC X, VandyHacks X, HopHacks 2024, HackHarvard 2024 and ShellHacks 2024 (Miami).

**7. Mental health wins at smaller or campus-scale events.** Examples are Better Gator (SwampHacks X), DinoMind (DeltaHacks X) and MindSight (lablab online). At the large events, physical, clinical and accessibility hacks take the health grand prizes. Accessibility for blind users (Shepherd, Jarvis, Scout, LidaCane) is often judged as health.

**8. Knight Hacks VI–VIII had no health-named prize on Devpost.** A health hack there would compete through sponsor or MLH prizes plus general judging, unless 2026 adds a health track.

**Takeaways for our Knight Hacks project:**
1. If we go health, build a physical or camera demo: an ESP32 or webcam, one sensor, and a live dashboard, used on a judge at the table.
2. Pick one clinical workflow and name its real standard (SOAP, ICD-10, FHIR, CMS-1500, triage levels). Specificity stands in for clinical validation.
3. Use synthetic data (Synthea) or public data (OpenFDA, Kaggle) and make PHI-safety a visible feature. It turns the data-access weakness into a 2026-style strength.
4. Stack sponsor prizes onto one build, as Good Samaritan (3 prizes), Jarvis (3) and MedRelay (3) did. A health hack fits sponsor tracks such as Terra, Commure, Regeneron and patient-safety challenges, plus MLH prizes (Presage camera vitals, ElevenLabs voice).
5. Show a number. MedRelay showed forms automated, LidaCane an 8 m range, Shepherd a 1/20 cost and TherapEase rPPG heart rate. Judges reward a measurable claim over "AI health assistant" chatbots.

## 4. Open questions / next searches

- **WebFetch returns 403 on all devpost.com pages.** Every Devpost result here came from curl. The Stanford Daily TreeHacks 2025 article does not name the health winners.
- **Missing health winners in some galleries.** No "Best Healthcare Hack" (1st) winner turned up for Hacklytics 2025, and HackMIT 2023 showed only 9 winners. These may sit past gallery page 7 or be unpublished:
  - https://hacklytics2025.devpost.com/project-gallery
  - https://hack-mit-2023.devpost.com/project-gallery
- **Health prizes found but galleries not scanned:**
  - Hacklytics 2026 healthcare 2nd and 3rd: https://hacklytics-2026.devpost.com
  - HackDavis 2026: https://hackdavis-2026.devpost.com
  - nwHacks 2026 wellness: https://nwhacks-2026.devpost.com
  - McHacks 13 HoloRay medical video: https://mchacks13.devpost.com
  - HackRU Fall 2024 mental-health prize: https://hackru-fall-2024.devpost.com
  - HackTX 2023 ProCore construction mental health: https://hacktx-2023.devpost.com
  - Hackabull VII "Health Care by SASE" (Tampa): https://hackabull26.devpost.com
  - SwampHacks XI wellbeing: https://swamphacks-xi.devpost.com
  - HopHacks Fall 2026 (just ended): https://hophacks-fall-2026.devpost.com
  - MHacks 2026 (just ended): https://mhacks-2026.devpost.com
- **Other HackPrinceton S26 Regeneron clinical-trial winners worth a skim:** InSilico, Onkos, Lazarus, ProtoSense, ACTA AI, BioStrata, Synova, Rom-Com, Trustworthy Science, Atlas. Each has a link from the "Submitted to" section at https://hackprinceton-spring-26.devpost.com/project-gallery.
- **Leads to check once sponsor tracks drop:** whether Knight Hacks IX adds a health or patient-safety track or a Terra/Presage-style sponsor. The Patient Safety Technology Challenge is a recurring traveling prize worth watching for.
- **MindSight:** I couldn't load the lablab project page or confirm its stack (https://lablab.ai/ai-hackathons/lokahi-innovation-in-healthcare/communeed/mindsight-ai-powered-therapy-progress-tracker). The win comes from the lablab summary blog.
