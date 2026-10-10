# Winners: lablab.ai AI/LLM sprint hackathons (2024–2026)
_Researched 2026-10-09 · sources: lablab.ai `/ai-hackathons/<event>/live` results pages, lablab.ai project pages (with place medals), lablab.ai/ai-articles winner summaries_

## 1. Scope
**Visited:**
- Event index: https://lablab.ai/event
- Results pages (the `/live` suffix shows the final Champion, Runner-up and 3rd place):
  - https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-ii/live
  - https://lablab.ai/ai-hackathons/raise-your-hack/live
  - https://lablab.ai/ai-hackathons/band-of-agents-hackathon/live
  - https://lablab.ai/ai-hackathons/qualcomm-x-meta-executorch-hackathon/live
  - https://lablab.ai/ai-hackathons/milan-ai-week-hackathon/live
  - https://lablab.ai/ai-hackathons/24h-claude-hackathon/live
  - https://lablab.ai/ai-hackathons/alpaca-ai-trading-agents-hackathon/live
  - https://lablab.ai/ai-hackathons/ibm-bob-2-hackathon/live (judging still in progress)
  - https://lablab.ai/ai-hackathons/ai-infra-summit-hackathon/live (judging still in progress)
- Winner articles:
  - https://lablab.ai/ai-articles/ibm-watsonx-hack-summary
  - https://lablab.ai/ai-articles/llama-impact-hackathon-sf-summary
  - https://lablab.ai/ai-articles/ai-agents-hackathon-summary
  - https://lablab.ai/ai-articles/ai-genesis-hackathon-2025-summary
  - https://lablab.ai/ai-articles/raise-your-hack-summary-2025 (it has no winner names)
- About 25 individual project pages. Each one confirmed a place medal, stack and repo.

**Skipped:**
- 2023 events (Cohere/Qdrant, OpenAI Stack Hack, ChatGPT/Whisper), because they fall outside the 2024–2026 window.
- IBM Bob 2.0 and AI Infra Summit, which have only community-vote rankings so far and no official winners.
- Special-prize winners that are named only, with no other detail.

**Tip:** the plain event page (`/ai-hackathons/<slug>`) never lists winners. Append `/live` to see them.

