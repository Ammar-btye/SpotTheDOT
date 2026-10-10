# Winners: Fintech and finance sponsor challenges (2023–2026)
_Researched 2026-10-09 · sources: Devpost hackathon pages (prize text) and project pages ("Winner" label plus prize name), crawled with curl_

## 1. Scope
- **Method:** I used the Devpost hackathon search API to find about 120 collegiate events from 2023 to 2026. For each event I scraped the prize list on its homepage to get the finance-sponsor prompts. Then I crawled every winner in each project gallery and kept the projects whose page shows "Winner" next to a finance-related prize.
- **Galleries crawled (2023–26 editions):** Bitcamp, Technica, hackUMBC, VTHacks, HackGT, HackPrinceton, HackUTD, ShellHacks, Hacklytics, HackIllinois, HackNYU, TAMUhack, HackTX, MHacks, SwampHacks, HackRU, HackHarvard, HackMIT, TreeHacks, Hack the North, Cal Hacks, HackNC, HackRice, SteelHacks, HackPSU, RevolutionUC, DubHacks, LA Hacks, WildHacks, Hack@Brown, HopHacks, CUhackit, HackUSF, Hackabull, UofTHacks, HackViolet, HenHacks, YHack, HackKU, HackSMU, RowdyHacks, BoilerMake, Kent Hack Enough, Knight Hacks VI/VII/VIII, BloomKnights, and The FinTech Hackathon.
- **Skipped:**
  - Projects already logged by other agents: CreditShield, Overphone, Money Mentor AI, FinScope, FraudGuard, Agent Zero, Halo, cryptX, Pay Pals, BudgetBuddy.
  - MLH's "Best DEI/Accessibility Hack sponsored by Fidelity". It is a generic MLH prize, not a finance prompt.
  - JPMorgan, Citadel and Jane Street. I found no Devpost sponsor prizes from them. JPMorgan runs its own Code for Good event off Devpost.

