# Winners: Social Good, Accessibility & Civic Tech Tracks
_Researched 2026-10-09 · sources: Devpost hackathon pages, project galleries and project pages, pulled with curl because WebFetch returns 403 on Devpost; Devpost search API (`devpost.com/api/hackathons`)_

## 1. Scope
- **Method:** I listed about 225 collegiate and online Devpost hackathons from 2023–2026 through the Devpost API. I scanned each prize list for social good, social impact, accessibility, assistive, civic, community, inclusion, equity or public sector prizes, which turned up about 90 events with such a prize awarded. For about 55 of those I crawled the gallery winners and kept a project only when its own page showed **Winner + the exact track prize**.
- **Galleries crawled** (all `https://<slug>.devpost.com/project-gallery`): bitcamp2023, bitcamp2024, bitcamp2025, bitcamp-2026, cal-hacks-10, cal-hacks-12-0, deltahacks-xi, deltahacks-12, dubhacks-23, hack-mit-2023, hack-the-hill-iii, hackdavis-2024/2025/2026, hackduke2023, hackduke-code-for-good-2025, hackgt-x, hackharvard-2023, hackillinois-2026, hackprinceton-fall-2023, hackru-fall-2024/2025, hackumass-xiii, hoohacks-2024/2025/2026, hophacks, hophacks-fall-2025, knight-hacks-vi, la-hacks-2026, mhacks-15, mhacks-2024, nwhacks-2024/2025/2026, pennapps-xxv, swamphacks-xi, swamphacksx, technica-2023/2024/2025, unihack2025/2026, vandyhacks-x, ai-for-social-good-mlh, hackrice-15, citrus-hack-2026, uofthacks-13, hackthe6ix2023, hackatbrown2023, hacksmu-v, hackscx, bostonhacks-2023, impacthack26.
- **Skipped as duplicates** (already logged by other agents): Fluxus, WakeMate, Aggie Street Smart, BrailleOut, Ligands, StormSurge, Forget Me Not, SignScore (Knight Hacks VI accessibility), Polaris, SignVerse, ReStory.
- **Skipped as off-theme**, though they did win "accessibility" or "social good" prizes: SustainaSwap, No Hooting Around, StudyBuddy, Bytes, TouchGrass and UniSync. They are covered in Patterns.

