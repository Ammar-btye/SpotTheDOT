# System 2: context building, fine-tune vs prompt, grounding, latency

_Researched 2026-10-10. Items marked **(unverified)** are estimates or come from secondary sources._

## 1. Scope

System 2 takes a validated Laya flag, pulls Neon logs, and returns an Orbit-style question / answer / reasoning plus a recommended action (Qwen3.5-9B or Qwen3-VL-8B, llama.cpp, gfx1151). Covers context building, fine-tune vs prompt, faithfulness and eval, industrial copilots, latency.

Serving and data details: `tech-amd-rocm-hf-serving-2026-10-09.md`, `spot-data-insights-2026-10-09.md`.

## 2. Findings (URLs)

### 2.1 Context building

- **Text-to-SQL is unreliable at 7–9B.**
  - On BIRD, Qwen2.5-Coder-7B reaches 39.1% execution accuracy, against 49.2% for Llama-3.3-70B. Self-correction is the one "near-free win" (https://arxiv.org/abs/2606.29733).
  - Our questions are a small known set, so free-form SQL buys nothing.
- **The Neon MCP server is a dev tool, not a runtime path.**
  - The hosted server is `https://mcp.neon.tech/mcp`. `?readonly=true` keeps SELECTs and schema inspection available and disables writes (https://neon.com/docs/ai/neon-mcp-server).
  - Neon itself says: "We recommend MCP for development and testing only, not production environments" and "Never connect MCP agents to production databases" (same URL).
  - A secondary source says `run_sql` can run any SQL, so true read-only access needs a restricted DB role (https://mcpservers.org/zh-CN/servers/neondatabase/mcp-server-neon) **(unverified against Neon docs)**.
- **Tool calling works in llama.cpp, but needs care.**
  - llama-server supports OpenAI-style function calling with `--jinja`. Some models need a template override (https://raw.githubusercontent.com/ggml-org/llama.cpp/master/tools/server/README.md).
  - Every tool round trip adds a full LLM turn (see 2.5).
- **RAG over embedded logs is the wrong tool.**
  - The data is small, structured and numeric (40 anomalies, 270 actions; spot-data-insights). SQL on asset, anomaly type and waypoint finds similar incidents exactly; embeddings only approximate.
  - Neon has pgvector if we ever need free-text similarity, for example over operator notes (https://neon.com/docs/extensions/pgvector) **(not opened this session)**.
- **Packet ordering matters.** Models use information at the start and end of the context best, and degrade as the context grows (Lost in the Middle, https://arxiv.org/abs/2307.03172). Keep the packet short, put the key facts first, and put the question last.
- **Don't let the LLM do arithmetic.** Cognite's Atlas AI agents hand time-series retrieval, calculations, Python and REST calls to tools (https://docs.cognite.com/cdf/atlas_ai/references/atlas_ai_agent_tools.md). Precompute deltas, rates and percentages in SQL.

### 2.2 Fine-tune or prompt?

- **Fine-tuning teaches format and style, not facts.**
  - LIMA: 1,000 curated examples were enough to align format, because "knowledge … is learned almost entirely during pre-training" (https://arxiv.org/pdf/2305.11206).
  - OpenAI sees improvements from 50–100 examples and advises starting with 50 (https://developers.openai.com/api/docs/guides/supervised-fine-tuning).
- **Fine-tuning on new facts raises hallucination.**
  - When fine-tuning examples contain knowledge the model lacks, the model's tendency to hallucinate rises linearly as it learns them (Gekhman et al., EMNLP 2024, https://arxiv.org/abs/2405.05904v3).
  - RAG consistently beats fine-tuning for knowledge injection (Ovadia et al., EMNLP 2024, https://aclanthology.org/2024.emnlp-main.15).
  - So facts come from the packet; train only "read packet → explain".
- **Distillation evidence.**
  - Distilling step-by-step uses teacher rationales as extra supervision: over 50% less data than plain fine-tuning, and a 770M T5 beat 540B PaLM (https://arxiv.org/abs/2305.02301).
  - SCOTT shows student rationales can drift from predictions (https://www.amazon.science/publications/scott-self-consistent-chain-of-thought-distillation). **Lesson:** filter teacher outputs for faithfulness before training.
- **Structured outputs already handle format.**
  - llama-server enforces JSON through `json_schema` or `response_format: {"type":"json_schema","schema":…}` by converting the schema to a GBNF grammar (server README above).
  - Strict formats can hurt reasoning and key order matters (https://arxiv.org/pdf/2408.02442); dottxt blames unequal prompts and recommends in-format examples (https://blog.dottxt.ai/say-what-you-mean.html). Rule: put `evidence` before `answer`.
- **LoRA on gfx1151 is feasible.**
  - Unsloth lists Strix Halo (gfx1151) as "Full" support (https://unsloth.ai/docs/basics/amd).
  - For Qwen3.5-9B, a bf16 LoRA needs about 22 GB. Unsloth says "It is not recommended to do QLoRA (4-bit) training on the Qwen3.5 models". It exports to GGUF directly and requires transformers v5 (https://unsloth.ai/docs/models/qwen3.5/fine-tune).
  - llama-server loads adapters with `--lora` and can set a per-request `lora` scale. That allows a live A/B on one server (README).
  - With about 30 GB usable (rocm note), training beside the serving model is tight.

### 2.3 Faithfulness and evaluation

- **Prompting patterns.** Allow "I don't know", quote sources, cite every claim, retract unsupported ones, restrict to provided context (https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-hallucinations).
- **RAGAS faithfulness** = supported claims / total claims, verified against context; Vectara's open HHEM-2.1 T5 can do the verification (https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/).
- **MiniCheck**, a 770M fact-checker, reaches GPT-4-level grounding accuracy at about 400x lower cost (https://arxiv.org/abs/2404.10774v1). It can run locally as the post-hoc checker.
- **LLM-as-judge.** GPT-4 judges agreed with humans over 80% of the time, matching human–human agreement. The known biases are position, verbosity and self-enhancement (https://arxiv.org/abs/2306.05685). Use a different model as judge, and spot-check against a human.

### 2.4 Industrial copilots: what operators see

- **Boston Dynamics Orbit.**
  - AIVI-Learning now runs on Gemini Robotics. "AIVI prompts will now feature transparent reasoning, allowing you to see exactly how the model interprets your prompt and the logical steps it took" (https://bostondynamics.com/blog/aivi-learning-now-powered-google-gemini-robotics/).
  - Spot 5.2 adds targeted alerts, for example pump engineers get pump alerts. It also adds an MCP layer so enterprise AI agents can dispatch Spot (https://roboticsandautomationnews.com/2026/10/01/boston-dynamics-updates-spot-to-connect-autonomous-robot-inspections-with-enterprise-ai-systems/105384/).
- **AVEVA.** "Source-linked citations that support traceability and auditability", "cross-critique methodologies", never trained on customer data (https://www.aveva.com/en/perspectives/blog/generative-ai-in-connect-with-industrial-ai-assistant/).
- **Siemens.**
  - The Industrial Copilot translates machine error codes into plain language and suggests fixes from operational history and documentation.
  - Siemens claims 25% less reactive maintenance time (vendor claim) (https://www.automate-uk.com/news-publications/use-of-ai-copilots-set-to-grow-further-with-new-offering-aimed-at-machine-maintenance/).
- **Cognite.** Atlas AI grounds its agents in an industrial knowledge graph and calls deterministic tools (https://www.cognite.com/en/product/atlas, tools doc above).
- **Honeywell.** Experion Operations Assistant predicted alarms 5–10 minutes ahead in pilots; the UI is not described (https://www.honeywell.com/us/en/press/2026/03/honeywell-unveils-commercial-launch-of-ai-powered-control-room-assistant-following-successful-pilot).
- **Common trust pattern:** citations, visible reasoning, targeted alerts, tools for numbers, local data.

### 2.5 Latency and caching

- **Expected speed on Strix Halo.** A 7B Q4 model prefills at about 1,000–1,100 tok/s and generates at about 37–47 tok/s (https://github.com/visorcraft/strix-halo-llm-perf).
  - For a 9B model: a 2k-token packet takes about 2–3 s, and a 300-token answer about 8–10 s. That is about 10–13 s cold **(unverified; extrapolated)**.
- **Qwen3.5 caches poorly.**
  - Qwen3.5-9B is a hybrid model: 3 Gated DeltaNet layers to every 1 attention layer (HF card).
  - llama.cpp cannot shift or reuse KV for hybrid/recurrent models. It logs "forcing full prompt re-processing… (likely due to SWA or hybrid/recurrent memory)" (https://github.com/ggml-org/llama.cpp/issues/18497).
  - Users report full re-processing on Qwen3.5 when RAG content varies between requests (https://github.com/ggml-org/llama.cpp/issues/24587, https://github.com/ggml-org/llama.cpp/issues/24714).
  - `cache_prompt` is on by default and reuses only a shared prefix (README).
  - Qwen3-VL-8B uses standard attention, so prefix caching should work normally **(unverified)**.
- **Neon latency.** The Free plan scales to zero after 5 minutes (https://neon.com/pricing). Keep the compute warm before the demo.

## 3. Recommendations (concrete)

**R1. Use templated SQL context packets.** No text-to-SQL, no runtime MCP, no embedding RAG.
- Write one parameterized query bundle per flag type (`action_failed`, `anomaly`, `reading_out_of_range`, `battery_risk`) as Postgres views or functions in Neon.
- `buildPacket(flag_id)` returns JSON in under 1,500 tokens.
- Every row carries a short stable ID.
- For the follow-up chat only, expose the same views as three or four fixed llama.cpp tools that take parameters, not SQL.

**R2. Packet contents, in this order:**
1. **Flag:** Laya label and score, the validator rules that fired and their thresholds, time, mission, robot.
2. **Event:** the action row (type, status, `battery_pct`, error), the reading (value, unit, quality, expected range), and the anomaly (severity, type).
3. **Derived facts `[F#]` (SQL):** priority = severity × criticality; battery-band success (≤25%: 33%, n=24); drain per action; true mission health; QUESTIONABLE readings marked untrustworthy.
4. **Asset `[S#]`:** criticality, the last 5 readings (min, max, slope), lifetime anomaly count, prior flags with operator ack or dismissal and notes.
5. **Waypoint `[W#]`:** environment (HIGH_NOISE, DUSTY, LOW_LIGHT), success rate by action type, localization failures.
6. **Similar incidents `[I#]`:** top 3 by same asset and anomaly type, then same waypoint and failure type, each with its outcome or ack.
7. **Allowed actions (an enum)** plus the validator's suggested action.

Put the question last.

**R3. Output schema, enforced by grammar.**
- Fields: `evidence:[{claim, ids:[enum]}]` → `answer` → `question` → `recommended_action:{enum}` → `confidence:{low|med|high}` → `insufficient_context:bool`.
- Build the `ids` enum per request from the packet's IDs, so citing a row that doesn't exist is impossible.
- The UI re-orders to Orbit's question / answer / reasoning and shows clickable ID chips that open the row.
- Turn thinking off (`enable_thinking:false`) and set `max_tokens` around 350.

**R4. Use a deterministic post-check.** It is under 50 lines of code.
- Every number and asset/waypoint name in the text must appear in the packet (±rounding); the action must be in the enum.
- If required sections are missing, set `insufficient_context=true` before calling the LLM and render "Insufficient data: needs X".
- On failure, retry once with errors appended, then fall back to a templated explanation. Optionally score claims with MiniCheck or HHEM.

**R5. Verdict: prompt first, fine-tune only as a gated stretch.**
- Ship prompting with 3 few-shot packet→JSON examples, grammar constraints and R4.
- If time remains after the pipeline works (budget about 4 h), distill a LoRA:
  - **Teacher:** a larger open model on the same box (Qwen3.8-27B or Qwen3-30B-A3B, rocm note), prompted with R2 and R3.
  - **Data:** about 100 real flags plus 300–500 perturbed packets; 10–15% "insufficient context" targets. Keep only outputs passing R4. Hold out by mission or asset.
  - **Training:** Unsloth bf16 LoRA (r=16, 2–3 epochs; standard defaults, **unverified for this task**) → GGUF adapter → `--lora`.
- Ship the adapter only if it beats the baseline on R6 (AMD story: "trained and served on gfx1151"). The target is the packet-grounded explanation, not Laya's labels.

**R6. A 2-hour eval.**
- On 40 held-out flags, measure schema validity, citation-ID validity, number consistency (R4), claim support (RAGAS-style, different judge model), action agreement with the validator, and p50/p95 latency.
- Judge rubric, 1–5: grounded, actionable, concise.
- A teammate hand-labels 15 flags to check judge agreement. Put the table in the pitch.

**R7. Latency plan.**
- Precompute explanations for every flag (fewer than 100) into a Neon `explanations` table, keyed by `(flag_id, packet_hash, model, prompt_ver)`. The dashboard reads it instantly.
- Live "explain" button: render the packet first (SQL, about 100 ms **(unverified)**), stream tokens, keep the system prompt and few-shots as a fixed prefix.
- Don't count on KV reuse with Qwen3.5. If live latency matters most, A/B against Qwen3-VL-8B or a 4B model.
- Warm Neon and llama-server about 5 minutes before judging.

## 4. Open questions

1. Measured prefill and generation speeds for Qwen3.5-9B Q4 on our box, and whether `--ctx-checkpoints` helps with a fixed prefix.
2. Teacher license: open Qwen is safe; check terms before using a closed API's outputs for training.
3. 22 GB for training while llama-server is resident, or use a separate AMD environment?
4. Does Neon MCP read-only `run_sql` block writes? Matters only beyond dev.
5. Show confidence? Orbit documents reasoning, not confidence scores.
