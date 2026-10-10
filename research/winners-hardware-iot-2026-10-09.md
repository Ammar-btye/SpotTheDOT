# Winners: Hardware, IoT, Robotics and Embedded Hacks

_Researched 2026-10-09 · sources: Devpost galleries and project pages (fetched with curl; WebFetch gets HTTP 403 on devpost.com), the Devpost hackathon search API, guide.mlh.com, mlh.com/resources/hardware_

## 1. Scope

**Method.** I scraped every "Winner"-badged entry from 50 Devpost galleries (about 1,180 winning projects). Then I pulled each project page's prizes, "Built With" tags and "Try it out" links, and filtered for hardware tags (arduino, esp32, raspberry-pi, jetson, servo, sensor, 3D printing, drones, ROS, Unitree and similar). Every row below was confirmed against the project page's "Winner" label and prize text.

**Galleries scraped (`https://<slug>.devpost.com/project-gallery`):** treehacks-2023, -2024, -2025, -2026; pennapps-xxiv, -xxv, -xxvi; hackgt-x, hackgt-12; mhacks-16; hackharvard-2023, -2024, -2025; knight-hacks-vi, knight-hacks-vii, knighthacksviii; hackillinois-2024, -2025, -2026; cal-hacks-11-0, cal-hacks-12-0; hack-mit-2023; bitcamp2024, bitcamp2025; hackprinceton-fall-2023, -spring-2024, -spring-2025; shellhacks2024, shellhacks2025; swamphacksx, swamphacks-xi; hackthenorth2023, hackthenorth2025; uofthacks-11, uofthacks-13; boilermake-xii; hacktx-2024, hacktx2025; hackrice-15; madhacks-fall-2025.

**Skipped because other agents already logged them** (same names appear in other files in research/): Shepherd, OmNom, Portable Braille, Edith, Smart Shoe and Robosurge (TreeHacks); Encrypta, Tacti-sight, Formify, Dragonotchi, Chat Clip That, Restful Knights, Virtual Foosball, EchoAI, iPalo, ZPM and HeliosAI (Knight Hacks); Dose and TreePlenish (HackGT); SoundSheild, SurgeVue, Diabeteasy, Post Surgery Pillow, ResQme and SixthSense (Ivy); TerraGlide and the John Deere robots, plus REMI (Midwest); Rubbish, ReStory, Lumi Lens and ARSL (Florida); Hardware Context Protocol and Ted.AI (Cal Hacks 12).

