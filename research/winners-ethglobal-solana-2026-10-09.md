# Winners: ETHGlobal finalists, Solana Colosseum and MLH "Best Use of Solana"
_Researched 2026-10-09 · sources: ethglobal.com/showcase project pages, The Block, crypto.news, Flow blog, TechFlow, CSULB news, blog.colosseum.com, solana.com/news, Devpost project pages (pulled through the Devpost search JSON)_

## 1. Scope
**Visited:**
- ETHGlobal showcase: https://ethglobal.com/showcase?events=bangkok (listing), plus project pages /showcase/zubernetes-zk8s-vvchq, /daogenie-nha62, /bouncer-ai-1sd06, /enshell-6t95y and /corpus-j7an5
- Press:
  - Bangkok 2024 finalists: https://www.theblock.co/post/326975/ethglobal-hackathons-10-finalists-showcase-ai-agents-crypto-games-dao-tools-and-more
  - Cannes 2026 finalists: https://crypto.news/ai-agents-privacy-and-prediction-markets-define-ethglobal-cannes-2026-finalists/
  - Flow at Bangkok: https://flow.com/post/flow-makes-record-breaking-appearance-at-ethglobal-bangkok
  - SF 2024 finalists: https://www.techflowpost.com/en-US/newsletter/61916
  - OmniAgent at ETHGlobal NY: https://www.csulb.edu/node/618036
- Solana:
  - Breakout winners: https://blog.colosseum.com/announcing-the-winners-of-the-solana-breakout-hackathon/
  - Cypherpunk winners: https://blog.colosseum.com/announcing-the-winners-of-the-solana-cypherpunk-hackathon/
  - Radar winners: https://solana.com/news/solana-radar-winners
  - MLH x Solana program: https://blog.mlh.com/mlh-drives-blockchain-education-for-student-developers-with-solana-12-09-2025
- Devpost: `devpost.com/software/search?query=solana|phantom|anchor|spl token|solana pay` (about 60 result pages). For each winner page I checked that the prize label literally says "Best Use of Solana".

**Skipped:**
- Already logged elsewhere (see winners-mlh-sponsor-prizes): MomentumX (ShellHacks 2026), Rescu (HackGT 13), Versus/hth (Hack the Hill III) and Mint (hackUMBC 2026).
- Solana-tagged Devpost winners whose prize was not Solana: T-Cell, PledgeCheck, Hurricane Week, Pixel Cat Arena and HackOdds.