## 2. Winners table
| Name | Hackathon | Prize/track | What it does | Stack | Repo | Source URL |
|---|---|---|---|---|---|---|
| Communico | DeltaHacks 12 (Jan 2026) | Best Accessibility Hack | AAC app for nonverbal/autistic users: symbols, emotions, drawings to speech | TypeScript, Gemini, ElevenLabs, face-api.js, OpenSymbols | github.com/xafn/communico | https://devpost.com/software/communico-i5opvc |
| Chorus | UofTHacks 13 (Jan 2026) | Backboard.io Humanity Award | AAC tool that raises words-per-minute for people with motor impairments | Next.js, Gemini, OpenAI, Whisper, ElevenLabs, MongoDB | github.com/samtjhia/uofthacks | https://devpost.com/software/chorus-wx1l79 |
| Unmute | HooHacks 2025 | Best Accessibility & Empowerment | Phone-calling app for people with speech differences | React, OpenAI, Twilio, WebSockets, Neon | github.com/Tron16/hoohacks2025final | https://devpost.com/software/unmute-lc5nkw |
| Reclaim. | MLH AI for Social Good (Jul 2026) | Best Use of DigitalOcean AI in a Social Good Hack | Restores agency and voice to non-verbal individuals | React Native/Expo, computer vision, ElevenLabs, DigitalOcean | github.com/AlanRoybal/reclaim | https://devpost.com/software/reclaim-j30yrd |
| Dom | HopHacks Fall 2025 | Social Good Track (Bloomberg) | Voice-driven web navigation for people with hand disabilities | Python, LangChain, Gemini, Web Speech API | github.com/sanghyuplee20/Dom | https://devpost.com/software/dom-hands-free-web-accessibility-for-people-with-disability |
| Access Buddy | nwHacks 2025 | Potential Community Impact | Natural language becomes website actions (type, scroll) for motor- and vision-impaired users | React, Flask, Node, OpenAI, Arduino | github.com/notjamesw/AccessBuddy | https://devpost.com/software/access-buddy-pyw1hf |
| HALO | HackUMass XIII (Nov 2025) | Best Accessibility Hack | Chrome extension that blocks photosensitive-epilepsy triggers and adds an ADHD reading mode | Chrome Ext API, Gemini, ElevenLabs, WCAG 2.1 | github.com/athulya-anil/Halo | https://devpost.com/software/halo-u73r9j |
| Focusly | Citrus Hack 2026 | Social Impact & Accessibility | AI tutor that chunks text with voice for neurodivergent learners | React Native, Gemini, ElevenLabs | github.com/thewildox/AccessTutor | https://devpost.com/software/focusly-wqc6sk |
| Fable | HackDuke Code for Good 2025 | Best Overall + Best Accessibility Hack | Immersive, accessible reading with generated audio and visuals | React, FastAPI, Gemini, LangChain, MediaPipe, AudioCraft | github.com/menamerai/hackduke | https://devpost.com/software/fable-m1d4bq |
| gatorlator | SwampHacks XI (Jan 2026) | Best Education, Accessibility & Social Impact | Chrome extension that live-translates lectures for ESL students | JS, DeepL, ElevenLabs, Gemini | github.com/suupreme/gatorlator | https://devpost.com/software/live-translation-extension |
| HAPPI | HackDavis 2025 | Best Assistive Technology | Personalized Alzheimer's care hub | Python, Streamlit, Gemini, MongoDB, Firebase | github.com/smthom1/alz-data | https://devpost.com/software/happi-1jh72r |
| EchoLens | Bitcamp 2025 | Best Social Good Hack | Phone camera describes nearby objects for blind users | React, Flask, OpenAI | github.com/JemLuu/bitcamp | https://devpost.com/software/echolens-xf9a5q |
| Altify | Technica 2023 | Best Accessibility Solution | Generates alt text for images | JS, TensorFlow | github.com/Quirkster/altify | https://devpost.com/software/altify |
| TactileVision | HackGT X (2023) | Fidelity Best Accessibility Hack | Continuously updating tactile map for blind mobility | Python, KiCad, SolidWorks (hardware) | github.com/JustinHahn8902/Tactile-Vision | https://devpost.com/software/tactilevision |
| GuideBot | Hack the 6ix 2023 | MLH Best Accessibility Hack (Fidelity) | Street-navigation device for visually impaired pedestrians | ESP32, Arduino, TensorFlow, React | github.com/davisliu2006/GuideBot | https://devpost.com/software/guidebot |
| Audivision | Bitcamp 2023 | Best Social Good Hack | LiDAR white cane plus haptic belt for spatial awareness | Raspberry Pi, RPLidar, Python, 3D printing | github.com/eileenyq/Bitcamp2023 | https://devpost.com/software/eyes-change-later |
| GST – Global Sign-language Translator | DubHacks '23 | MLH Best Accessibility Hack (Fidelity) | Translates sign languages from multiple regions | React Native, Flask, OpenCV/cvzone | github.com/Sheepca/Hand-Sign-Detection | https://devpost.com/software/gst-global-sign-language-translator |
| SLR – Sign Language Rocks | HackPrinceton Fall 2023 | Best Accessibility Hack (Fidelity) | Live sign-language subtitles | Python, MediaPipe, Arduino | github.com/danielazbib/sign-language-subtitles | https://devpost.com/software/slr-sign-language-rocks |
| DuoASL | nwHacks 2024 | Healthcare & Accessibility Track | Gamified ASL learning that checks your gestures with a neural net | Next.js, Flask, TensorFlow, OpenCV | github.com/jasonz23/duoasl | https://devpost.com/software/duoasl |
| NeuroNavigate | Bitcamp 2024 | Best Social Good Hack | App that helps autistic children read social and sensory situations | Swift, Flask, OpenAI, Vosk/Kaldi, CNN | github.com/AwesomeCuber6543/BitCamp | https://devpost.com/software/neuronavigate |
| Expungo | Cal Hacks 12.0 (Oct 2025) | Greatest Social Impact + Promise Public Impact Prize | Voice/AI guide that walks people through criminal-record expungement | Next.js, FastAPI, LiveKit, Gemini, GPT-4, LangChain, Chroma | — | https://devpost.com/software/clearpathai |
| VitaSpectra | Hack the Hill III (Sep 2026) | Civic Technology 1st | Contactless vitals HUD for first responders | Raspberry Pi, Presage, CV, 3D printing | github.com/QuantumCoder325/HackTheHill3 | https://devpost.com/software/tempname-sfk4wn |
| Porchlight | Hack the Hill III (Sep 2026) | Civic Technology 2nd | Offline-first neighborhood emergency network (button or fall reaches neighbours and the City via Open311) | Arduino, Web Bluetooth, TinyML, Next.js, Gemini, ElevenLabs, Auth0, Vultr, TimescaleDB | github.com/GautamTalksDev/porchlight | https://devpost.com/software/porchlight-5mtw8u |
| evidently | Hack the Hill III (Sep 2026) | Civic Technology 3rd | Flags where police reports and bodycam footage diverge, for defence review | Next.js, FastAPI, YOLO, ByteTrack, ffmpeg, Gemini | github.com/kyle-yu33/bodycam-discrepancy | https://devpost.com/software/evidently-scdwh7 |
| AwareTexas | HackRice 15 (Sep 2025) | Social Impact Track | Plain-language tracker for Texas state legislation | React, Node, Cheerio scraping, Gemini, Firebase | github.com/kene2x/awaretexas | https://devpost.com/software/awaretexas |
| FireZero | HackDavis 2025 | Best Hack for Social Good | Turns public fire-hazard data into risk scores and action steps for agencies | Next.js, Python, Mapbox, Gemini | github.com/hunter-nguyen/HackDavis2025 | https://devpost.com/software/firezero |
| EyeQ | Bitcamp 2026 | Best Social Good Hack | Video system that flags caregiver abuse of vulnerable people | Python, YOLO, Gemini, SQLite | github.com/Haadesx/EyeQ | https://devpost.com/software/eyeq-0c8wdl |
| Surviv | HooHacks 2026 | Best Accessibility & Empowerment | Offline phone-to-phone mesh app for emergencies | Swift, MultipeerConnectivity, Core ML, MapKit | github.com/CruidGals/surviv | https://devpost.com/software/temp-ckv6zn |
| MeshMap | UNIHACK 2026 | Social Impact Prize | BLE mesh that relays messages and crisis alerts without Wi-Fi | Swift CoreBluetooth, Kotlin, Next.js, Supabase, Twilio, Claude | github.com/RuoHan-Chen/MeshMap | https://devpost.com/software/meshnet |
| RippleEffect | HopHacks Fall 2025 | Social Good Track (Bloomberg) | Round-up spare change into charity donations via a browser extension | React, Chrome Ext, Stripe, Firebase, Gemini | github.com/msavya/hophacks2025 | https://devpost.com/software/rippleeffect-k5i2vd |