## 2. Winners table
| Name | Hackathon | Prize/track | What it does | Stack | Repo | Source URL |
|---|---|---|---|---|---|---|
| OttoTrade | BloomKnights 2026 (Knight Hacks, UCF) | Best Fintech Hack [Bloomberg] | Links world news to your portfolio to explain why stocks move | React, Vite, Supabase, Gemini API, TradingView API | — (demo ottotrade.vercel.app) | https://devpost.com/software/ottotrade |
| H2A Bank | ShellHacks 2024 | BNY AI-powered Financial Fraud Detection | Flags and reports suspicious transactions with SQL plus an LLM | Flask, Python, SQL, OpenAI | https://github.com/z3nL/h2a | https://devpost.com/software/h2a-bank |
| SmartCards | ShellHacks 2024 | Capital One | Budgeting add-on that categorizes transactions and suggests investing opportunities | React, Vite, Flask, Express, OpenAI, Kaggle data | https://github.com/mavreyn/smart-cards | https://devpost.com/software/smartcards-qxdusb |
| Clarifina | ShellHacks 2024 | Vanguard | Collaborative AI financial-literacy app | Firebase, AWS (S3, CloudWatch), Express, OpenAI | — | https://devpost.com/software/clarifina |
| The Rat Race | ShellHacks 2025 | State Farm (+ Netflix) | Story game set in a corporate "rat race" that teaches insurance | Next.js, React, Adobe | — | https://devpost.com/software/the-rat-race |
| edgecart. | HackPrinceton Fall 2025 | Best Financial Hack by Capital One (+ YC challenge, Knot TransactionLink) | Grocery-store camera vision for "risk-adjusted target liquidation" | Flask, PyTorch ResNet18, Gemini, Knot API, React | https://github.com/AntoDono/edgecart | https://devpost.com/software/edgecart |
| C2Pay | HackHarvard 2025 | Best Financial Hack by Capital One | Mobile SDK for adaptive MFA on risky payments (device trust, biometrics, C2PA) | React Native/Expo, Stripe, TEE, TypeScript | https://github.com/sofiaal1/C2Pay | https://devpost.com/software/c2pay |
| Visa Verify | HackHarvard 2025 | Visa Truth and Trust Track | Chrome extension that scores online-payment fraud from behavioral biometrics | Chrome extension, Node/Express, JS | https://github.com/HaoChiBao/hackharvard2025 | https://devpost.com/software/visa-verify |
| I'd Rather Scroll | HackGT 12 (2025) | Capital One – Best Financial Hack | "Productive doomscrolling" app | React | — | https://devpost.com/software/i-d-rather-scroll |
| Resale Radar | Technica 2025 | [Capital One] Best Financial Hack | Recommends resale listing prices from scraped category data | Java, FXML | — | https://devpost.com/software/resale-radar |
| InvestyBesty | Technica 2025 | [T. Rowe Price] Investor Education Challenge | GenAI personalized investing tutor | Next.js, Gemini, Alpha Vantage, FMP API, Cloudflare | https://github.com/amansahu205/Technica-2025 | https://devpost.com/software/ohmyfunds-xyz |
| Drift | TAMUhack 2026 | Capital One Challenge | Probabilistic simulator of your financial future | Next.js, Express, Nessie, Gemini, ElevenLabs, NumPy | https://github.com/aadit2805/drift | https://devpost.com/software/pff |
| Sigma Predictor | TAMUhack 2026 | USAA Challenge | GenAI financial predictor ("one standard deviation above the average") | Next.js, MongoDB, Gemini, ElevenLabs | https://github.com/KoalaisMad/TAMUHACK2026 | https://devpost.com/software/sigma-predictor |
| SpaceShare | Hack@Brown 2026 | Visa Custom Track + Capital One Best Financial Hack | "Airbnb of storage": peer-to-peer storage marketplace with payments | React, TypeScript, Tailwind, AWS | https://github.com/Vigneshpeddi/EcoSquare | https://devpost.com/software/spacesquare |
| Velum | HackIllinois 2026 | Best Use of Capital One Nessie | Decentralized encryption to protect user identity | Solana, Nessie, Node, Python, TS | https://github.com/MarcDasilva/HackIllinois | https://devpost.com/software/velum |
| Settlr | MHacks 2026 | Best Use of Nessie @ Capital One | Shared finances for roommates moving cities | Svelte, SpacetimeDB, Nessie API, Python | https://github.com/andrew-oriti18/settlr-mhack26 | https://devpost.com/software/settlr-s4gr9y |
| Black Swan | Hacklytics 2025 | Best Finance Hack (Capital One) | AI market-insight dashboard for uncertain markets | Next.js, Flask, MongoDB, OpenAI, Alpha Vantage | https://github.com/kaustubhbhal/Black-Swan | https://devpost.com/software/black-swan |
| Swipe Coach | HackRice 15 (2025) | Capital One Best Financial Hack | Picks the best cashback card for each purchase and coaches spending | React, Flask, MongoDB, Auth0, Gemini | https://github.com/leo2971998/HackRice25 | https://devpost.com/software/swipe-coach |
| Boilerchain | BoilerMake XI (2024) | Best Fintech Hack (Bloomberg) | Campus cryptocurrency you mine in the browser, with a trading leaderboard | FastAPI, Redis, React, Docker | https://github.com/kambhani/boilerchain | https://devpost.com/software/boilerchain |
| TrustIssues.AI | HackUTD 2025 | Goldman Sachs | Multi-agent vendor onboarding: extract data, verify identity, score risk, human approval | Python, Streamlit, NVIDIA Nemotron, OpenAI SDK | https://github.com/ybavgito/TrustIssues.AI | https://devpost.com/software/coffee-overflow |
| ProDuh! | HackUTD 2025 | PNC Bank | Multi-agent LLM command center for product managers (Jira/ADO) | Google ADK, Gemini, OpenAI, PostgreSQL, GCP | https://github.com/christinaduthie/produh | https://devpost.com/software/produh |
| MirrorAPI | HackUTD 2025 | State Farm | Compares API versions to catch breaking changes | React, TypeScript | https://github.com/ParsaBazrpash/MirrorAPI | https://devpost.com/software/mirror-api |
| Mira Mira on Da Wall | TreeHacks 2026 | [Visa] Generative Edge: Future of Commerce ($10k) | AI smart mirror that recommends outfits and buys items | ElevenLabs, HeyGen, Firecrawl, Google Shopping, MCP, embedded | https://github.com/23jmo/mirrorless | https://devpost.com/software/mira-3xqlos |
| Lullabuy | HackGT 13 (2026) | VISA: Reimagine Shopping ($5k) | Holds a Visa payment until a camera checks baby gear against CPSC/NHTSA recalls | Expo, Gemini, CLIP, MongoDB Atlas Vector Search, MCP | https://github.com/StephenSook/secondhand-safe | https://devpost.com/software/lullabuy |
| Minty: Digital Tooth Fairy | DubHacks '25 | VISA – Play, Pay, Repeat | Kids earn money for brushing their teeth (gamified allowance) | Next.js, Prisma, Postgres, Stripe, Gemini | https://github.com/owenkrause/tfp | https://devpost.com/software/minty-4vcu9m |
| Shomi | HackPrinceton Spring 2026 | KnotAPI: build on purchase data | Shop through iMessage using your purchase history | Knot API, LangChain, SQLite, TS | https://github.com/mitoiscool/shomi-hackprinceton26 | https://devpost.com/software/shomi |
| Money Talks | Hack the North 2025 | RBC InvestEase – Investing for the Future | Upload a card statement; get budgets, insights and an investing roadmap | Next.js, FastAPI, InvestEase API, Martian | https://github.com/KadenDaya/Money-Talks | https://devpost.com/software/money-talks-d93izn |
| QuickVest-SP | HackNC 2025 | Fidelity Open-to-Invest Hack | Gamified investing onboarding with voice AI and reels | React Native/Expo, Supabase, Gemini, OpenAI, ElevenLabs | https://github.com/SupratikPanuganti/quickvest | https://devpost.com/software/quickvest |
| FinDaddy | RevolutionUC 2025 | Fifth Third Sponsor Challenge ($1k) | Financial-literacy and planning dashboard for young adults | Python Dash, Plotly, MongoDB, Gemini | https://github.com/SohumKanojia/RevUC_25.git | https://devpost.com/software/findaddy |
| AllBank | HackUTD 2024 | Goldman Sachs | AI banking companion for unbanked and underbanked users | React Native, Firebase, Gemini | https://github.com/aprajita27/AllBank | https://devpost.com/software/allbank |