## 2. Winners table
### ETHGlobal (finalist = top ~10 of 200–700 projects)
| Name | Hackathon | Prize/track | What it does | Stack | Repo | Source URL |
|---|---|---|---|---|---|---|
| Zubernetes (ZK8S) | ETHGlobal Bangkok 2024 | Finalist; Blockscout Big Pool; Phala Best General Use Case | TEE + ZK container orchestrator (SP1 proofs of execution traces in SGX) | Next.js, Solidity/Foundry, FastAPI, Rust/Go, Gramine, Intel SGX, Phala Dstack | https://github.com/mnm458/zubernetes-monorepo | https://ethglobal.com/showcase/zubernetes-zk8s-vvchq |
| DAOGenie | ETHGlobal Bangkok 2024 | Finalist; Flow Most Killer App 1st; Linea; Hedera; Rome 3rd | DAO whose votes trigger AI agents that do real-world tasks (purchases, donations) | t3/Next.js, zod, Dynamic wallet, wagmi, Hardhat, Playwright agent, Tesseract OCR | https://github.com/tkeith/daogenie | https://ethglobal.com/showcase/daogenie-nha62 |
| Industry.ai | ETHGlobal Bangkok 2024 | Finalist | Four specialised AI agents collaborate on complex on-chain operations | — | — | https://www.theblock.co/post/326975/ethglobal-hackathons-10-finalists-showcase-ai-agents-crypto-games-dao-tools-and-more |
| MiniDAO | ETHGlobal Bangkok 2024 | Finalist | DAO inside Telegram; the bot holds a wallet controlled by group members | Telegram bot | — | https://www.theblock.co/post/326975/ethglobal-hackathons-10-finalists-showcase-ai-agents-crypto-games-dao-tools-and-more |
| LootGO | ETHGlobal Bangkok 2024 | Finalist; Flow Best Gaming | Walk-to-earn memecoin hunts | Flow | — | https://flow.com/post/flow-makes-record-breaking-appearance-at-ethglobal-bangkok |
| Metaloot | ETHGlobal Bangkok 2024 | Finalist; Flow Best Gaming | Launchpad that connects games to Flow with cross-game item ownership | Flow | — | https://flow.com/post/flow-makes-record-breaking-appearance-at-ethglobal-bangkok |
| UniV4Backtester | ETHGlobal SF 2024 | Finalist (TechFlow: "first place by Uniswap Foundation") | Replays UniV3 swaps/mints/burns to backtest hypothetical Uniswap v4 positions | — | — | https://www.techflowpost.com/en-US/newsletter/61916 |
| bouncerAI | Agentic Ethereum 2025 (async) | Finalist (10 of 518) | Token launchpad where an AI "bouncer" interviews buyers for vibe and knowledge before allowing purchase | Next.js/Vercel, Node/Express/Redis, Foundry on Arbitrum, Supabase, LangChain on Autonome, Privy | https://github.com/GiantDole/ethglobal_agent | https://ethglobal.com/showcase/bouncer-ai-1sd06 |
| OmniAgent | ETHGlobal New York | 1st, Saga partner track | AI-first DAO governance: drafts proposals, plans treasury strategy, executes on-chain | — | — | https://www.csulb.edu/node/618036 |
| ENShell | ETHGlobal Cannes 2026 | Finalist; Chainlink Best CRE workflow | On-chain firewall between AI agent intent and execution; Claude scores each action as approve/escalate/block | Solidity AgentFirewall, ECIES-encrypted SDK, Chainlink CRE, Claude, ENS, CLI | https://github.com/0xenshell/contract | https://ethglobal.com/showcase/enshell-6t95y |
| Corpus | ETHGlobal Cannes 2026 | Finalist | Turns a product into an autonomous "agent corporation" that runs GTM and earns; tokenised governance | Next.js, Stagehand + Chrome agent, Hedera HTS, Circle MPC wallets + x402 nanopayments, World ID | https://github.com/spock-mark1/corpus-protocol | https://ethglobal.com/showcase/corpus-j7an5 |
| DIVE | ETHGlobal Cannes 2026 | Finalist | AI agent swarm verifies real-world truth for prediction-market settlement | Multi-agent oracle | — | https://crypto.news/ai-agents-privacy-and-prediction-markets-define-ethglobal-cannes-2026-finalists/ |
| VEIL VPN | ETHGlobal Cannes 2026 | Finalist | Pay-as-you-go VPN that proves it keeps no logs | Anonymous credentials, ZK attestations | — | https://crypto.news/ai-agents-privacy-and-prediction-markets-define-ethglobal-cannes-2026-finalists/ |

### Solana: Colosseum (online, 1,300–1,600 submissions)
| Name | Hackathon | Prize/track | What it does | Stack | Repo | Source URL |
|---|---|---|---|---|---|---|
| Reflect | Solana Radar (2024) | Grand Champion, $50k | Hedge-backed stablecoin currency exchange (delta-neutral) | Solana | — | https://solana.com/news/solana-radar-winners |
| TapeDrive | Solana Breakout (2025) | Grand Champion, $50k | Decentralised storage network that pays you to store data | Solana | — | https://blog.colosseum.com/announcing-the-winners-of-the-solana-breakout-hackathon/ |
| Latinum | Solana Breakout (2025) | AI track 1st, $25k | Payment middleware so MCP server builders get paid | Solana, MCP | — | https://blog.colosseum.com/announcing-the-winners-of-the-solana-breakout-hackathon/ |
| Unruggable | Solana Cypherpunk (2025) | Grand Champion, $30k | Solana-native hardware wallet + companion app | Solana, hardware | — | https://blog.colosseum.com/announcing-the-winners-of-the-solana-cypherpunk-hackathon/ |
| MCPay | Solana Cypherpunk (2025) | Stablecoin track 1st, $25k | Open payment infrastructure connecting MCP and x402 | Solana, MCP, x402 | — | https://blog.colosseum.com/announcing-the-winners-of-the-solana-cypherpunk-hackathon/ |