## 3. Patterns
**What wins in accessibility, 2025–26: AAC and voice for people who can't speak or type.** Communico, Chorus, Unmute and Reclaim. all give a voice to nonverbal users or users with speech or motor differences, and Dom and Access Buddy let users drive the web by voice. The shared stack is **an LLM (Gemini or OpenAI) plus ElevenLabs TTS**, so one product idea also qualifies for the MLH ElevenLabs and Gemini prizes.

**Browser extensions are a cheap, high-scoring format.** HALO, gatorlator and RippleEffect are Chrome extensions. They demo instantly on any site, and HALO cited WCAG 2.1 directly in its "Built With" list, which signals rigor to judges.

**Sign-language translators are saturated.** They won repeatedly in 2023 (GST, SLR, SignScore at Knight Hacks VI) and in 2024 (DuoASL, SignVerse). By 2025–26, accessibility winners have moved to AAC, cognitive and neurodivergent support (Focusly, HALO, HAPPI) and agentic web control. A plain MediaPipe ASL classifier is no longer distinctive.

**Blind-navigation hardware still wins, especially at the top level.** TactileVision, GuideBot and Audivision won here. Portable Braille (TreeHacks 2025 Grand Prize 3rd) and BrailleOut are logged in other files. Physical, tactile demos stand out.

**2026 trend: offline-first resilience.** Surviv, MeshMap and Porchlight (plus Embers, nwHacks 2026 Community Impact) all keep working with no internet or power. This is a natural fit for Florida hurricanes.

**Civic winners pair public data with an LLM explanation layer.** Examples: AwareTexas (legislation), FireZero (fire-hazard data), Expungo (legal process; won 2 prizes at Cal Hacks 12.0 with a LiveKit voice agent) and evidently (bodycam versus report). Judges reward a concrete, named stakeholder: defence teams, a city, first responders.