## 2. Winners table
| Name | Hackathon | Prize/track | What it does | Stack | Repo | Source URL |
|---|---|---|---|---|---|---|
| Intelligence for Existing CCTV Systems | AMD Developer Hackathon ACT II (Jul 2026) | 1st | Lets operators query existing CCTV footage in natural language and get answers backed by video evidence | AMD Dev Cloud/ROCm, Claude, Claude Code, Gemma, HF Hub | github.com/CU-DrAgon/rocm-cctv-analysis | https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-ii/roc-dragon/intelligence-for-existing-cctv-systems |
| OyeHoye Zero Tokens | AMD ACT II | 2nd | Local-first router for 8 NL task types that spends zero Fireworks tokens at grade time | Gemma, llama.cpp, spaCy, Cython, Claude Code, AMD Dev Cloud | github.com/nkapila6/oyehoye | https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-ii/oyehoye/oyehoye-zero-tokens |
| CacheForge topology-aware KV | AMD ACT II | 3rd | Rust KV-cache control plane for vLLM fleets on MI300X ("TTFT -36%, throughput +26%") | Rust, vLLM, AMD MI300X, Claude Code | github.com/lucheeseng827/amd-hackathon | https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-ii/roc-m-roll/cacheforge-topology-aware-kv |
| Autonomous Agents from APIs – Zero Code Builder | RAISE your HACK (Paris, Jul 2025; Vultr track team) | 1st / Champion | Turns natural-language prompts into deployable agents wired to enterprise APIs | Groq, Llama 3.x, Coral Protocol, Fetch.ai, Google ADK, Vultr, Next.js, Streamlit | github.com/GitDemo-VortexIQ/agent-studio-coral-adk-enterprise-vultr-orchestration | https://lablab.ai/ai-hackathons/raise-your-hack/autonomous-agents-from-apis-vultr-track/autonomous-agents-from-apis-zero-code-builder |
| Fashion AI | RAISE your HACK 2025 (Prosus track team) | 2nd | Multimodal fashion e-commerce with conversational style discovery | Groq, LLaVA, Llama 3, Fetch.ai | github.com/Jroq-Prosus/Fashion.AI | https://lablab.ai/ai-hackathons/raise-your-hack/jroq-prosus-track/fashion-ai |
| Freight Room | Band of Agents Hackathon (Jun 2026) | 1st | Assembles domain agents (logistics, finance, carrier, "dissent") at runtime to resolve ship-delay and demurrage decisions using real AIS and Customs data | Band AI, CrewAI, LangGraph, PydanticAI, GPT-4o, Mistral, Claude Code, Vercel | github.com/rohan879/freight-room | https://lablab.ai/ai-hackathons/band-of-agents-hackathon/band-baaja-baaraat/freight-room-a-response-room-for-ship-delays |
| Recoverflow | Band of Agents | 2nd | 9-agent dunning system for cross-border SME payment recovery, with compliance guardrails and Slack human-in-the-loop | Band SDK, Claude Sonnet/Haiku 4.5, ElevenLabs ConvAI, Twilio, Circle USDC, Chroma | github.com/JudyaiLab/recoverflow | https://lablab.ai/ai-hackathons/band-of-agents-hackathon/judy-ai-lab/recoverflow-cross-border-ar-on-autopilot |
| ClaimArbiter | Band of Agents | 3rd | Agents handle insurance claims from filing to signed decision, with human oversight and a tamper-evident audit trail | CrewAI, LangChain, GPT-4o, Llama 3, Gemma, Featherless, Claude Code | github.com/sahil-sharma-50/ClaimArbiter | https://lablab.ai/ai-hackathons/band-of-agents-hackathon/solorun/claimarbiter |
| Lodestar – Offline AI Survival Copilot | Qualcomm x Meta ExecuTorch Hackathon (Jun 2026) | 1st | Fully offline first aid, GPS-less navigation and emergency comms on a Snapdragon phone | ExecuTorch, Llama 3.2, Snapdragon (Galaxy S25 Ultra), Claude Code, Cursor | github.com/arpan-s-dev/QCOM | https://lablab.ai/ai-hackathons/qualcomm-x-meta-executorch-hackathon/lodestar/lodestar-offline-ai-survival-copilot |
| SnapOn | ExecuTorch Hackathon | 2nd (per results page) | Offline Android assistant: voice and camera frame → Whisper → SmolVLM on the Hexagon NPU, with "remember this" memory | ExecuTorch, Whisper, SmolVLM-500M, CLIP, FAISS, SQLite | github.com/Lexi-cod/snap | https://lablab.ai/ai-hackathons/qualcomm-x-meta-executorch-hackathon/live |
| Toddle AI | ExecuTorch Hackathon | Top 3 (results page says 3rd; project page shows a 1st medal) | On-device pose estimation that gives explainable gait metrics for toddlers | Snapdragon, pose estimation | github.com/preyashyadav/toddle-ai | https://lablab.ai/ai-hackathons/qualcomm-x-meta-executorch-hackathon/toddle-ai/toddle-ai |
| Deals Machine | AI Agent Olympics / Milan AI Week (May 2026) | 1st | Autonomous sales agent that runs outreach through to closing follow-ups | Claude, Claude Code, Speechmatics, Vultr, OpenAI, Next.js, Supabase | github.com/kyletdow47/deals-machine | https://lablab.ai/ai-hackathons/milan-ai-week-hackathon/view-1-studio/deals-machine-the-autonomous-sales-agent |
| ContextGuard – Live Decision Helper | AI Agent Olympics | 2nd | Live meeting agent that flags conflicts between what is said and company knowledge, then takes corrective action | Gemini 3 Flash, Speechmatics, Vultr, Next.js, Valkey | github.com/akirykouski/live-context-collision | https://lablab.ai/ai-hackathons/milan-ai-week-hackathon/revived/contextguard-live-decision-helper |
| Cascade AI | AI Agent Olympics | 3rd | Four coordinating agents automate client onboarding (emails, plan, intake, follow-ups) | Gemini, Vultr, Claude Code | github.com/YusufsDesigns/Cascade-AI | https://lablab.ai/ai-hackathons/milan-ai-week-hackathon/cracked-dev/cascade-ai |
| Autobelay | Alpaca AI Trading Agents Hackathon (Sep 2026) | 1st | Options agent: the LLM proposes trades and deterministic code enforces risk limits | Alpaca, Claude, Featherless | github.com/bill-mccormick-dg/alpaca-hackathon | https://lablab.ai/ai-hackathons/alpaca-ai-trading-agents-hackathon/razorsedge/autobelay-long-premium-short-leash |
| Should-AI Buy? | Alpaca Trading Agents | 2nd | Multi-agent trader with adversarial risk review and quant filters | Alpaca, Gemini 3 Flash, Qwen3, Claude Code | github.com/nabielnovelkhubran/Should-AI-Buy | https://lablab.ai/ai-hackathons/alpaca-ai-trading-agents-hackathon/trioblessingmiracle/should-ai-buy |
| Killswitch Capital | Alpaca Trading Agents | 3rd | Claude finds options trades and Python risk gates block rule violations | Alpaca, Claude, Featherless | github.com/SamsonDoski/alpaca-trading-assistant | https://lablab.ai/ai-hackathons/alpaca-ai-trading-agents-hackathon/team-quantus/killswitch-capital |
| AI to understand synthetic biology | 24h Claude Hackathon (Mar 2024) | 1st | Claude 3 Opus grades student synthetic-biology research and designs new MS2 phage experiments | Claude 3 Opus | github.com/doibio/claude3-hackathon | https://lablab.ai/ai-hackathons/24h-claude-hackathon/bioai/ai-to-understand-synthetic-biology |
| Mod GuardAIn | 24h Claude Hackathon | 2nd | Content moderation based on intent and nuance, beyond keyword filters | Claude, Vercel | github.com/Jaswir/AI-Forum-Moderation | https://lablab.ai/ai-hackathons/24h-claude-hackathon/ai-powerhouse/mod-guardain |
| GlucoGuide | 24h Claude Hackathon | 3rd | Personal diabetes assistant for meals and exercise based on sugar levels | Claude, Streamlit | github.com/Amna-Hassan04/GlucoGuide | https://lablab.ai/ai-hackathons/24h-claude-hackathon/glucoguide/glucoguide |
| Overshare | Generative AI Hackathon with IBM watsonx (Sep 2024) | 1st ($5k + $1.5k credits) | Scans images before you post them, to catch privacy and identity leaks | IBM Granite | github.com/mstatt/media_meta_data_extraction | https://lablab.ai/ai-hackathons/ibm-watsonx-challenge/limitlessgood/overshare |
| CompanyMatch | IBM watsonx (2024) | 2nd ($3k) | Automates competitor analysis | IBM Watson, Exa | — | https://lablab.ai/ai-articles/ibm-watsonx-hack-summary |
| MyVision | IBM watsonx (2024) | 3rd ($2k) | Describes surroundings from photos, with spoken feedback for visually impaired users | — | — | https://lablab.ai/ai-articles/ibm-watsonx-hack-summary |
| VizMotion | IBM watsonx (2024) | Best Use of Granite | Turns text into animated diagrams with editing and video export | IBM Granite | — | https://lablab.ai/ai-articles/ibm-watsonx-hack-summary |
| Aquinas | AI Agents Hackathon (lablab x MindsDB, Sep 2024) | 1st ($5k) | Monitors Twitter mentions and drafts on-brand replies, with a human-approval dashboard | AutoGen, Redis | github.com/thomasturek/aquinas | https://lablab.ai/ai-hackathons/ai-agents-hack-with-lablab-and-mindsdb/zarathustra/aquinas-ai-powered-social-media-engagement-tool |
| DEV AI AGENT | AI Agents Hackathon 2024 | 2nd ($3k) + Best Use of Llama 3.1 ($3k) | "Automates up to 99% of app development" | Llama 3.1 | — | https://lablab.ai/ai-articles/ai-agents-hackathon-summary |
| TEMO | AI Agents Hackathon 2024 | 3rd ($2k) | Helps children with ASD build emotional and social skills | — | — | https://lablab.ai/ai-articles/ai-agents-hackathon-summary |
| Llama Navigator AI | Llama Impact Hackathon SF (Nov 2024) | On-site 1st ($5k) + Best Use of Solo Tech | Chrome extension that guides you to the information you need on any site | Llama 3.2, Solo Tech | — | https://lablab.ai/ai-articles/llama-impact-hackathon-sf-summary |
| Compllama | Llama Impact SF | On-site 2nd ($3k) + Best Use of Restack | Building codes by location, plus compliance tracking for construction | Llama 3.2, Restack | — | https://lablab.ai/ai-articles/llama-impact-hackathon-sf-summary |
| Farmipole | Llama Impact SF | On-site 3rd + Best Use of MindsDB KB (1st) | Multilingual discovery of government schemes for Indian farmers | Llama 3.2, MindsDB | — | https://lablab.ai/ai-articles/llama-impact-hackathon-sf-summary |
| Bridging Underprivileged to Government Support | Llama Impact SF | Online 1st ($3k) | Real-time alerts about public benefits a user is eligible for | Llama 3.2 | — | https://lablab.ai/ai-articles/llama-impact-hackathon-sf-summary |
| MYFORMSNAPPER | AI Genesis Hackathon (Dubai, Nov 2025) | Best Use of Gemini, 1st ($10k GCP) | — | Gemini | — | https://lablab.ai/ai-articles/ai-genesis-hackathon-2025-summary |
| Emergency Triage Automation | AI Genesis 2025 | Best Opus Workflow, 1st ($3k) | Automates emergency-care prioritization (from its title) | AppliedAI Opus | — | https://lablab.ai/ai-articles/ai-genesis-hackathon-2025-summary |