### Solana: MLH "Best Use of Solana" and other Solana-sponsor wins at student hackathons (Devpost)
| Name | Hackathon | Prize/track | What it does | Stack | Repo | Source URL |
|---|---|---|---|---|---|---|
| Settlers of Solana | Hack the North 2026 | HTN Finalist; Solana: Best Use of Solana and Badge Hack | Swarm of AI agents simulates a free-market economy on Solana | Rust, JS, Claude, OpenAI, Codex, Baseten | https://github.com/leakyhose/agent-economy | https://devpost.com/software/_solanasim |
| burn402 | VTHacks 14 | [MLH] Best Use of Solana | Agent pays for its own compute (x402) to train custom models; verifiable via Arweave + ANS | Solana, x402, A2A, Arweave | https://github.com/aykk/burn402 | https://devpost.com/software/burn402 |
| Nomad | JAMHacks 10 | Best Use of Solana | "Passports" for AI agents: agent authentication on Solana | Anchor/Rust, TS, Fastify, tweetnacl | https://github.com/michaelmazilu/Nomad | https://devpost.com/software/nomad-nrgx3l |
| Solace | AI Hackfest | [MLH] Best Use of Solana | Solana wallet driven by plain-English commands; AI guard scans each tx; self-rebalancing portfolio | Next.js, Claude, shadcn, Solana | https://github.com/Nucleon2/AI-hackfest-AI-agent-wallet | https://devpost.com/software/solace-gljbon |
| ReliefPool | StormHacks 2026 | [MLH] Best Use of Solana | Real-time quake data + ML assess tsunami risk and auto-release relief funds on Solana | Rust, Python, TS | https://github.com/manandrew-dev/ReliefPool | https://devpost.com/software/reliefpool |
| BackFill | Gator Quant Hacks (UF) | MLH Best Use of Solana | Turns FDA drug shortages into trading signals on competitors that can fill the gap | Python/pandas, TimescaleDB/Tiger Data, Snowflake, Gemini, Vultr, Solana | https://github.com/AIForge10/BackFill | https://devpost.com/software/backfill-1kpq2o |
| CampusPup | Hackabull VII (USF) | [MLH] Best Use of Solana + [MLH] Auth0 AI Agents | Virtual-puppy stress relief for students | Solana, Auth0 AI, Snowflake, MongoDB, Gemma, ElevenLabs | https://github.com/hlee18lee46/campuspup | https://devpost.com/software/campuspup |
| CareLess | Pearl Hacks 2026 | 3rd overall + [MLH] Solana + Fidelity Finance For All 2nd | "Where Caring Meets Transparency" | React, Gemini, ElevenLabs, Vultr, Solana | https://github.com/purva115/CareLess | https://devpost.com/software/careless |
| Wallet Warden | VandyHacks XII | MLH Best Use of Solana | Geofenced AI phone call stops impulse purchases and assigns savings tasks | Python, React, Gemini, ElevenLabs, Twilio, Radar.io, Nessie, Solana | https://github.com/mbaizhakyp/vandyhacks | https://devpost.com/software/wallet-warden |
| LeaseLedger | Hack@Davidson 2026 | Best Blockchain App + [MLH] Solana | Rental platform with on-chain deposits/staking and rent payments, no middleman | Next.js, MongoDB, Llama, ElevenLabs, DigitalOcean, Solana | https://github.com/hlee18lee46/hackdavidson | https://devpost.com/software/trustedtenants-eth |
| CarbonIQ | Innovation Hacks 2.0 (2026) | MLH Best Use of Solana | "Live greener, earn more, prove it on-chain" | React, Python, OpenAI, MongoDB, Rust | https://github.com/amapara27/carbon-iq | https://devpost.com/software/carboniq-erp9tf |
| Jen Zombie | SteelHacks XIII | Press Start + [MLH] Solana | "Your room is the level": WebXR/ARCore game with ESP32 hardware | three.js, ARCore, NVIDIA Nemotron, Gemini, ESP32, Raspberry Pi | https://github.com/brubru6707/jen-zombie | https://devpost.com/software/jen-zombie |
| WhatTheHoot | OwlHacks 2026 | [MLH] Best Use of Solana | Real-time biometrics drive a personalised owl companion | Swift, Next.js, Presage, Snowflake, Solana | https://github.com/hlee18lee46/owlhacks | https://devpost.com/software/whatthehoot |

**Total logged: 31** (13 ETHGlobal, 5 Colosseum, 13 student-hackathon Solana).

## 3. Patterns
**What ETHGlobal judges reward (compared with collegiate hackathons):**
- **Deep technical depth on frontier primitives over polish.**
  - Zubernetes combined TEE (SGX), SP1 ZK proofs and on-chain attestation.
  - ENShell built a four-layer pipeline: encryption, contract queue, Chainlink CRE and LLM scoring.
  - Judges include protocol founders (Vitalik, Stani Kulechov, Jesse Pollak at Bangkok), so novelty of the mechanism counts most.
- **Stacking sponsor bounties is normal and expected.** DAOGenie won 4 sponsor prizes on top of finalist, and Corpus combined Hedera, Circle, x402 and World ID. ETHGlobal finalist status is separate from and above sponsor prizes. At MLH events a project wins only one MLH category (see the mlh-sponsor-prizes file).
- **Themes by year:**
  - Bangkok 2024 had 4 of 10 finalists in gaming, plus Telegram-native apps (MiniDAO, BubbleWars) and AI agents. A Base judge called out "Tokenization and AI Agents".
  - Agentic Ethereum 2025 was all agents.
  - Cannes 2026 was **agent safety** (ENShell, npmguard), **privacy** (VEIL) and **prediction-market settlement** (DIVE).