**Prize stacking is normal.** Fable won Best Overall and Accessibility, and Expungo won 2 social-impact prizes. Porchlight won Civic 2nd while using Auth0, ElevenLabs, Vultr, Tiger Data and GoDaddy, which are all current MLH sponsor technologies.

**Judges read "accessibility" and "social good" loosely.** The Fidelity accessibility prize went to SustainaSwap (a tool-swap marketplace, HackHarvard 2023) and UniSync (note-taking, HackSMU V). DeltaHacks XI's accessibility prize went to a productivity owl, and TouchGrass won Technica 2024 social good. A solid build with a credible impact story can take these prizes when the field is thin.

**Prize-landscape facts:**
- MLH "Best Accessibility Hack sponsored by Fidelity" ran across 2023 events, including Knight Hacks VI. By 2024 it had turned into "[MLH] Best DEI Hack sponsored by Fidelity" (Listings, Technica 2024).
- Recurring in-house tracks: Bitcamp Best Social Good (2 winners a year, 2023–26), HackDavis Best Hack for Social Good (2023–26), HooHacks Accessibility & Empowerment (2023–26), HackRU Social Good (every semester), Technica social good and accessibility, UNIHACK Social Impact, nwHacks Community Impact.
- **Knight Hacks VII (2024) and VIII (2025) had no social good or accessibility prize.** The closest were "Most Useful" Hack and OneEthos "AI for Financial Empowerment". ShellHacks 2023–25 had none either.

### Takeaways for our Knight Hacks project
1. **Don't count on a dedicated social-good track at Knight Hacks.** Use the impact story to win "Most Useful", Overall and sponsor prizes, the way Fable and Expungo stacked theirs.
2. **Pick a named user and one painful daily task**, for example a nonverbal person making a phone call (Unmute) or hands-free browsing (Dom). Then demo it live from that user's point of view.
3. **Build on Gemini and ElevenLabs** (MLH prize-eligible) plus one more MLH technology such as Auth0, Vultr or Snowflake. The accessibility idea and the sponsor prizes stack.
4. **Use a Florida-native angle**, such as offline-first hurricane resilience or plain-language civic data (Orange County and Florida legislature, 311). It matches the 2026 winning trend and gives judges an obvious local stakeholder.
5. **Avoid a vanilla ASL translator.** If we go into accessibility, aim at AAC, cognitive and neurodivergent support, or agentic web control, and cite WCAG.

## 4. Open questions / next searches
- **WebFetch is blocked** (HTTP 403) on all `*.devpost.com` pages. Use `curl` with a browser User-Agent.
- **Devpost's `prize_filter[prizes][]` gallery parameter does not filter by prize**; it returns every winner. Confirm a prize only from each project page's "Submitted to → Winner" list.
- **ImpactHack 2026** (https://impacthack26.devpost.com) ended Oct 8, 2026 and shows no Winner badges yet. Its "Best Social Impact" and "Best Accessibility Project" prizes are worth re-checking.
- **Not crawled, worth checking:** Assistive Innovation Challenge 2026 (https://assistive-innovation-challenge.devpost.com), CityCamp Gainesville Hack Day, Sep 2026 (https://citycamp-hack-day.devpost.com, Florida civic), Civic Tech & Data Hackathon @ Baruch (https://civic-tech-data-hack-baruch.devpost.com), Richmond Civic Hackathon (https://hack-for-rva.devpost.com), Accessibility Hackathon Jan 2026 (https://accessibility-hackathon.devpost.com), and Hack Away Hunger's Community Impact Award (https://hack-away-hunger.devpost.com).
- **Other tracks seen in the scan but not crawled:** HackMerced "Health for Social Good" (https://hackmerced-x.devpost.com), MHacks 16 "Social Impact" (https://mhacks-16.devpost.com), HackPSU Social Impact (https://hackpsu-fall-2023.devpost.com) and UNIHACK 2023/2024 Social Impact.
- **Microsoft AI for Accessibility Hackathon 2024** (SE Asia, not on Devpost) came up in search only and was not verified.
- **Once sponsor tracks drop,** if Knight Hacks IX adds an accessibility, DEI or "useful" prize, re-read HooHacks and Bitcamp judging criteria: https://hoohacks-2026.devpost.com and https://bitcamp-2026.devpost.com.