**33 winners logged.**

## 3. Patterns
- **Multi-agent "war rooms" for a narrow, boring business process win agent events.** Freight Room (ship demurrage), Recoverflow (cross-border dunning), ClaimArbiter (insurance claims), Cascade AI (client onboarding) and Deals Machine (sales) all pick one costly workflow and run it end to end. Their write-ups stress audit trails, a "dissent" agent and human-in-the-loop approval. None of them is a generic chatbot.
- **"LLM proposes, deterministic code disposes."** All three Alpaca winners (Autobelay, Killswitch Capital, Should-AI Buy?) use the LLM for ideas and then put hard-coded risk gates or adversarial checks on top. Judges reward visible safety rails over raw autonomy.
- **Hardware-sponsor events reward measurable systems work, not apps.** At AMD ACT II, CacheForge reported TTFT -36% and throughput +26%, and OyeHoye's pitch was "zero tokens at grade time". At ExecuTorch, all three winners ran fully offline on a Snapdragon phone (Lodestar, SnapOn, Toddle AI). Benchmarks or a live on-device demo are worth a lot here.
- **Use the sponsor's own tech, and stack several sponsor tools.** Overshare and VizMotion used IBM Granite. The Llama Impact winners each also collected a partner side prize (Compllama→Restack, Farmipole→MindsDB, Llama Navigator→Solo Tech). DEV AI AGENT won 2nd place plus Best Use of Llama. The RAISE champion combined Groq, Llama, Coral, Fetch.ai and Vultr. Stacking partner tools wins several prizes for one project.
- **Social good and accessibility do well in the 24–48h events.** Examples are GlucoGuide, MyVision, TEMO (autism), Farmipole and Bridging Underprivileged, plus "AI for government" Chrome extensions (Llama Navigator, Clear Bureau).
- **Claude Code shows up everywhere in 2026.** It is listed as a tool by most 2026 winners (all three AMD winners, Band, Milan, Alpaca, Lodestar). Coding agents are now table stakes for speed.
- **Every winner shipped a public GitHub repo, a live demo URL (often on Vercel) and a slide PDF.** lablab requires these, and the winning submissions fill all of them in.

