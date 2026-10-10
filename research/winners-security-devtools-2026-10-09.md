# Winners: Cybersecurity, Privacy and Developer Tools
_Researched 2026-10-09 · sources: Devpost project galleries and project pages (winner badges plus the "Winner" prize lines on each project page), pulled through the Devpost gallery HTML and the `devpost.com/software/search` JSON_

## 1. Scope
**Method.** I scraped every winner-badged project from 55 Devpost galleries (about 1,570 winners). Then I fetched each winner's project page for its prize names, "Built With" tags and "Try it out" links, and filtered on prize names and taglines (security, cyber, forensics, privacy, fraud, "Developer Tool", Warp, 1Password, Nord). Every row below comes from the project page's own "Winner" prize line.

**Galleries visited** (`https://<slug>.devpost.com/project-gallery`):
- **Florida:** knighthacksviii, knight-hacks-vii, knight-hacks-vi, shellhacks-2023, shellhacks2024, shellhacks2025, shellhacks-2026, swamphacksx, swamphacks-xi
- **Other in-person:** treehacks-2024/2025/2026, cal-hacks-11-0, cal-hacks-12-0, hack-mit-2023, hackharvard-2023/2024, hackthenorth2023/2026, la-hacks-2024/2026, hackillinois-2025/2026, hackgt-11-circus-of-invention, hackgt-12, pennapps-xxv, hacktx-2024, hacktx2025, uofthacks-11/13, hophacks-fall-2025, hackumass-xii/xiii, hack-brown-2025, madhacks-fall-2025, boilermake-xii, hacknc-2024/2025, hackru-fall-2024/2025, bitcamp2024/2025, bitcamp-2026, hackprinceton-fall-2025, hackprinceton-spring-26, hacklytics2025, hacklytics-2026, mhacks-2024, hackrice-15
- **Online:** pangea-securathon, pangea-securathon-showdown, healthandwealth (Pangea), authorizedtoact (Auth0), github-copilot, gitlab (GitLab AI Hackathon 2026)

**Skipped:** projects already logged by other agents (Nara, dockerc, Krates, HawkWatch, Systema, Vertex A11y, Forens.tech area). I also skipped ETHGlobal, lablab.ai and Kaggle, because the Devpost yield was enough. The Devpost project pages returned 403 to WebFetch, but curl worked.

**Knight Hacks context.** The prize lists for Knight Hacks VI, VII and VIII contain **no** security track. At Knight Hacks, security-flavored projects won only through sponsor challenges: BNY fraud detection, AMD and Auritas.

