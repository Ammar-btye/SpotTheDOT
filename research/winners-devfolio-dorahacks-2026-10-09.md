# Winners: Devfolio and DoraHacks (ETHIndia, Hack This Fall, Unfold, BuidlAI, Warpspeed, Push to Prod, Hedera Origins, BNB Hack), 2024–2026

_Researched 2026-10-09 · sources: Devfolio public search API (`api.devfolio.co/api/search/projects`, which returns each project's `prizes` array, i.e. the same data the project pages render), devfolio.co project pages, hedera.com blog, en.cryptonomist.ch_

## 1. Scope

**Visited / queried**
- Devfolio project search API for these hackathon slugs. Projects that won prizes were pulled from each one's `prizes` field, and each row below links to its devfolio.co/projects page.
  - `ethindia2024` (275 projects): https://ethindia2024.devfolio.co/projects
  - `buidlai-hack` (BuidlAI Hack 2025, Seoul, 33 projects): https://buidlai-hack.devfolio.co/
  - `push-to-prod` ("Push to Prod Hackathon with Genspark & Claude", Apr 2026, 44 projects)
  - `warpspeed2025` (Warpspeed: Agentic AI Hackathon, Lightspeed India, Jun 2025, 62 projects)
  - `hackthisfall2024` (HTF 4.0, Feb 2024, 132 projects): https://hackthisfall2024.devfolio.co/
  - `hackthisfall` (HTF 2025 Milestone Edition, Oct–Nov 2025, 119 projects)
  - `unfold2024` (208 projects)
  - `ethindia-villa` (Nov 2025). Every project there got a "Project Submission Prize", so it is not a real win and I skipped it.
- Devfolio past-hackathons list API, used to find 2025–2026 slugs.
- https://devfolio.co/blog/ethindia-2024-playing-the-infinite-game-of-ethereum/ (recap only; it names no winners)
- DoraHacks: dorahacks.io pages and API sit behind an AWS WAF "Human Verification" wall (HTTP 405/403). I used organizer recaps instead.
  - https://hedera.com/blog/these-are-the-winners-of-the-hello-future-origins-hackathon.md (each winner links to its dorahacks.io/buidl page)
  - https://en.cryptonomist.ch/2026/07/08/bnb-hack-winners/ (BNB Hack: AI Trading Agent Edition, Jul 2026, run on DoraHacks)

**Skipped:** HackBangalore (I found no Devfolio slug), ETHIndia 2025 (no `ethindia2025` slug; ETHIndiaVilla appears to stand in for it), and Unfold 2024 sponsor-only bounties apart from one AI example. I also skipped ETHIndia sponsor-only "pool prize" splits.

## 2. Winners table

| Name | Hackathon | Prize/track | What it does | Stack | Repo | Source URL |
|---|---|---|---|---|---|---|
| Bridge-AI | ETHIndia 2024 | Top 10 Finalist; BuidlGuidl Winner; Okto Winner; CDP Pool Prize | AI agent that takes Web2 users onchain through natural language | Scaffold-ETH 2, Next.js, Python, CDP kit, LangGraph, LangChain | https://github.com/bhavyagor12/onchain-hojayega | https://devfolio.co/projects/bridgeai-1851 |
| Whispered Secrets | ETHIndia 2024 | Top 10 Finalist; Coinbase Developer Platform Winner; Huddle01 Winner | Onchain murder-mystery game where players and AI agents work together to solve a crime | CDP AgentKit, Base, Llama 3, LangChain, LangGraph, Huddle01 | https://github.com/Envoy-VC/whispered-secrets-ethindia2024 | https://devfolio.co/projects/whispered-secrets-a1c4 |
| Khoj | ETHIndia 2024 | Top 10 Finalist; True Network Winner; Polkadot 1st Runner Up; Base/Lit/CDP pools | AI-personalised real-world treasure hunts with onchain rewards | Solidity, React, Coinbase SDK, Lit Protocol, Anthropic AI, Walrus | https://github.com/marcdhi/Khoj | https://devfolio.co/projects/khoj-3336 |
| zkRail | ETHIndia 2024 | Top 10 Finalist; Polygon 2nd Place; Base/CDP pools | Trustless rails for real-world payments | Node.js, OpenAI, AgentKit, Cloudflare, Hono, Solidity, Foundry | https://github.com/d4mr/zkrail | https://devfolio.co/projects/zkrail-5702 |
| Bifrost Protocol | ETHIndia 2024 | Top 10 Finalist; Polygon 1st Place | Darkpool-based aggregation layer across Bitcoin and EVM | Solidity/Hardhat, React, FROST/Schnorr, SP1 zk | https://github.com/jayendramadaram/Bifrost-protocol | https://devfolio.co/projects/bifrost-protocol-9058 |
| Tapify | ETHIndia 2024 | Top 10 Finalist; BNB Chain First Prize; Base pool | NFC tap-to-onboard crypto wallet | Solidity, account abstraction, NFC | https://github.com/koshikraj/tapify | https://devfolio.co/projects/tapify-b2b2 |
| Insider-Ink | ETHIndia 2024 | Top 10 Finalist; True Network Winner | Anonymous voices, verified truths: anonymous posting with verified claims | Next.js, Gemini API, zkSync, shadcn | https://github.com/an2yea/Insider-Ink | https://devfolio.co/projects/insiderink-4ff6 |
| Cure Me Baby | BuidlAI Hack 2025 (Seoul) | First Prize; NEAR AI "Psych"; Nethermind 2nd; Gensyn Winner | Gamified AI psychiatrist for mental wellness, running in a TEE | NEAR, Phala TEE, Upstage API, Cursor | https://github.com/derek2403/CureMeBaby | https://devfolio.co/projects/cure-me-baby-20c7 |
| Imperator of Mars | BuidlAI Hack 2025 | Second Prize; NEAR AI Creative; Story 3rd | Uses first-order logic and Merkle DAGs to verify LLM output and cut hallucination | LLM, MCP, NEAR agent, Story SDK | https://github.com/ainize-team/imperatorofmars | https://devfolio.co/projects/imperator-of-mars-1f91 |
| NEAR Analyst | BuidlAI Hack 2025 | Third Prize; NEAR AI Chain Research | Natural-language-to-SQL agent over NEAR chain data | NEAR AI agents, Flipside, Snowflake SQL, React | — | https://devfolio.co/projects/near-analyst-63c3 |
| BAYSED | BuidlAI Hack 2025 | Third Place; Story 3rd | Memory hub for AI agents | ElizaOS, Story MCP, Walrus | https://github.com/baYsed-BuidlAI/eliza-beta | https://devfolio.co/projects/baysed-d4b0 |
| AgentForge | BuidlAI Hack 2025 | Nethermind First Place; Rootstock 1st Prize | Launch self-hosted AI agents that chat, use tools and get paid | Next.js, shadcn, Wagmi, Bun, Postgres/Drizzle, Vercel AI SDK | https://github.com/grmkris/seoul-2025-buildai-hackathon | https://devfolio.co/projects/agentforge-815e |
| ConnectCrew | Push to Prod w/ Genspark & Claude (Apr 2026) | 1st Place | — (tagline is a joke: "looking for a job") | Claude Code, Genspark, Supabase, Composio, Node, Tailwind | https://github.com/bboxfred/connect-crew | https://devfolio.co/projects/connectcrew-77ed |
| Vendor Wrangler | Push to Prod w/ Genspark & Claude | 2nd Place | "Talk to vendors without talking to vendors" | Python, Node.js, SQL | https://github.com/ishnad/BDN | https://devfolio.co/projects/vendor-wrangler-d548 |
| Unscatter | Push to Prod w/ Genspark & Claude | 3rd Place | "Company brain" that gathers scattered team knowledge with no discipline needed | Python, React, Claude, Claude Code, Groq | https://github.com/matthewfarant/unscatter-ai | https://devfolio.co/projects/unscatter-cec5 |
| DreamOps | Warpspeed Agentic AI 2025 | Grand Prize | AI agent that handles on-call incidents | Python, Next.js, Kubernetes, AWS CloudWatch, Slack API | https://github.com/SkySingh04/DreamOps | https://devfolio.co/projects/dreamops-9f20 |
| PragyanAI | Warpspeed Agentic AI 2025 | First Runner-up | Personal multilingual AI learning agent | Python, React, Next.js, GCP | https://github.com/Kamalllx/Warp-Hack | https://devfolio.co/projects/pragyanai-097f |
| PlushieOS | Warpspeed Agentic AI 2025 | Second Runner-up; Bhindi AI Top 5 | Sentient emotional AI companion ("PlushieOS") | Python, Flask, Next.js, OpenAI | https://github.com/sanjuhs/ai-plushie-agent-web | https://devfolio.co/projects/plushieos-e022 |
| crediblecode | Hack This Fall 2024 (4.0) | Hackathon Winning Team | Tells real GitHub contributions from fake ones | React, Node/Express, MongoDB, LLM, Postman | https://github.com/Nilesh-chaudhary/crediblecode | https://devfolio.co/projects/crediblecode-4235 |
| Purrfect-Pal | Hack This Fall 2024 (4.0) | 1st Runners-Up; Vonage Best API project | Pet care, sitting and adoption platform | React, Django, Postgres, Vonage, Android | https://github.com/PekaVengers/PurrfectPal | https://devfolio.co/projects/purrfectpal-d759 |
| learn.ai | Hack This Fall 2024 (4.0) | 2nd Runners-Up; Postman Best Use | Personal learning navigator that curates content to your needs | TS, Node, LangChain, HuggingFace, Tesseract OCR, PyTorch | https://github.com/sshiwangi/LearnAI | https://devfolio.co/projects/learnai-f373 |
| SwasthकAI | Hack This Fall 2024 (4.0) | Best All Girls Team | AI health assistant ("Decode, Decide, Thrive") | Python, Express, PostgreSQL, AI/ML | https://github.com/jankigabani/SwasthKAI | https://devfolio.co/projects/swasthai-ab9e |
| Three21 | Hack This Fall 2025 | Hacker House & Demo Day invite; Lingo.dev 2nd; Apify Most Creative Actor | AI-assisted 3D model visualizer platform | Three.js, React, Node, Apify | https://github.com/Amon20044/3D-AI-Three21 | https://devfolio.co/projects/three-ai-assisted-d-visualizer-platform-7825 |
| Latent.fun | Unfold 2024 | Nethermind Best Agentic Project; Bullieverse Runner Up #2; Aptos/Okto bounties | Talent show where AI and the audience score (and roast) acts, with betting | React, FastAPI, ElevenLabs, Aptos, Base, Okto | https://github.com/satwikkansal/latent.fun | https://devfolio.co/projects/latentfun-unfold-got-latent-b7a4 |
| Major Gainz | Hedera Hello Future Origins 2025 (DoraHacks) | AI & Agents 1st ($15k) | AI DeFi copilot that turns wallet data into clear insights | Hedera | — | https://hedera.com/blog/these-are-the-winners-of-the-hello-future-origins-hackathon.md (BUIDL: https://dorahacks.io/buidl/30832) |
| Hedron | Hedera Origins 2025 (DoraHacks) | AI & Agents 2nd ($10k) | AI agent that guides new users to optimise Hedera DeFi investments | Hedera | — | same Hedera blog (https://dorahacks.io/buidl/29176) |
| Mariposa Plus | Hedera Origins 2025 (DoraHacks) | AI & Agents 3rd ($5k) | AI Web3 wallet with email setup and natural-language commands | Hedera | — | same Hedera blog (https://dorahacks.io/buidl/30772) |
| Aegis Protocol | Hedera Origins 2025 (DoraHacks) | DeFi & Tokenization 1st ($15k) | Trust and asset-management layer on Hedera Consensus Service | Hedera HCS | — | same Hedera blog (https://dorahacks.io/buidl/30404) |
| Lynx Token | Hedera Origins 2025 (DoraHacks) | Legacy Builders 3rd ($5k) | AI agents that automate DAO voting via HCS | LangChain, OpenAI, hedera-agent-kit | — | same Hedera blog (https://dorahacks.io/buidl/30683) |
| Neural Alpha by ClipX | BNB Hack: AI Trading Agent Ed. (Jul 2026, DoraHacks) | Autonomous Trading Agents 1st ($10k) | Agent that reads market conditions and executes trades on its own | BNB Chain | — | https://en.cryptonomist.ch/2026/07/08/bnb-hack-winners/ |

**30 winners logged.**

## 3. Patterns

1. **Agents won 2025–2026, and the winners did real things.** Every top-3 at Warpspeed (DreamOps, PragyanAI, PlushieOS), BuidlAI (Cure Me Baby, Imperator of Mars, NEAR Analyst), Push to Prod (ConnectCrew, Vendor Wrangler, Unscatter) and Hedera AI & Agents (Major Gainz, Hedron, Mariposa Plus) was an agent. The winners went past chat: DreamOps responds to real incidents through CloudWatch, Kubernetes and Slack, and Vendor Wrangler handles vendor conversations for you. BNB Hack's judges said outright that agents had to "interpret market conditions… and execute actions autonomously."
2. **Agent "trust layers" scored with AI-savvy judges.** Imperator of Mars (logic-verified LLM output), Cure Me Baby (TEE), BAYSED (agent memory) and AgentForge (agent monetization) won by adding verifiability or infrastructure to agents, rather than building one more agent.
3. **Stacking prizes is how ETHIndia winners worked.** Khoj won 6 prizes, Bridge-AI 4 and zkRail 4. Each one integrated 3–6 sponsor SDKs (CDP/AgentKit, Lit, Walrus, Huddle01) in a way that fit the product. Every one of the 10 main finalists also won at least one sponsor prize.
4. **Consumer or game hooks plus AI.** Whispered Secrets (AI murder mystery), Khoj (AI treasure hunt), Latent.fun (AI roasts a talent show) and PlushieOS (AI plush toy) all pair a fun, demo-able experience with the AI underneath.
5. **Plain-English problems win student-run events.** HTF winners such as crediblecode (fake GitHub contributions), Purrfect-Pal (pets), learn.ai and SwasthकAI (health reports) solve problems judges grasp in one sentence. They use ordinary MERN/Django stacks with a little LLM, and they also collected API sponsor prizes (Vonage, Postman).
6. **Recurring tech:** Next.js + Tailwind/shadcn, Python/FastAPI backends, LangChain/LangGraph, OpenAI/Claude/Gemini/Groq, Supabase/Postgres, Vercel deploys. Claude Code was named outright in 2 of the 3 Push to Prod 2026 podium stacks.

**Takeaways for our Knight Hacks project**
- Build an agent that takes real actions (it sends, files, deploys, or pages someone) inside a workflow judges recognise. Show it doing so live, not just answering questions.
- Plan 2–4 sponsor/MLH prize integrations that each carry real weight in the product. Stacking prizes is the most reliable payoff we found.
- Add a trust or safety angle (verification, privacy, audit log). It sets an "AI app" apart from the many others.
- Wrap it in a fun, demo-able hook (a game, a roast, a physical object). Consumer delight carried Whispered Secrets, Khoj and Latent.fun.
- Ship a deployed URL plus a GitHub repo plus a short video. Nearly every winner above linked all three.

## 4. Open questions / next searches

- **DoraHacks direct pages are blocked** (WAF; `dorahacks.io/buidl/30832` gave 405, the API gave a challenge page, and hidorahacks.medium.com gave 403). A real browser is needed to read stacks and repos for the Hedera and BNB winners. More DoraHacks results to chase: Sonic DeFAI Hackathon (2025, $250k; no winners recap found), Injective x ElizaOS AI Agent Hackathon (2025; only the launch post was found: https://injective.com/blog/introducing-the-injective-x-elizaos-ai-agent-hackathon), and ETHDenver 2025 Hedera AI bounty (InfoFi named 1st in search snippet only, unverified: https://hedera.com/blog/announcing-the-winners-of-eth-denver-2025-hedera-bounties/).
- **Devfolio queries that failed or timed out:** `agentic-commerce` (Aug 2026, 3,160 hackers), `the-great-agent-hackathon` (Sep 2026) and `pushtoprod-india` (Aug 2026). The API returned non-JSON or no hits, probably rate limiting, so retry them. The same goes for `ethmumbai2026`, `hackthisfall-virtual` (Nov 2024), `mosaicbytpf` and `cdp-agentkit-hackathon` (Coinbase Agents in Action, May 2025).
- ETHIndia 2024's 1st/2nd/3rd overall is unclear. The API shows only "Top 10 Finalists" for main judging, and the blog points to a winners tweet I did not load.
- HackBangalore: I found no Devfolio slug. Search X for the results post.
