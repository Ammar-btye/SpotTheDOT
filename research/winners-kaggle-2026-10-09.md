# Winners: Kaggle hackathon-format and LLM competitions (2024–2026)

_Researched 2026-10-09 · sources: blog.google, developers.googleblog.com, blogs.nvidia.com, developer.nvidia.com, huggingface.co/blog, arcprize.org, arxiv.org, aimoprize.com, nebius.com, techcrunch.com, gadgetbond.com, ndurner.substack.com_

## 1. Scope

**Searched and confirmed:**
- Gemma 4 Good Challenge (Kaggle hackathon, 2026): https://blog.google/innovation-and-ai/technology/developers-tools/winning-entries-gemma-4-good-challenge/
- Gemma 3n Impact Challenge (Kaggle, 2025): https://blog.google/innovation-and-ai/technology/developers-tools/developers-changing-lives-with-gemma-3n/
- MedGemma Impact Challenge (Kaggle, 2026): https://gadgetbond.com/google-medgemma-impact-challenge-winners/
- Google Tunix Hackathon (Kaggle TPUs, 2026): https://developers.googleblog.com/how-the-community-trained-gemma-to-think-with-tunix-and-tpus/
- AIMO Progress Prize 1, 2 and 3: https://huggingface.co/blog/winning-aimo-progress-prize, https://blogs.nvidia.com/blog/reasoning-ai-math-olympiad, https://aimoprize.com/updates/2026-06-24-aimo-3-winners-announced
- ARC Prize 2024 and 2025: https://arcprize.org/2024-results, https://arxiv.org/html/2412.04604v2, https://arcprize.org/blog/arc-prize-2025-results-analysis, https://developer.nvidia.com/blog/nvidia-kaggle-grandmasters-win-artificial-general-intelligence-competition/
- LMSYS Chatbot Arena Human Preference: https://nebius.com/blog/posts/chatbot-arena-competition-review
- K Prize (Konwinski): https://techcrunch.com/2025/07/23/a-new-ai-coding-challenge-just-published-its-first-results-and-they-arent-pretty/
- OpenAI gpt-oss-20b Red-Teaming: https://ndurner.substack.com/p/kaggle-red-teaming-challenge-openai-gpt-oss-concluded

**Skipped or unconfirmed:** "Unlock Global Communication with Gemma" (no winners list found). Gen AI Intensive and Agents Intensive capstones: Kaggle discussion pages are JS-only. Gemini Long Context: no winners list found. OpenAI to Z: only 2nd place (Commencis "GlyphTrack") was confirmed, and the source gave few details, so it is left out of the table. Not every category or tech-prize winner is listed, to stay under the word budget. A grep of /research showed no prior Kaggle or Gemma winner entries.

## 2. Winners table