## 2. Winners table
| Name | Hackathon | Prize/track | What it does | Stack | Repo | Source URL |
|---|---|---|---|---|---|---|
| codebreaker | LA Hacks 2026 | **1st Overall**; Cognition challenge | Agent platform plus its own CVE benchmark (ECVE-Bench); finds, validates and auto-patches vulns | Devin, Modal, Cloudflare, React, TS | https://github.com/KevinWu098/codebreaker | https://devpost.com/software/codebreaker-la |
| Alias | UofTHacks 13 (2026) | 1Password: Best Security Hack | Decompiles a .exe (Ghidra + LLM4Decompile), explains its behavior, verdict safe/suspicious | pyghidra, Gemini, FastAPI, Next.js | https://github.com/Leo-Zh9/uofthacks13 | https://devpost.com/software/decompiler |
| Phisherman | Hacklytics 2025 | Best Cybersecurity Hack | AI phishing and deepfake simulations to train employees | React, TS, Python, MongoDB | https://github.com/oscarzhang228/Phisherman | https://devpost.com/software/phisherman-4x1vw5 |
| minutemesh | HackUMass XIII (2025) | Most Impactful Cybersecurity Hack | Pentesting toolkit for Meshtastic mesh radio networks | C/C++, PlatformIO, protobuf, AES | https://github.com/jordaeday/minutemesh | https://devpost.com/software/minutemesh |
| Obscurafy | HackUMass XIII (2025) | Cybersecurity: Best Data Protection | On-device iOS detection of personal info in screenshots before sharing | Swift, CoreML, PyTorch, Gemini | https://github.com/AlexanderMcGreevy/Obscurafy | https://devpost.com/software/vaulteye |
| Infraflow | HackUMass XII (2024) | Best Security Hack; MLH Terraform | Visual builder for cloud infrastructure that outputs Terraform | Next, Terraform, AWS/Azure/GCP | https://github.com/weebao/infraflow | https://devpost.com/software/infraflow |
| 3s Spacial Awareness Assessment | HackRU Fall 2024 | Best Security Hack (Nord Security) | Cognitive tests encrypted with CKKS homomorphic encryption; analytics on ciphertext | Python, Flask, CKKS | https://github.com/Binimal101/3sSpacialAwarenessAssessment | https://devpost.com/software/3s-spacial-awareness-assessment |
| Hiding in Plain Sight | Bitcamp 2025 | Best Cybersecurity Track Hack | Steganography forensics: finds hidden messages in images | Flask, Python, JS | https://github.com/braynguyen/Hiding-in-Plain-Sight | https://devpost.com/software/hiding-in-plain-sight |
| KeyCatchAI | Bitcamp 2024 | Best Digital Forensics (Cipher Tech) | Acoustic side-channel: recovers keystrokes from keyboard audio | PyTorch, librosa, Flutter, Flask | https://github.com/3752V/KeyCatchAI | https://devpost.com/software/keycatchai |
| QWave | Bitcamp 2026 | Best Digital Forensics (Cipher Tech) | Detects attacks hidden in audio using quantum-noise features | Qiskit, Python, Streamlit, Cloud Run | https://github.com/shreya222mishra/bitcamp-2026 | https://devpost.com/software/quanterp |
| Watchful.AI | PennApps XXV (2024) | Best Privacy/Security Hack; Most Technically Complex | Camera agent that watches for school-shooting threats 24/7 | GPT-4o, Roboflow, OpenCV, Next.js, ChromaDB | https://github.com/Yatsz/PennApps2024 | https://devpost.com/software/watchful-ai-u5id0v |
| Zorg | TreeHacks 2024 | Blockchain & Security Grand Prize | Encrypted, decentralized patient health records | Solidity, Hardhat, Next, Flask, InterSystems | https://github.com/rohan-patra/Zorg | https://devpost.com/software/zorg-7ubd4x |
| Gallop | TreeHacks 2026 | Elastic: Best end-to-end agentic system | Multi-agent platform that detects and stops intrusions in real time | eBPF, Rust, Elasticsearch, Next.js, OpenAI | https://github.com/Eth007/gallop | https://devpost.com/software/gallop |
| ShadowGuard | TreeHacks 2026 | OpenEvidence Healthcare Track Grand Prize | Network-layer AI firewall that redacts patient data before it leaves | mitmproxy, Python, Node, OpenAI, D3 | https://github.com/shamanthak-hegde/ShadowGuard | https://devpost.com/software/shadowguard-l6yv7p |
| GHOST | Pangea Securathon Showdown (2024, online) | Grand Prize | Chatbot that redacts and sanitizes what users type so it doesn't leak | Pangea APIs, Streamlit, Cohere, Gemini | https://github.com/dotAadarsh/ghost | https://devpost.com/software/ghost-rtzwjs |
| Mind Your Prompt | ShellHacks 2026 | Assurant | Browser extension that flags private data before you paste it into an AI chat | Transformers.js/ONNX BERT, WXT, Next.js, Snowflake Cortex | https://github.com/krishnatejasai/ShellHacks_2026 | https://devpost.com/software/mind-your-prompt-prompt-shield |
| CreditShield | Knight Hacks VII (2024) | BNY Mellon: AI Financial Fraud Detection | Real-time fraud monitoring of bank transactions | Kafka, scikit-learn, React, Solidity, MongoDB | https://github.com/parkerblume/fraud-detection | https://devpost.com/software/creditshield |
| Sora2Detector | Knight Hacks VIII (2025) | AMD: Best use of AMD HW/SW | Multi-phase detector for AI-generated (Sora 2) video | Python, AMD ROCm | https://github.com/LeeMarshall1113/Sora2Detector | https://devpost.com/software/sora2detector |
| ShellHacked | ShellHacks 2024 | Break Through Tech | Security-awareness challenges played entirely in the terminal | Go, charm.sh, SQLite, ngrok | — | https://devpost.com/software/shellhacked |
| Cloud Vault | ShellHacks 2024 | Wolfi OS Container Security | Containerized secure file uploader on Chainguard images | Chainguard, Docker, Flask | https://github.com/lain561/CloudVault | https://devpost.com/software/cloud-vault |
| T-Error | HackHarvard 2024 | Best Developer Tool | Custom C++ shell captures stderr; team dashboard of error trends plus runnable docs | C++, Node, MongoDB, React | https://github.com/hellolol2016/hackharvard2024 | https://devpost.com/software/terror |
| BlackBox Studio | HackIllinois 2025 | Best Developer Tool | Block-based visual programming for any language | Rust (Actix), React Flow | https://github.com/Dandandooo/BlackBox-Studio | https://devpost.com/software/blackbox-studio |
| ARDB: AR Debugger | Hack the North 2026 | Warp: Best Developer Tool | AR overlay showing live diagnostics of embedded hardware | ESP32, MQTT, WebXR, Raspberry Pi | https://github.com/PyneKoyne/AR-Debugger | https://devpost.com/software/ardb |
| InfraBlocks | HackGT 12 (2025) | Warp: Best Developer Tool | Drag-and-drop cloud-service design with AI | Next.js, xyflow, OpenAI, Cedar-OS | https://github.com/Carbinski/InfraBlocks | https://devpost.com/software/infrablocks |
| CodeScribe | HackRice 15 (2025) | Warp Best Developer Tool; Productivity & Education Track | VS Code extension: highlight code to get its purpose, history and impact | TypeScript, Gemini, VS Code API | https://github.com/justi-lai/HackRice2025 | https://devpost.com/software/codex-iqhao5 |
| Autopsy | LA Hacks 2026 | **3rd Overall**; Cognition challenge | "Black-box recorder" for coding agents; turns failures into guardrails, one-line install | FastAPI, pgvector, Next.js, Devin/opencode, Cloudflare | https://github.com/balebbae/Autopsy | https://devpost.com/software/autopsy-zq5d84 |
| Repro | ShellHacks 2026 | Microsoft | Repo diagnostic and repair: secrets, deps and static analysis plus AI fixes, MCP | gitleaks, osv-scanner, semgrep, Gemini, MCP, tRPC | — | https://devpost.com/software/repro-h6gq70 |
| GraphDev | GitLab AI Hackathon (2026, online) | Most Impactful on GitLab & Anthropic: Grand Prize | Codebase-as-semantic-graph; structural impact analysis on every MR | GitLab Duo Agent Platform, Claude, FastAPI, Next.js | https://gitlab.com/gitlab-ai-hackathon/participants/35368827 | https://devpost.com/software/graphdev |
| Change Scribe | Accelerate App Dev with GitHub Copilot (2024–25, online) | Best Use of GitHub Copilot | VS Code extension that writes semantic changelogs from commits | TypeScript, VS Code API, Azure OpenAI | — (Marketplace listing) | https://devpost.com/software/change-scribe |
| SuperMAN | HackTX 2024 | Best LLM Hack; Best Pitch; Best Use of Intel AI | Local LLM that turns natural language into terminal commands | Ollama, Llama 3.2, ipex-llm, Python | https://github.com/praneelseth/superMAN | https://devpost.com/software/superman-2wigou |