- **Real-world bridge wins.** Examples: DAOGenie (agents act in the physical world), ETHPark-QR (Thai parking tickets) and LootGO (walking).
- **Detailed "How it's Made" write-ups.** ENShell built a separate GitHub org and a docs site. Judges and sponsors read these sections, so a clear architecture write-up is part of what gets judged.

**Solana patterns:**
- **Agents + payments is the 2025–26 meta.** Latinum (MCP payments, Breakout AI 1st) and MCPay (MCP + x402, Cypherpunk stablecoin 1st) won at the pro level. Students mirrored this: burn402 (agent pays for compute via x402), Nomad (agent passports), Solace (AI-guarded wallet), Settlers of Solana (agent economy).
- **Hardware wallets win.** Unruggable won a Colosseum grand champion. cryptX (Bitcamp, logged elsewhere) shows the same idea at student level.
- **The student "Best Use of Solana" bar is moderate:**
  - The chain moves value inside a real-world flow, such as relief funds released by tsunami risk (ReliefPool), rent deposits (LeaseLedger) or carbon rewards (CarbonIQ).
  - Winners pair Solana with other MLH tech: Gemini, ElevenLabs, Snowflake, Auth0.
  - Some winners use Solana lightly (CampusPup, Jen Zombie). A working on-chain demo seems to matter more than depth.
  - Anchor/Rust programs show up in the stronger ones (Nomad, ReliefPool).
- **The same builder wins repeatedly.** hlee18lee46 won Solana at Hackabull, OwlHacks and Hack@Davidson by reusing a pattern: consumer app + MLH stack + a Solana payment or mint.

**Takeaways for our Knight Hacks project:**
1. If we go for MLH Best Use of Solana, make Solana move value inside the core loop. Examples: escrow released by an AI or sensor trigger, or agent-to-agent payments with x402/Solana Pay. Avoid a bolted-on token. Have the devnet transaction visible in the demo (open the explorer link live).
2. "AI agent that holds a wallet, with guardrails" fits both the Solana prize and the AI-heavy tracks. Examples: an agent guard like ENShell or Solace, or agent identity like Nomad. It is also on-trend with what ETHGlobal and Colosseum judges rewarded in 2025–26.
3. Borrow ETHGlobal discipline: write a crisp "How it's made" with an architecture diagram and per-sponsor integration notes. Judges skim these.
4. We can win only one MLH category, so pick Solana only if the idea is blockchain-native. Otherwise spend sponsor effort on the less crowded MLH categories.
5. Real-world, local framing wins at all levels. Examples: ReliefPool's disaster relief, and the hurricane, Florida and UCF context.

## 4. Open questions / next searches
- **ethglobal.com blocked partway through.** WebFetch later returned "Unable to verify if domain ethglobal.com is safe". The SSR search `showcase?q=` stopped returning results after a few queries (likely rate-limited). Showcase slugs for these finalists were not confirmed:
  - Agentic Ethereum finalists: AIMen, Nimble, SecretAgent, Smol Universe, Synapze, PvPvAI, Shaman, Streme.fun, YieldSeeker. The list comes only from the X post https://x.com/ETHGlobal/status/1890448806975795550 and was not fetched.
  - Bangkok: BubbleWars, Dark Factory, Cat in a Box, ETHPark-QR.
- **ETHGlobal Cannes 2025 finalists not verified.** The list (BeamPay, OnlyDanks, PolyBet, livestakes, Pace Club, POAPrivacy, PrivyCycle, ChromaMind, PrivacyLinks, Hashlocked) came only from a search snippet. https://www.rootdata.com/news/309069 returned an empty page.
- **Other ETHGlobal finalist lists not verified:**
  - SF 2024: PumpRoyale, VVLDrizzy, IP Infinity, OmiSwap, HelloACAI, DAOsaster, Chain Waves, BuildBlocks, Betsy. TechFlow confirmed the names but gave no descriptions.
  - ETHGlobal NY (13 finalists, incl. FRAMED! and AirTracker): the year is unclear. Lead: https://www.mexc.com/news/66143
- **Not researched:** Taipei 2025 (8 finalists; lead https://wise-token.notion.site/ETHGlobal-Taipei-2025-1f073aed339180f4a992c82e8ab5159a), Brussels, Singapore, Trifecta and New Delhi.
- **Colosseum university awards:** Pythia (Cypherpunk) and Lexicon (Radar). No descriptions were fetched. Lead: https://colosseum.com/cypherpunk
- **Devpost built-with and gallery pages return 403 to WebFetch.** Use the `devpost.com/software/search?query=...` JSON endpoint with curl instead.
- **ETHGlobal judging criteria page not fetched.** Lead: https://ethglobal.com/events/cannes2026/prizes