**Recurring sponsor prompts.** Text is from the Devpost prize sections.
- **Capital One, "Best Financial Hack"** (the most common finance prize). Seen at Bitcamp 2023–26, Technica 2023–25, HackGT X/12, HackPrinceton 2025, HackHarvard 2025, HackNC 2024–25, HackRice 14–16, HackTX 2023/25, TAMUhack 2025–26, SwampHacks XI, WildHacks 2024, VTHacks 11, HackViolet 2024, Hacklytics 2025, Hack@Brown 2026, ShellHacks 2023–25 and HackUTD 2025.
  - The prompt is "intentionally vague": "innovative payment solution, helping consumers shop smarter, making financing more accessible, or … financial literacy", with Nessie offered as an optional mock-banking API (https://th26.devpost.com).
  - **In 2026 it is turning into "Best Use of Nessie"** (HackIllinois 2026, MHacks 2026, VTHacks 14).
  - ShellHacks runs its own versions: in 2024, GenAI for mobile financial services; in 2025, "Innovate & elevate – Gen AI/blockchain".
- **Bloomberg** has three recurring prizes:
  - "Best Fintech Hack" (BoilerMake XI, BloomKnights 2026). Judged on "originality, potential for impact, and technical difficulty"; personal finance or markets both count.
  - "Most Philanthropic Hack" (Bitcamp 2023/24/26, HopHacks 2024–26).
  - Bloomberg Industry Group AI and legal-data prompts (Technica, Bitcamp).
- **BNY, "AI-powered Financial Fraud Detection System"** (Knight Hacks VII, ShellHacks 2024). Anomaly detection on real-time transactions.
- **OneEthos** at Knight Hacks: "AI for Financial Empowerment" ($4k, Knight Hacks VIII) and "Best Clean Energy Solution" (BloomKnights).
- **State Farm** at ShellHacks 2023–26 and HackUTD. The prompt: make insurance understandable for students (theft, fire, accidents) through tools, gamification or education.
- **HackUTD every year:** three-place tracks from Goldman Sachs, PNC, Fidelity, Fannie Mae, State Farm and Toyota Financial.
- **TAMUhack:** USAA ("transform GenAI output in a novel way before returning it to the user").
- **T. Rowe Price, Investor Education** (Technica, hackUMBC): "we want them to actually understand the concepts and not only create a tool."
- **Visa** is new in 2025–26 and pays the largest finance prizes: TreeHacks 2026 ($10k), HackGT 13 ($5k), HackHarvard 2025, DubHacks 2025, Hack@Brown 2026 and Cal Hacks 12.

## 3. Patterns
- **Consumer money apps with one sharp twist win Capital One.** Examples: card optimization (Swipe Coach), roommate or peer money (Settlr, SpaceShare), a gamified feed (I'd Rather Scroll), security (C2Pay). Judges reward a clear user and a fresh angle over technical depth. Several winners have small stacks (Resale Radar uses Java/FXML; I'd Rather Scroll is React only).
- **Fraud, trust and identity is the second-largest theme.** H2A Bank, Visa Verify, C2Pay, Velum and TrustIssues.AI won it, and so did Knight Hacks VII's BNY winners. Visa's 2025–26 prompts lean toward "trust" and "future of commerce".
- **Real financial APIs signal credibility.** Winners used Nessie (Drift, Settlr, Velum), Knot (edgecart, Shomi), Stripe (Minty, C2Pay), Alpha Vantage, TradingView and RBC InvestEase.
- **Gemini dominates 2025–26 finance winners, often alongside ElevenLabs voice.** Examples: OttoTrade, Drift, Swipe Coach, Lullabuy, QuickVest-SP, InvestyBesty, FinDaddy. Mixing MLH prize tech into a finance project is normal.
- **Big Visa money goes to commerce in the physical world.** A smart mirror (Mira) and a camera-gated payment escrow (Lullabuy) won. Neither was a dashboard.
- **Enterprise sponsors at HackUTD reward multi-agent workflow tools,** not consumer apps: TrustIssues.AI for KYC onboarding, ProDuh! for PM agents, MirrorAPI for API diffs.
- **Prize stacking is common.** edgecart won Capital One, YC and Knot. SpaceShare won Visa and Capital One. The Rat Race won State Farm and Netflix. PAWS at TAMUhack 2025 won USAA and Capital One.
- **Education prompts (T. Rowe, Fidelity, RBC, Fifth Third, Vanguard, OneEthos) reward learning loops** for young adults, not just trackers. Examples: InvestyBesty, QuickVest-SP, Money Talks, FinDaddy.

**Takeaways for our Knight Hacks project**
1. Knight Hacks keeps bringing in a finance sponsor: BNY fraud at Knight Hacks VII, OneEthos "AI for Financial Empowerment" ($4k) at VIII, and Bloomberg Fintech plus OneEthos at BloomKnights 2026. Plan a finance-capable core that can be framed as either empowerment/literacy or fraud/trust.
2. Pick one specific user and one twist, such as roommates, resale sellers or new investors. Wire in a real or mock financial API (Nessie, Plaid sandbox, Stripe test mode, market data) so the demo moves real-looking money.
3. Add a trust or fraud layer (anomaly score, explained alerts). It lets one project qualify for BNY-style, Visa "trust" and Capital One prompts at the same time.
4. Build for stacking: use Gemini and ElevenLabs on purpose (MLH prizes) inside the finance project, and keep a live, deployed URL.
5. If the prompt is about education, show that users actually learn something (a quiz, a simulation, or an explanation of why), not only a dashboard.

## 4. Open questions / next searches
- **Hacklytics 2024** (https://hacklytics-2024.devpost.com/project-gallery): my crawl found 0 winners. Unverified.
- **HackMTY 2026** (https://hackmty-26.devpost.com) lists Capital One and Banorte 1st–3rd prizes, but the gallery showed no winners yet.
- **Knight Hacks VIII:** the OneEthos prompt body only lists prizes. Look for the full brief in the event's Discord or Notion. OneEthos winners are already logged in winners-knighthacks-history.
- **HackUTD 2025:** the Goldman, PNC, State Farm and Toyota Financial prize texts list only prizes. The challenge briefs (KYC onboarding, PM agents, API versioning, inferred from winners) are probably in HackUTD's sponsor docs.
- **ShellHacks 2026** (https://shellhacks-2026.devpost.com): State Farm winner Halo is already logged. Worth checking for other finance sponsors.
- **JPMorgan Code for Good, Citadel and Jane Street:** nothing on Devpost. Look at https://careers.jpmorgan.com (Code for Good) if JPM sponsors.
- **Deep-dive leads once tracks drop:**
  - Nessie API docs: http://api.nessieisreal.com
  - Knot API prompt: https://hackprinceton-spring-26.devpost.com
  - Visa TreeHacks 2026 track: https://treehacks-2026.devpost.com
  - Bloomberg Fintech prompt: https://boilermake-xi.devpost.com
  - BloomKnights: https://bloomknights.devpost.com