**30 winners logged.** Other confirmed winners left out for space:
- **Security:** Deqo and Cipher AI (Hacklytics 2025, 2nd and 3rd in Cybersecurity); Moth Challenege (Bitcamp 2024 Cybersecurity Track); Miraculous Fuzzer (HackUMass XII, Nord add-on); ProtestLink (TreeHacks 2025, Delve Most Secure App); Cyberwright (MHacks 2024)
- **Developer tools:** Ensemble and GenHint (MHacks 2024 Warp); CodeFusion and Swarm AI (TreeHacks 2025 dev-tool prizes); Unreal EngJam (Cal Hacks 11 Warp); Gitdefender (GitLab Grand Prize); Department of Incidents (Auth0 Grand Prize)

## 3. Patterns
**What wins in security**
- **Offense-as-defense with AI agents is the 2026 meta.**
  - codebreaker took **1st Overall** at LA Hacks 2026 (out of about 65 winners), with an agent that finds, validates and patches CVEs.
  - Gallop (eBPF intrusion response), Nara (logged elsewhere) and Alias (decompile, then explain) won in the same season.
  - Judges reward a *closed loop* (detect, prove, fix) over a dashboard. codebreaker also shipped its own benchmark (ECVE-Bench) with a leaderboard, which reads as rigor.
- **Privacy firewalls in front of LLMs.** The newest privacy pattern is to intercept data *before* it reaches an AI: ShadowGuard (a mitmproxy-based PHI redactor) won a TreeHacks *healthcare* grand prize, along with Mind Your Prompt (ShellHacks 2026), GHOST (Pangea) and Obscurafy. Pairing security with a domain track (health, finance) let these compete for bigger prizes than a security-only pitch could.
- **Novel side channels and forensics win the niche forensics prizes.** Examples: KeyCatchAI (keystrokes from audio), QWave (attacks hidden in audio), Hiding in Plain Sight and minutemesh (radio mesh pentesting). They pair hardware or signals with a memorable "whoa" demo.
- **Phishing and fraud are crowded but still win when tied to a sponsor brief.** CreditShield won the BNY fraud challenge at Knight Hacks VII, and FraudGuard and H2A Bank won the same BNY brief at ShellHacks 2024. Phisherman framed phishing as *training simulations* rather than detection.
- **Where security prizes exist.**
  - Dedicated tracks: Bitcamp (Cybersecurity plus Cipher Tech forensics), HackUMass (three cybersecurity prizes), Hacklytics (1st through 3rd in Cybersecurity), PennApps (Privacy/Security track), UofTHacks (1Password) and HackRU (Nord).
  - In Florida, security wins came through sponsor briefs and "Wolfi/Chainguard container security."