**Takeaways for our Knight Hacks project**
1. Pick one specific, expensive real-world workflow (claims, compliance, billing, triage) and automate it end to end with 3–5 named agents, a human-approval step and a visible audit log.
2. Put deterministic guardrails around the LLM (risk gates, validators) and show them in the demo. Judges from AI companies read this as engineering maturity.
3. If a hardware or infra sponsor (AMD, Qualcomm, etc.) has a challenge, bring numbers: a latency or throughput delta, an offline mode, or cost per query.
4. Combine 2–3 sponsor tools in one project so it qualifies for the main prize and several "Best Use of X" prizes.
5. Ship the full package: a public repo with a README, a deployed demo URL, and a short deck that opens with the problem's dollar cost.

## 4. Open questions / next searches
- The RAISE your HACK 2025 `/live` page showed only Champion and Runner-up. The per-track winners (Qualcomm SignWriting translator, Prosus trip coordinator, Vultr AR field-tech assistant, Qubic auditor, Blackbox security companion) are described but not named in https://lablab.ai/ai-articles/raise-your-hack-summary-2025. Try the RAISE track pages.
- Toddle AI has conflicting place data: 3rd on https://lablab.ai/ai-hackathons/qualcomm-x-meta-executorch-hackathon/live but a 1st medal on its project page.
- IBM Bob 2.0 (https://lablab.ai/ai-hackathons/ibm-bob-2-hackathon/live) and AI Infra Summit (https://lablab.ai/ai-hackathons/ai-infra-summit-hackathon/live) were still being judged. Recheck them later.
- The AI Genesis article gave no project URLs, and its descriptions were too vague to log, so those rows use "—".
- Not yet covered: lablab events for Google Gemini, Mistral, Upstage (Solar), Cohere, Groq and OpenAI in 2024–2025, plus AMD ACT I. Try `https://lablab.ai/ai-hackathons/<slug>/live` for slugs found via `site:lablab.ai/ai-hackathons`. Also WeAreDevelopers x BAND (ended Oct 6, 2026) and the AssemblyAI Voice Agent hackathon (Sep 2026).
- Llama Impact project page URLs were not retrieved. Repos for CompanyMatch, MyVision, DEV AI AGENT and TEMO were not checked.