**MLH hardware lab** ([guide.mlh.com contents](https://guide.mlh.com/organizer-resources/hardware-lab-contents), [logistics](https://guide.mlh.com/general-information/event-logistics/hardware), [mlh.com/resources/hardware](https://www.mlh.com/resources/hardware)):
- **Who gets it:** US member events only, and availability is limited.
- **Big items:** 9 Raspberry Pi 4B kits, 12 Arduinos with Grove base shields, 8 Logitech webcams, Google Nest Minis and JBL Go 3 speakers.
- **About 25 kinds of Grove modules:** ultrasonic, accelerometer, light, sound, moisture, air quality, UV, touch, NFC, joystick, LCD, 7-segment, servo, stepper with driver, and a motor/servo driver board.
- **Basics:** brushless DC motors, breadboards, jumper wires, resistors and capacitors.
- **Shared tools:** multimeter, strippers and pliers.
- **Checkout:** you leave your **ID as collateral** until everything comes back. Quantities are small (only 3 ultrasonic sensors and 4 servos), so bring your own ESP32s or MCUs.

**Knight Hacks hardware prizes:**
- KH VII had a "Best Hardware Hack" prize (a Raspberry Pi 5 for each team member).
- KH VIII (Oct 2025) had five:
  - "Best Embedded Hack" (a Raspberry Pi 5 plus an UNO R3 kit with 400+ add-ons)
  - Pheratech "ROS2 Autonomy Challenge"
  - NextEra "Drone Optimization Challenge" (all 3 winners built software route optimizers with OR-Tools, not drones)
  - AMD "Best use of AMD Hardware/Software"
  - MLH "Best Use of Arm"

  Source: https://knighthacksviii.devpost.com/

## 2. Winners table

| Name | Hackathon | Prize/track | What it does | Stack | Repo | Source URL |
|---|---|---|---|---|---|---|
| Recollect | TreeHacks 2024 | Best Hardware Hack (4x Prusa 3D printers) | Robot that flips pages, photographs and digitizes physical books | Arduino, 3D-printed + laser-cut frame, Fusion 360, Google Cloud Vision, GPT-4, Next.js, Supabase | https://github.com/Scott-Hickmann/Book-Scanner | https://devpost.com/software/recollect-ytn0bk |
| Show and Tell | TreeHacks 2024 | Most Creative Hack; Human Capital prize | Sensor glove that adds emotion/expression to sign language via LLM | ESP32, IMU, Hume AI, OpenAI | https://github.com/raviriley/aidactyl | https://devpost.com/software/show-and-tell-capturing-emotion-in-sign-language |
| LavÜ | TreeHacks 2023 | Most Cyberpunk Hardware Hack by Arduino; Best VALUENEX Radar Hack | Wearable EMG muscle-tension sensor with haptic feedback + app | Arduino, EMG, 3D printing, haptics, Figma | https://github.com/mehulrao/Lav-U | https://devpost.com/software/lavu |
| Express Drone Care | TreeHacks 2023 | Best Use of Drone Technology by Parrot | Drone delivery of prescriptions/lab tests from a medical record | Arduino, servo, Fusion 360, OpenAI, Python, React | https://github.com/dliud/express-drone-care | https://devpost.com/software/express-drone-care |
| WingNote | TreeHacks 2025 | Google Cloud: Best Use of Gemini | Clip-on nurse device that listens and auto-structures care notes | XIAO ESP32, Arduino Nano, RFID reader, LiPo, Deepgram, Gemini, Next.js, Supabase | https://github.com/bencullenn/wing-note | https://devpost.com/software/wingnote |
| Ranger | TreeHacks 2025 | NVIDIA: Best Accelerated Compute | Wearable AR that visualizes surrounding sounds for deaf users | Jetson Nano, Unity, Python ML | https://github.com/YuanSamuel/Treehacks2025/ | https://devpost.com/software/ranger-6jkv5s |
| diffuji | TreeHacks 2026 | Most Creative; [Neo] Most Likely to Become a Product | Instant camera that restyles photos with diffusion and prints stickers | Raspberry Pi (512MB), Arducam, thermal printer, OLED, rotary encoder, 18650s | http://github.com/alexkranias/dispo | https://devpost.com/software/diffuji |
| HeartStart | TreeHacks 2026 | Best Beginner Hack | Wearable detects cardiac arrest; robot navigates to patient for CPR, Twilio alert | Arduino, ROS2, OpenCV, Arducam, PySerial, Twilio | https://github.com/nicolewongbiz/cpr-robot.git | https://devpost.com/software/heartstart |
| Sprout | TreeHacks 2026 | [NVIDIA] Edge AI Track | Mini robot microfarm run by an on-device LLM | Jetson Nano, Arduino, GPIO/I2C, Ollama, Qwen | https://github.com/lethan3/cactushacks | https://devpost.com/software/greenguardian-microfarm |
| TORQ | TreeHacks 2026 | [NVIDIA] Edge AI Track | Retrofit kit to make a car self-driving on Jetson Thor | Jetson Thor, CUDA, Holoscan, MQTT, C++, Swift | https://github.com/bryandong24/treehacks2026 | https://devpost.com/software/torq |
| Keryx | TreeHacks 2026 | Human Capital Fellowship Prize | Drones map buildings into world models that assistive agents navigate | Drones, Apple Depth Pro, Hugging Face, FastAPI, Modal | https://github.com/WubbLord/treehacks-26 | https://devpost.com/software/keryx-k49dta |
| ambi. computing | PennApps XXIV (2023) | Best Hardware Hack | Touchless hand-gesture control of car peripherals (fan, lights) | Arduino UNO, NeoPixel, PWM fan driver, OpenCV, Flask, Swift | https://github.com/jibraanghani/PennApps23 | https://devpost.com/software/ambi-qsiawr |
| Glucose | PennApps XXV (2024) | Best Hardware Hack | Flex-sensor sleeve tracks joint rehab progress | ESP32, flex sensor, Bluetooth, Angular, Flask, Plotly | https://github.com/Keith-Khadar/Pennapps24 | https://devpost.com/software/glucose |
| BikeBuddy | HackGT 12 (2025) | The Gadget Gallery – 1st | Bike rear-view camera + turn-signal module streamed to a phone app | ESP32 (AP + webserver), camera, LCD, 3D print, laser cut, React Native, PlatformIO | https://github.com/tsar-boomba/BikeBuddy | https://devpost.com/software/bikebuddy |
| Dispatch | HackGT 12 (2025) | Hall of Illusions – 1st | VR locomotion hardware for first-responder training | PlatformIO, C++, Unity, SteamVR, Python | https://github.com/RealityBenders/BoundlessVR | https://devpost.com/software/dispatch-u7fwrv |
| PulseWalk | Cal Hacks 11.0 (2024) | Cal Hacks: Best Hardware Hack | Shoe with IR sensors + haptic servos for blind navigation, satellite GPS | Arduino, IR sensors, servos, vibration motors, Skylo Type 1SC, React Native | https://github.com/lucasreljic/Cal-Hacks-shoe-thing | https://devpost.com/software/pulsewalk |
| Canary | Cal Hacks 11.0 | Skylo: Cellular-to-Satellite | Satellite-linked wireless sensor network for early wildfire detection | Arduino, ESP8266, Murata, Skylo, UDP, Streamlit | https://github.com/tsai-henry/canary | https://devpost.com/software/canary-lrg3ep |
| Talk Tuah | Cal Hacks 11.0 | Best Beginner Hack; Deepgram Voice Agent | AR glasses with a social-coaching AI chatbot | Raspberry Pi, Arduino, Deepgram, Hume, Flask, React Native | https://github.com/steven-mu12/talk-tuah | https://devpost.com/software/talk-tuah |
| MIRAI | Cal Hacks 12.0 (2025) | BitRobot: Best Robotics Hack – 1st | Unitree G1 humanoid imitates your pose and obeys voice | Unitree SDK2, MediaPipe, OpenCV, Pinocchio IK, SpeechRecognition | https://github.com/A-Mundanilkunathil/Unitree-G1 | https://devpost.com/software/boxing-robot |
| MARC | Cal Hacks 12.0 | BitRobot: Best Robotics Hack – 2nd | Robot arm draws text-prompted images with a marker (~2 mm accuracy) | LeRobot arm, Stable Diffusion XL, OpenCV homography, PyTorch | https://github.com/yyardi/cal-hacks-marc | https://devpost.com/software/marc-marker-actuated-robotic-controller |
| Walkie Talkie | HackPrinceton Spring 2025 | Best Hardware Hack | Smart cane: YOLO obstacle detection + ultrasonic haptics | Raspberry Pi, GPIO, YOLOv5, OpenCV, WebSockets | https://github.com/AahanMehta21/smartCane | https://devpost.com/software/walkie-talkie-xg9d70 |
| Harvest Hero | HackPrinceton Fall 2023 | Best Environment Hack (track) | Soil/moisture sensing + plant-disease detection | Arduino, Raspberry Pi, Azure IoT, PyTorch, Streamlit | https://github.com/bplatoff/HackPrinceton23 | https://devpost.com/software/harvest-hero-0alkmo |
| LivePresence | Bitcamp 2024 | Best Hardware Hack; Best Advanced Quantum Track | Room-occupancy detection from CO2/temp/motion/VOC sensors | ESP32-WROVER, MQTT (Mosquitto), Flask, PyTorch + Qiskit, OpenAI | https://github.com/Fredswqa190/BitCamp2024Submission-LivePresence | https://devpost.com/software/a-i36e2g |
| Cyber Sentinel | Bitcamp 2025 | Best Hardware Hack | Raspberry Pi appliance that scans sites/downloads for malware | Raspberry Pi, YARA, Gemini, MongoDB, React | https://github.com/Suvrath421/bitcamp2025 | https://devpost.com/software/cyber-sentinel |
| SwampRise | SwampHacks XI (2026) | Best Integration of Hardware | Alarm clock that wakes you based on live bus arrival times | ESP32, ESP-IDF, FreeRTOS, RTC, LCD, 7-segment, reverse-engineered transit API | https://github.com/ethantayl/SwampRise | https://devpost.com/software/swamp-rise |
| Happy Head | ShellHacks 2025 | Best First-Time Hacker | Modular IoT head-impact safety platform for youth athletes | TI LaunchPad, accelerometer/gyro, I2C/SPI/UART, MediaPipe, Next.js, Supabase | https://github.com/PGatts/HappyHead | https://devpost.com/software/happy-head |
| Ctrl-ARM | ShellHacks 2025 | Microsoft | Control your computer with forearm-muscle (EMG) gestures + voice | MyoWare 2.0 EMG, XIAO Sense IMU, scikit-learn, Electron, Gemini, Whisper | https://github.com/DanielJEfres/ctrl-arm | https://devpost.com/software/ctrl-arm |
| AstroDoodle.party | HackTX 2025 | Best Overall | Multiplayer space game played by casting spells with 3D-printed LED wands | 3D printing, LEDs, OpenCV, $Q gesture recognizer, TypeScript | https://github.com/gjkeller/astrodoodle | https://devpost.com/software/rocket-racer-l1hmn6 |
| Electric Chair | MadHacks Fall 2025 | Most Dangerous Hack | Rideable motorized chair driven by Xbox controller / Kinect | ESP32, Bluepad32, RoboClaw 2x60A, Kinect, 3D printing | https://github.com/Balabalu-VE/Chair_Bot | https://devpost.com/software/electric-chair |
| DUM-E | Hack the North 2025 | Finalist | Natural-language robotic arm with CV and fast inference | Arduino, Raspberry Pi, OpenCV, Groq, CAD | https://github.com/pekachoo/htn-DUM-E | https://devpost.com/software/dum-e-kgx6at |

## 3. Patterns

**1. Assistive wearables and accessibility devices win most often.**
- Examples: PulseWalk (shoe), Walkie Talkie (cane), Show and Tell (glove), Ranger (deaf AR), Ctrl-ARM (EMG) and LavÜ (EMG haptics).
- The theme also took grand prizes we skipped as already logged: Shepherd won TreeHacks 2026 1st, Tacti-sight won Knight Hacks VI 1st and Portable Braille won TreeHacks 2025 3rd.
- The usual formula is cheap sensors (ultrasonic, IR, IMU) driving haptic output for someone with a sensory gap.
- It works because the demo is visceral: a judge puts it on, closes their eyes and feels it work.

**2. "Hardware + AI brain" beats pure hardware or pure AI.**
- The device does the sensing and acting, and an LLM or VLM supplies the reasoning. Examples: WingNote (Gemini notes), Talk Tuah (Deepgram + Hume), Sprout (local Qwen on Jetson), DUM-E (Groq) and diffuji (on-device diffusion).
- Sponsor AI prizes (Gemini, Deepgram, NVIDIA, Microsoft) regularly go to hardware teams. A physical object makes the API use stand out.

**3. The ESP32 is the default microcontroller in 2024–2026, with Arduino and Raspberry Pi close behind.**
- ESP32 shows up in Glucose, BikeBuddy, SwampRise, LivePresence, Electric Chair and WingNote. Built-in WiFi/BLE replaces a tethered laptop: BikeBuddy ran the ESP32 as its own access point plus webserver.
- Raspberry Pi is the go-to for camera and CV work (Walkie Talkie, diffuji). Note that Walkie Talkie reported the Pis "would repeatedly hang or crash" running YOLO, so they moved inference off-device.
- Jetson boards win NVIDIA tracks (Ranger, Sprout, TORQ).

**4. Sponsor hardware gets its own prize pool.**
- Examples: Skylo satellite modems (Canary, PulseWalk), Unitree G1 and LeRobot arms (MIRAI, MARC), Parrot drones (Express Drone Care), Viam (PennApps), Snap Spectacles, LeLamp and NVIDIA Jetson.
- These tracks have few entrants, because few teams risk sponsor hardware in 36 hours.
- Knight Hacks VIII had the same structure with Pheratech ROS2, NextEra drones and AMD.

**5. Fabrication polish is rewarded.**
- Recollect (3D-printed + laser-cut book scanner), BikeBuddy (acrylic enclosure), diffuji ("sleek and functional product") and AstroDoodle (wands CADed and printed overnight) all stressed enclosures.
- Judges reward an object that looks like a product, not a breadboard. "Most Likely to Become a Product" went to diffuji.

**6. Scoping lessons from winners' own write-ups.**
- **Power is the top failure point.** Smart Shoe "smoked components" on power circuitry, and Show and Tell hit shared power/ground problems. Budget time for batteries, buck converters and regulators.
- **Keep the demo path wired.** HeartStart: "Our ultimate aim is full wireless… this wired solution gave us the reliability needed."
- **Trade accuracy for latency.** Ctrl-ARM dropped a 98.6%-accurate CNN for a faster decision tree.
- **Use a kit chassis.** TerraGlide (logged elsewhere) built on a SunFounder rover kit, and DUM-E and MARC used off-the-shelf arms. Build the novel part, not the drivetrain.
- **Outdoor autonomy is fragile.** OmNom's RTK GPS drift prevented "a reliable demo which did the whole sequence," and it still won Most Creative on ambition.
- **Even a Raspberry Pi as a server counts.** Cyber Sentinel won Bitcamp's Best Hardware Hack with a Pi running Python and YARA scripts. Category judges reward working integration over deep electronics.

**7. Demo style.** Winners show live physical interaction plus a web or phone dashboard of the sensor data (Glucose, BikeBuddy, HeartStart, Happy Head). Several hand out a takeaway: diffuji printed stickers for attendees, and AstroDoodle let judges play.

### Takeaways for our Knight Hacks project
1. **Target Knight Hacks' own hardware lines.** KH VIII offered Best Embedded Hack, a ROS2 Autonomy challenge, a drone challenge, AMD hardware and MLH Best Use of Arm, and KH VII had Best Hardware Hack. One ESP32/Arduino build can enter the embedded prize plus 1–2 sponsor or MLH tracks.
2. **Build "sensor + AI brain + dashboard."** Use an ESP32 or Arduino with 2–3 sensors and one actuator (haptics, servo or LED), stream over WiFi or serial to a Python backend with an LLM, and show a live web dashboard.
3. **Bring your own boards and power.** The MLH lab has only about 9 Pis, 12 Arduinos, 3 ultrasonic sensors and 4 servos, with your ID held as collateral. Bring ESP32s, LiPo batteries with a charger and buck converters, and have a 3D-printed or laser-cut enclosure planned before the event.
4. **Freeze the hardware at hour ~20.** Wire the demo path, keep a recorded-video fallback, and spend the last hours on the enclosure and the judge-hands-on moment.
5. **An accessibility or safety story plus a hands-on demo is the most reliable winning combination,** but pick a fresh user. Canes and blind-navigation devices are heavily saturated (Shepherd, Walkie Talkie, PulseWalk, iPalo, EchoAI).

## 4. Open questions / next searches
- **Pages that failed:**
  - HackPrinceton Fall 2024 gallery returned HTTP 403.
  - hackgt-11, mhacks-17, calhacks-10 and calhacks12 slugs returned 404, so the real slugs are unknown.
  - 2 project pages in batch 1 and 7 in batch 2 did not return HTTP 200, so their prizes are unverified.
  - The Happy Head description failed to load; its row uses Devpost tags and tagline only.
  - The guide.mlh.com "hardware-labs-and-additional-resources" page returned only navigation.
- **Hack the North 2025 "Finalists":** ChessMate (motorized chess board, https://devpost.com/software/chessmate-nwygvq) and S-KBD67 (Nerf-gun FPS controller with ESP32 + MPU6050, https://devpost.com/software/s-kbd67) also carry this badge; I logged only DUM-E.
- **Not logged for space:**
  - BallAR (Cal Hacks 12, Snap Spectacles + ESP32 electro-stimulation): https://devpost.com/software/ballar
  - Red Lamp and Wattson (UofTHacks 13, LeLamp robot track): https://devpost.com/software/red-lamp
  - Aerovision Pro Max and Project LearnSafe (PennApps XXIV, Viam robotics)
  - Dotify (HackGT 12, Gadget Gallery 2nd, Arduino + servo): https://devpost.com/software/dotify
- **Once sponsor tracks drop:**
  - If Pheratech returns, study ZPM (KH VIII ROS2 winner, logged elsewhere): https://devpost.com/software/zero-panic-in-movement-zpm
  - If NextEra returns, note that all 3 drone-challenge winners were OR-Tools route optimizers (GridWatch, DronePath): https://knighthacksviii.devpost.com/project-gallery
  - For an AMD/ROCm track, compare EchoAI and Restful Knights.
- **Unscraped galleries worth checking:** HackMIT 2024/2025 (only hack-mit-2023 is on Devpost), MHacks 2024/2025, HackGT 11, Cal Hacks 10, and hardware-only events (MakeHarvard, Hack the North hardware tracks, IEEE hackathons).