**What wins in developer tools**
- **Warp's "Best Developer Tool" is the most consistent dev-tools prize on the circuit.** It appeared at TreeHacks 2024 and 2025, Cal Hacks 11, MHacks 2024, Hack@Brown 2025, HackRice 15, HackGT 12 and Hack the North 2026 (a few are logged in the table). HackHarvard and HackIllinois also ran their own "Best Developer Tool" prize.
- **Winners live where developers already work.** Examples:
  - The terminal: T-Error, SuperMAN, ShellHacked
  - VS Code: CodeScribe, Change Scribe, GenHint
  - Git/MR pipelines: GraphDev, Repro
  - A one-line installer: Autopsy (`curl … | bash`)
- **Tools for AI coding agents are the 2026 frontier.** Autopsy (3rd Overall, LA Hacks), Lore IDE and Litho all won the Cognition challenge, and Monolith and Longshot won Modal sandbox prizes at TreeHacks 2026. The pitch is memory, guardrails or observability *for agents*, not another chat-with-your-code app.
- **Hardware-flavored dev tools stand out.** ARDB (AR debugging for ESP32) beat software-only entries for Warp at Hack the North 2026.
- **Recurring stack:** Gemini/Claude/OpenAI as the reasoning layer, FastAPI plus Next.js, Rust for performance claims (Gallop, BlackBox Studio, Cyberwright), and real security tooling (semgrep, gitleaks, osv-scanner, Ghidra, mitmproxy, eBPF) rather than "AI decides everything."

**Takeaways for our Knight Hacks project**
1. **Don't count on a security track at Knight Hacks.** VI through VIII had none. Build a security or privacy core that can also be pitched to a sponsor challenge (fintech fraud, AMD/edge AI, legal or health data), the way CreditShield and Sora2Detector won.
2. **Close the loop and show proof.** Detect, then exploit or validate, then patch or redact, live on stage. Back it with real tools (semgrep, Ghidra, mitmproxy) plus an LLM explainer, and if possible a small benchmark number, as codebreaker did.
3. **A privacy firewall for LLMs is a timely, demo-friendly angle** (ShadowGuard, Mind Your Prompt, GHOST). It fits health, legal and finance sponsors and any "Best AI" prize.
4. **If we go dev-tools, ship it where devs live** (CLI one-liner, VS Code extension or Git hook) and target agent observability or guardrails. Watch for a Warp "Best Developer Tool" or Cognition/Devin prize in the sponsor list.
5. **A physical or signal twist differentiates** (KeyCatchAI, QWave, ARDB, minutemesh). UCF's Hack@UCF and CCDC culture makes a red-team or forensics demo land with local judges.

## 4. Open questions / next searches
- WebFetch returned **403** on Devpost project pages (curl worked), so descriptions were read only for codebreaker, Alias, Autopsy and T-Error. The others are summarized from taglines and tags.
- The `devpost.com/software/search?query=…&order_by=popular` JSON endpoint works for keyword sweeps, but winners are sparse in it. The galleries are the better route.
- The Hack@Brown 2025 Warp winner "Codex" has an unclear tagline, so it was not logged: https://devpost.com/software/codex-r2toqu
- Not yet checked: ETHGlobal security and ZK finalists, lablab.ai security hackathons, MLH "Hack@UCF"-style CTF events (not on Devpost), and HackGT 13 / Hacklytics 2026 security winners (Hacklytics 2026 gallery scraped, no security-named prize found).
- Deep-dive leads once sponsor tracks drop:
  - **Fintech fraud:** BNY brief winners at Knight Hacks VII and ShellHacks 2024 (https://knight-hacks-vii.devpost.com/project-gallery, https://shellhacks2024.devpost.com/project-gallery)
  - **Security track structure:** Bitcamp 2026 Cipher Tech forensics winners (https://bitcamp-2026.devpost.com/project-gallery) and HackUMass XIII Cybersecurity (https://hackumass-xiii.devpost.com/project-gallery)
  - **Dev tools / agents:** LA Hacks 2026 Cognition winners (https://la-hacks-2026.devpost.com/project-gallery) and GitLab AI Hackathon (https://gitlab.devpost.com/project-gallery)
  - **Auth/identity:** Auth0 "Authorized to Act" (https://authorizedtoact.devpost.com/project-gallery)