| Name | Hackathon | Prize/track | What it does | Stack | Repo | Source URL |
|---|---|---|---|---|---|---|
| GEM-4 | Gemma 4 Good Challenge (2026) | 1st place | Robotic assistant for elderly and disabled people: vision-language-action model turns camera views into movements | Gemma 4 31B (labels training data) + fine-tuned Gemma 4 E2B, custom VLA | [writeup](https://www.kaggle.com/competitions/gemma-4-good-hackathon/writeups/new-writeup-1778618527713) | https://blog.google/innovation-and-ai/technology/developers-tools/winning-entries-gemma-4-good-challenge/ |
| Trido | Gemma 4 Good Challenge | 2nd place | Voice-controlled whiteboard for teachers with physical disabilities; generates mind maps and quizzes live | Gemma 4 E2B running locally on a budget laptop, real-time speech | [writeup](https://www.kaggle.com/competitions/gemma-4-good-hackathon/writeups/trido) | same as above |
| PenguinAgent | Gemma 4 Good Challenge | 3rd place | Offline research agent for field ecologists studying penguin huddles | SAM 3 segmentation, SigLIP 2 tracking, local Gemma 4 26B, RAG grounding | [writeup](https://www.kaggle.com/competitions/gemma-4-good-hackathon/writeups/PenguinAgent) | same as above |
| Acuífero·Vigía | Gemma 4 Good Challenge | Global Resilience Prize | Flood early warning that fuses telemetry, audio and river-camera feeds | Gemma 4 E2B on Raspberry Pi 5 | [writeup](https://www.kaggle.com/competitions/gemma-4-good-hackathon/writeups/acuifero4vigia) | same as above |
| PreVillage | Gemma 4 Good Challenge | llama.cpp Prize | Voice-first WhatsApp guide to government services for rural Nepalis | Gemma 4 E4B via llama.cpp on Raspberry Pi 5 (7.5 tok/s), Romanized-Nepali ASR, self-healing RAG loop | [writeup](https://www.kaggle.com/competitions/gemma-4-good-hackathon/writeups/previllage-a-govspeak-platform) | same as above |
| PathOS | Gemma 4 Good Challenge | Ollama Prize | Offline histopathology cancer screening for rural clinics | Custom-trained Gemma 4 E2B, GRPO alignment, CPU-only, Ollama | [writeup](https://www.kaggle.com/competitions/gemma-4-good-hackathon/writeups/pathos-getalife) | same as above |
| MindBridge | Gemma 4 Good Challenge | Unsloth Prize | Mental-health screening in Hindi dialects for community health workers | Gemma 4 E2B audio layers, Unsloth fine-tune, iOS TestFlight build | [writeup](https://www.kaggle.com/competitions/gemma-4-good-hackathon/writeups/new-writeup-1779141852948) | same as above |
| Gilbeot (길벗) | Gemma 4 Good Challenge | LiteRT Prize | On-device walking navigation that describes routes by landmarks for elderly users | Gemma 4 E2B, Google AI Edge LiteRT-LM, Android, works offline | [writeup](https://www.kaggle.com/competitions/gemma-4-good-hackathon/writeups/gilbeot) | same as above |
| Gemma Vision | Gemma 3n Impact Challenge (2025) | 1st place + Google AI Edge prize | Assistant for blind users; chest-mounted phone camera, triggered by voice or a clicker | Gemma 3n, MediaPipe LLM Inference API, flutter_gemma, 8BitDo Micro controller | [writeup](https://www.kaggle.com/competitions/google-gemma-3n-hackathon/writeups/gemma-vision) | https://blog.google/innovation-and-ai/technology/developers-tools/developers-changing-lives-with-gemma-3n/ |
| Vite Vere Offline | Gemma 3n Impact Challenge | 2nd place | Turns photos into simple step-by-step instructions read aloud, for people with cognitive disabilities | Gemma 3n offline, device TTS | [writeup](https://www.kaggle.com/competitions/google-gemma-3n-hackathon/writeups/vite-vere-offline) | same as above |
| 3VA | Gemma 3n Impact Challenge | 3rd place | Translates pictograms into rich sentences for an AAC user with cerebral palsy | Fine-tuned Gemma 3n, Apple MLX | [writeup](https://www.kaggle.com/competitions/google-gemma-3n-hackathon/writeups/3va) | same as above |
| Dream Assistant | Gemma 3n Impact Challenge | Unsloth Prize | Voice assistant trained on one person's impaired speech | Gemma 3n + Unsloth fine-tune | [writeup](https://www.kaggle.com/competitions/google-gemma-3n-hackathon/writeups/amoritas-assistant-ai-assistant-for-speech-impaire) | same as above |
| LENTERA | Gemma 3n Impact Challenge | Ollama Prize | Offline AI micro-server that broadcasts local Wi-Fi for schools without internet | Gemma 3n via Ollama | [writeup](https://www.kaggle.com/competitions/google-gemma-3n-hackathon/writeups/lentera-offline-ai-microserver-for-remote-and-rura) | same as above |
| Graph-based Cost Learning + Gemma 3n for Sensing | Gemma 3n Impact Challenge | LeRobot Prize | Robot exploration pipeline that cuts sensing time | Hugging Face LeRobot, IGMC model, Gemma 3n | [writeup](https://www.kaggle.com/competitions/google-gemma-3n-hackathon/writeups/graphbased-cost-learning-and-gemma-3n-for-sensing) | same as above |
| My (Jetson) Gemma | Gemma 3n Impact Challenge | NVIDIA Jetson Prize | Context-aware voice interface for physical spaces | Gemma 3n on NVIDIA Jetson Orin, CPU-GPU hybrid inference | [writeup](https://www.kaggle.com/competitions/google-gemma-3n-hackathon/writeups/my-jetson-gemma) | same as above |
| EpiCast | MedGemma Impact Challenge (2026) | 1st place | Turns community health-worker notes into WHO IDSR outbreak signals in West Africa | Fine-tuned MedGemma, MedSigLIP, HeAR, multilingual, mobile-first | [writeup](https://www.kaggle.com/competitions/med-gemma-impact-challenge/writeups/new-writeup-1770830823676) | https://gadgetbond.com/google-medgemma-impact-challenge-winners/ |
| FieldScreen AI | MedGemma Impact Challenge | 3rd place | Edge TB screening that combines chest X-ray and cough audio | Fine-tuned MedGemma, HeAR, MedASR, TranslateGemma, on-device | [writeup](https://www.kaggle.com/competitions/med-gemma-impact-challenge/writeups/fieldscreen-ai) | same as above |
| G-RaR | Google Tunix Hackathon (2026) | 1st place | Teaches a small base model to reason, using rubric-graded RL | Gemma-2-2B, SFT + GRPO with a Gemma-3-12B LLM-as-judge rubric reward, Kaggle TPU v5e-8 for 9h | [writeup](https://www.kaggle.com/competitions/google-tunix-hackathon/writeups/new-writeup-1768107128907) | https://developers.googleblog.com/how-the-community-trained-gemma-to-think-with-tunix-and-tpus/ |
| Pinocchio-1B | Google Tunix Hackathon | 2nd place | 1B reasoning model trained in a 9h TPU pipeline | Gemma-3-1B, SFT → SimPO (custom formatting loss) → GRPO, Tunix | [writeup](https://www.kaggle.com/competitions/google-tunix-hackathon/writeups/new-writeup-1767940008062) | same as above |
| NuminaMath-7B-TIR (Team Numina) | AIMO Progress Prize 1 (2024) | 1st place (29/50) | Solves olympiad math by mixing chain-of-thought with Python code execution | DeepSeekMath-7B + 2-stage SFT (HF TRL, DeepSpeed), vLLM, self-consistency over 48 samples, 8-bit AutoGPTQ on T4s | [HF model](https://huggingface.co/AI-MO/NuminaMath-7B-TIR) / [Space](https://huggingface.co/spaces/AI-MO/math-olympiad-solver) | https://huggingface.co/blog/winning-aimo-progress-prize |
| NemoSkills (NVIDIA) | AIMO Progress Prize 2 (2025) | 1st place (34/50, $262,144) | Math reasoning model distilled from bigger reasoners | Qwen2.5-14B-Base distilled from DeepSeek-R1 and QwQ-32B data, TensorRT-LLM FP8, ReDrafter speculative decoding, early-exit voting, 4×L4 | NeMo-Skills (GitHub, per source) | https://blogs.nvidia.com/blog/reasoning-ai-math-olympiad |
| the ARChitects | ARC Prize 2024 | 1st place (53.5%, $25k) | Solves ARC grid puzzles with an LLM plus test-time training and scoring across augmented "perspectives" | LLM + test-time training (TTT) on a single P100, 12h, offline | [paper](https://github.com/da-fr/arc-prize-2024/blob/main/the_architects.pdf) | https://arcprize.org/2024-results |
| NVARC (Ivan Sorokin, Jean-François Puget) | ARC Prize 2025 | 1st place (24.03% ARC-AGI-2, $25k) | Ensemble of an ARChitects-style TTT model and TRM components, trained on synthetic puzzles | 4B Qwen-family model, Unsloth LoRA (per notebook name), NeMo RL, NeMo Skills SDG, ~$0.20/task | [Kaggle code](https://www.kaggle.com/code/gregkamradt/arc2-qwen3-unsloth-flash-lora-batch8-queue-trm2) | https://arcprize.org/blog/arc-prize-2025-results-analysis |
| 1st-place solution (author not named in source) | LMSYS Chatbot Arena Human Preference Predictions (2024) | 1st place | Predicts which of two chatbot responses a human prefers | Llama3-70B / Qwen2-72B teachers distilled with KL loss into Gemma2-9B LoRA (5 folds, LoRA weights averaged), 8×A100 | — | https://nebius.com/blog/posts/chatbot-arena-competition-review |
| Eduardo Rocha de Andrade | K Prize (Konwinski), Round 1 (2025) | 1st place (7.5%, $50k) | Fixes fresh, contamination-free GitHub issues with an offline, compute-limited agent | Small/open models offline (per organizer); exact stack not given | — | https://techcrunch.com/2025/07/23/a-new-ai-coding-challenge-just-published-its-first-results-and-they-arent-pretty/ |
| "Policy over Values: Alignment Hacking via CoT Forgery" (Charles Ye, Jasmine C.) | OpenAI gpt-oss-20b Red-Teaming (2025) | Prize winner (rank not stated) | Jailbreaks gpt-oss by adding fake policy deliberations to the prompt | gpt-oss-20b, mechanistic-interpretability validation | [writeup](https://www.kaggle.com/competitions/openai-gpt-oss-20b-red-teaming/writeups/lucky-coin-jailbreak) | https://ndurner.substack.com/p/kaggle-red-teaming-challenge-openai-gpt-oss-concluded |

**Logged: 26 winners.** Also confirmed, but left out of the table to save space: AIMO 3 winners Exalted Joseph (#1), varianceofx, SKobayak, TAMU-TACO and yemao ye. Organizers say most top entries were harnesses around gpt-oss-120b ([source](https://aimoprize.com/updates/2026-06-24-aimo-3-winners-announced)).

## 3. Patterns

**Judged Kaggle hackathons (Gemma 3n, Gemma 4 Good, MedGemma):**
- **Every top placer runs offline or on-device.** Gemma Vision (MediaPipe on a phone), Trido (budget laptop), PreVillage and Acuífero·Vigía (Raspberry Pi 5), My (Jetson) Gemma (Jetson Orin), Gilbeot (LiteRT on Android). Judges reward "it works with no internet, on cheap hardware" far more than benchmark numbers.
- **A specific, named beneficiary wins.** Examples: 3VA was built for "Eva", a designer with cerebral palsy. Others target blind users (Gemma Vision), dysarthria (Gem-Care), dementia caregivers, West African outbreak surveillance (EpiCast) and Nepali villagers (PreVillage). The MedGemma recap says winners stood out for fixing real workflow problems "rather than just technical sophistication."
- **Multimodal plus a physical input or output.** Camera, cough audio, speech, haptics, a clicker controller or a robot arm (GEM-4, LeRobot entry). The small "E2B/E4B" models were chosen because they take audio and vision.
- **Sponsor tech prizes are the easiest money.** Each hackathon paid separate prizes for Unsloth, Ollama, llama.cpp, LiteRT, LeRobot (Hugging Face), Jetson (NVIDIA) and Cactus. Winners used exactly one sponsor tool deeply, e.g. Dream Assistant and MindBridge each fine-tuned with Unsloth.
- **A cheap fine-tune adds credibility.** 3VA (MLX), PathOS (GRPO), Gem-Care (19.0% vs 32.7% WER) and EpiCast all report a before/after metric from a small LoRA or SFT run.

**Scored LLM competitions (AIMO, ARC, LMSYS, Tunix):**
- **Distillation beats size.** NemoSkills (R1/QwQ → 14B), LMSYS 1st (70B → Gemma2-9B) and NVARC (offline synthetic data → 4B model) all used it.
- **Test-time compute: sample many, verify, vote.** Numina used SC-TIR (48 samples + code execution + majority vote). NemoSkills ran parallel long-thinking with early exit. The ARChitects and NVARC scored candidates across augmentations.
- **Tool-integrated reasoning.** Letting the model write and run Python made math answers checkable (Numina, NemoSkills).
- **GRPO with cheap rewards.** Tunix winners trained on free Kaggle TPUs in 9 hours, using an LLM-as-judge rubric (G-RaR) or a TF-IDF reward (3rd place).
- **NVIDIA inference tooling shows up in winners.** TensorRT-LLM FP8 plus speculative decoding (NemoSkills) and NeMo RL/Skills (NVARC). Hugging Face TRL, vLLM and Spaces carried Numina.

### Takeaways for our Knight Hacks project
1. **Pick a small open multimodal model and run it locally.** Candidates: Gemma 3n/4 E2B, or Qwen via Ollama or llama.cpp. If we can borrow one from NVIDIA, run it on the Jetson. "Works offline on a Jetson or Pi" lines up with both the NVIDIA and the Hugging Face prizes.
2. **Name one real user and demo a physical interaction**, such as a camera, voice or a button. Make it multimodal rather than chat-only.
3. **Do one quick Unsloth or TRL LoRA fine-tune (~1–2h).** Report a before/after metric on the slide, and publish the model plus a Gradio Space on Hugging Face for the HF track.
4. **Add cheap test-time reliability**: sample N times, verify with code, tool or retrieval, then vote. A self-healing RAG loop (as in PreVillage) makes demos noticeably sturdier.
5. **Don't train big models in 36h.** Distill from an API or large model into a small one only if a dataset is already at hand. Otherwise spend the time on the harness and the UX, which is what AIMO 3's top entries did with gpt-oss-120b.

## 4. Open questions / next searches
- Agents Intensive capstone winners: https://www.kaggle.com/competitions/agents-intensive-capstone-project/discussion/663531 (JS-only page, returned no content)
- Gen AI Intensive 2025Q1 capstone winners: https://www.kaggle.com/competitions/gen-ai-intensive-course-capstone-2025q1/discussion/575927 (JS-only)
- "Unlock Global Communication with Gemma" winners: no announcement found. Lead: https://developers.googleblog.com/en/advancing-multilingual-ai-with-gemma-2-and-a-150k-challenge
- LMSYS 1st-place author: likely the repo https://github.com/tascj/kaggle-lmsys-chatbot-arena (it uses Gemma2 and is described as a "solution"), but the README does not state a placement. Unconfirmed.
- NVARC score differs between sources: NVIDIA's blog says 27.64%, arcprize.org says 24.03% (private set). The table uses arcprize.org.
- AIMO 3 1st-place write-up (Exalted Joseph) and the 47/50 claim: https://arxiv.org/pdf/2603.27844. Not verified.
- Gemma 4 Good winners not logged: DEMENTOR (4th), TrueVoice, Gem-Care, CodeBuddy, Project Rosie, KawanIsyarat (Cactus). MedGemma winners not logged: Sunny (2nd), Tracer (4th) and the special-tech winners. All are in the sources above.
- OpenAI to Z Challenge: only 2nd place (Commencis GlyphTrack) was found, at https://www.newsfilecorp.com/release/265853. 1st place is unknown.
- Gemini Long Context competition winners were not found. Lead: https://mlops.community/blog/lessons-learned-from-the-gemini-long-context-kaggle-competition
- No AMD ROCm or Databricks tooling appeared in any confirmed Kaggle winner.
