# Winners: Large online corporate competitions (Google/Gemini, Chrome AI, ElevenLabs, Solana, Microsoft, Bolt), 2024–2026
_Researched 2026-10-09 · sources: ai.google.dev, developer.chrome.com, elevenlabs.io blog, bolt.new blog, microsoft.github.io, cloud.google.com blog, solana.com, blog.colosseum.com, solanacompass.com, GitHub API_

## 1. Scope
**Visited (loaded OK):**
- https://ai.google.dev/competition (Gemini API Developer Competition 2024 winners)
- https://blog.google/technology/developers/gemini-api-developer-competition-winners/
- https://developer.chrome.com/blog/ai-challenge-winners (Chrome Built-in AI Challenge 2024)
- https://developer.chrome.com/blog/ai-challenge-winners-2025 (Chrome Built-in AI Challenge 2025)
- https://elevenlabs.io/blog/announcing-the-winners-of-the-elevenlabs-worldwide-hackathon (Devpost-hosted, 2025)
- https://bolt.new/blog/2025-bolt-hackathon-winners (World's Largest Hackathon, 2025)
- https://microsoft.github.io/AI_Agents_Hackathon/winners/ (Microsoft AI Agents Hackathon, Apr 2025)
- https://cloud.google.com/blog/topics/developers-practitioners/winners-and-highlights-from-gke-hackathon (GKE Turns 10, Devpost, Dec 2025)
- https://solana.com/news/solana-radar-winners, https://blog.colosseum.com/announcing-the-winners-of-the-solana-breakout-hackathon/, https://solanacompass.com/learn/breakpoint-25/winners-of-the-colosseum-cypherpunk-hackathon (Colosseum runs these on its own Arena platform, not Devpost, but they are Solana's flagship online competitions)
- https://lablab.ai/ai-hackathons/raise-your-hack/live (Vultr track, but see Open questions)
- https://api.github.com/search/repositories?q=gibberlink (repo check)

**Blocked (403):** every `*.devpost.com` subdomain and `devpost.com/software/*` page I tried (run.devpost.com, gemini3.devpost.com, /software/jayu, /software/gibber-link, /software/mochi-6i7vuk, /software/cart-to-kitchen-gke-ai-assistant). Because of that, the stacks below come from sponsor blogs only, and "—" means the stack is unknown.

**Skipped for time:** Perplexity, Elastic, Snowflake, MongoDB, TiDB, Meta Llama Impact, and AWS Bedrock/Nova developer hackathons. Amazon's Nova AI Challenge is a university red-team tournament, not a build hackathon, so it is out of scope.

## 2. Winners table
| Name | Hackathon | Prize/track | What it does | Stack | Repo | Source URL |
|---|---|---|---|---|---|---|
| Jayu | Gemini API Dev Competition 2024 | Best Overall App | Personal assistant that integrates Gemini with the user's device and works across the screen | Gemini API | — | https://ai.google.dev/competition |
| VITE VERE | Gemini API Dev Competition 2024 | Most Impactful + People's Choice | Personalized support for people with cognitive disabilities, for daily-life autonomy | Gemini API | — | https://ai.google.dev/competition |
| Prospera | Gemini API Dev Competition 2024 | Most Useful + Best Use of Flutter | Real-time sales-call coaching co-pilot | Gemini API, Flutter | — | https://ai.google.dev/competition |
| Outdraw AI | Gemini API Dev Competition 2024 | Most Creative | Human-vs-AI party game: draw things humans get but AI can't | Gemini API | — | https://ai.google.dev/competition |
| Gaze Link | Gemini API Dev Competition 2024 | Best Android App | Lets ALS patients communicate with their eyes | Gemini API, Android | — | https://ai.google.dev/competition |
| ViddyScribe | Gemini API Dev Competition 2024 | Best Web App | Adds audio descriptions to videos instantly for accessibility | Gemini API | — | https://ai.google.dev/competition |
| Nutshell | Chrome Built-in AI Challenge 2025 | Most Helpful (Extension) | Hands-free web browsing for motor-disabled users | Chrome built-in AI APIs | — | https://developer.chrome.com/blog/ai-challenge-winners-2025 |
| AAC Board AI | Chrome Built-in AI Challenge 2025 | Most Helpful (Web App) | AAC communication board that proofreads, rephrases and translates messages privately and offline | Chrome built-in AI (Proofreader/Rewriter/Translator) | — | https://developer.chrome.com/blog/ai-challenge-winners-2025 |
| Phonaify | Chrome Built-in AI Challenge 2025 | Best Multimodal (Extension) | Real-time phonetic feedback on English pronunciation while reading online | Prompt API (audio input) | — | https://developer.chrome.com/blog/ai-challenge-winners-2025 |
| Pet Shelter App | Chrome Built-in AI Challenge 2025 | Best Multimodal (Web App) | Helps under-resourced shelters get pets adopted | Prompt API (image input) | — | https://developer.chrome.com/blog/ai-challenge-winners-2025 |
| Mentelo | Chrome Built-in AI Challenge 2025 | Best Hybrid AI (Extension) | Talk-to-it extension for tech help plus 10 daily-use tools | Built-in AI + Firebase AI Logic/Gemini API | — | https://developer.chrome.com/blog/ai-challenge-winners-2025 |
| Trail | Chrome Built-in AI Challenge 2025 | Best Hybrid AI (Web App) | Offline trail companion for planning and navigation | Built-in AI + Firebase AI Logic/Gemini API | — | https://developer.chrome.com/blog/ai-challenge-winners-2025 |
| Mochi | Chrome Built-in AI Challenge 2024 | Best Real-World App (Extension) | Adapts web content for readers with dyslexia, ADHD or reading disabilities | Chrome built-in AI | — | https://developer.chrome.com/blog/ai-challenge-winners |
| WP on-device AI Assistant | Chrome Built-in AI Challenge 2024 | Best Real-World App (Web) | WordPress plugin with on-device AI block, rewriter and title generator | Chrome built-in AI, WordPress | — | https://developer.chrome.com/blog/ai-challenge-winners |
| The Crooked Tankard | Chrome Built-in AI Challenge 2024 | Most Innovative (Web) | Text adventure where the AI narrates the outcomes of your actions | Chrome built-in AI | — | https://developer.chrome.com/blog/ai-challenge-winners |
| BrowseGraph | Chrome Built-in AI Challenge 2024 | Best Hybrid AI (Extension) | In-browser GraphRAG over your browsing history | Chrome built-in AI, GraphRAG | — | https://developer.chrome.com/blog/ai-challenge-winners |
| GibberLink | ElevenLabs Worldwide Hackathon 2025 | Global Top Prize | Two AI phone agents realize they're both AI and switch to a data-over-sound protocol (ggwave) | ElevenLabs Conversational AI, ggwave | https://github.com/PennyroyalTea/gibberlink | https://elevenlabs.io/blog/announcing-the-winners-of-the-elevenlabs-worldwide-hackathon |
| Hugo Tour Guide | ElevenLabs Worldwide Hackathon 2025 | Online 1st | Conversational, location-aware travel companion | ElevenLabs | — | https://elevenlabs.io/blog/announcing-the-winners-of-the-elevenlabs-worldwide-hackathon |
| Pep | ElevenLabs Worldwide Hackathon 2025 | Online 2nd | Voice and vision agent that coaches physical-therapy exercises in real time | ElevenLabs, vision model | — | https://elevenlabs.io/blog/announcing-the-winners-of-the-elevenlabs-worldwide-hackathon |
| Agent SFX | ElevenLabs Worldwide Hackathon 2025 | Online 3rd | Generates voiceovers and SFX for game devs from vision models | ElevenLabs, fal.ai, Godot | — | https://elevenlabs.io/blog/announcing-the-winners-of-the-elevenlabs-worldwide-hackathon |
| Dealwise | ElevenLabs Worldwide Hackathon 2025 | San Francisco 1st | Researches and phones local businesses to get price quotes | ElevenLabs voice agent | — | https://elevenlabs.io/blog/announcing-the-winners-of-the-elevenlabs-worldwide-hackathon |
| Tailored Labs | Bolt World's Largest Hackathon 2025 | Grand Prize ($100K) | Edits raw footage into polished video from natural-language commands | Bolt.new | — | https://bolt.new/blog/2025-bolt-hackathon-winners |
| Weight Coach | Bolt World's Largest Hackathon 2025 | 2nd place | Grocery scanning plus AI meal planning and diet guidance | Bolt.new | — | https://bolt.new/blog/2025-bolt-hackathon-winners |
| RiskWise | Microsoft AI Agents Hackathon 2025 | Best Overall | Agents flag supply-chain risks (port delays, geopolitics) | Python, Next.js, Azure AI Agent Service, Semantic Kernel, SQL | — | https://microsoft.github.io/AI_Agents_Hackathon/winners/ |
| TARIFFED! | Microsoft AI Agents Hackathon 2025 | Best Use of Azure AI Agent Service | Q&A over trade-tariff schedules | Azure AI Agent Service, Azure OpenAI, .NET 9 Blazor, SQL Server, Docker | — | https://microsoft.github.io/AI_Agents_Hackathon/winners/ |
| WorkWizee | Microsoft AI Agents Hackathon 2025 | Best Copilot Agent | Automates P1/P2 incident management across Teams, Jira and Bitbucket | Copilot Studio, Python, Azure Functions, Jira APIs | — | https://microsoft.github.io/AI_Agents_Hackathon/winners/ |
| Cart-to-Kitchen GKE AI Assistant | GKE Turns 10 Hackathon (Devpost) 2025 | Grand Prize | Analyzes a grocery cart and recommends recipes | Gemini, GKE Autopilot, ADK, A2A | — | https://cloud.google.com/blog/topics/developers-practitioners/winners-and-highlights-from-gke-hackathon |
| Reflect | Solana Radar (Colosseum) 2024 | Grand Champion ($50K) | Decentralized currency exchange using hedge-backed stablecoins | Solana | — | https://solana.com/news/solana-radar-winners |
| TapeDrive | Solana Breakout (Colosseum) 2025 | Grand Champion ($50K) | Decentralized storage network that rewards users for storing data | Solana | — | https://blog.colosseum.com/announcing-the-winners-of-the-solana-breakout-hackathon/ |
| Latinum | Solana Breakout (Colosseum) 2025 | AI Track 1st ($25K) | Payment middleware so MCP builders get paid | Solana, MCP | — | https://blog.colosseum.com/announcing-the-winners-of-the-solana-breakout-hackathon/ |
| Unrugable | Colosseum Cypherpunk 2025 | Grand Champion | Solana-native hardware wallet with a companion app | Solana, hardware | — | https://solanacompass.com/learn/breakpoint-25/winners-of-the-colosseum-cypherpunk-hackathon |

## 3. Patterns
- **Accessibility is Google's strongest winning theme.** Seven of the 16 Google winners logged here are assistive tech: VITE VERE, Gaze Link, ViddyScribe, Mochi, Nutshell, AAC Board AI and Phonaify. VITE VERE took both Most Impactful and People's Choice. Google judges consistently reward a named, underserved user with a concrete daily task.
- **Prize categories map to sponsor features.** Chrome 2025 split prizes into "multimodal" and "hybrid" (on-device plus cloud), and each split had both an extension winner and a web-app winner. The Gemini competition had Flutter, Firebase, Android and ARCore prizes. Prospera won twice (Most Useful plus Best Flutter) by stacking sponsor tech. Using the sponsor's newest API, such as audio or image input to the Prompt API or Firebase AI Logic, opens up more prizes.
- **ElevenLabs rewards voice as the product, plus a viral moment.** GibberLink won globally on a 30-second demo with a twist: the agents realize they're both AI and switch to beeps. Other winning shapes were agents that phone people for you (Dealwise and Procuro) and voice plus vision coaching (Pep). Nobody won with a chatbot that simply had TTS added.
- **Games and playful AI win the "creative/innovative" slots.** Examples are Outdraw AI, The Crooked Tankard, and PenApple (Gemini Best Game). Adversarial, human-vs-AI mechanics demo well.
- **Microsoft and Google Cloud reward multi-agent orchestration on boring enterprise problems.** Examples are supply-chain risk (RiskWise), tariffs (TARIFFED!), incident management (WorkWizee) and GKE's ADK + A2A shopping agents (Cart-to-Kitchen). The architecture diagram is the pitch.
- **Solana grand champions are real financial or infrastructure primitives,** such as an FX/stablecoin exchange, decentralized storage and a hardware wallet. None of them is an app with a token added on. The AI-track winner (Latinum) sits where agents meet payments: MCP monetization.
- **Bolt's mass judging favored polished, consumer-ready SaaS** like Tailored Labs and Weight Coach, which look like products you could launch tomorrow.

**Takeaways for our Knight Hacks project**
1. Pick one specific user, ideally an accessibility or underserved one, and one daily task. This is the most reliable winning pattern for Google/Gemini.
2. Design so that one build qualifies for several sponsor prizes, for example Gemini as the brain, ElevenLabs as the voice and Solana for a real payment or settlement step. Prospera and VITE VERE show that one project can win twice.
3. For ElevenLabs, make voice the interface and script one memorable "wow" moment for the demo video, in the style of GibberLink. An agent that makes a real phone call is a proven winning format.
4. If we use Solana, make the on-chain step necessary to the product (payments for AI/agent services, as in Latinum). Don't add a token for its own sake.
5. Use the sponsor's newest capability (Gemini multimodal/live, agent frameworks) and say so explicitly in the Devpost write-up. Judges score categories against named features.

## 4. Open questions / next searches
- **Gemini 3 Hackathon (gemini3.devpost.com, early 2026, $100K):** a search summary named Globot (grand prize), Aegis: Autonomous Multi-Agent Crisis Command (2nd) and Netra (3rd), but I couldn't load a page confirming it (gemini3.devpost.com and /updates returned 403). Not logged. Next step: retry through a browser or the Devpost blog.
- **Cloud Run Hackathon (run.devpost.com, winners announced Dec 17):** 403. It has AI Studio, AI Agents and GPU categories. Next step: search the Google Cloud blog for "Cloud Run hackathon winners".
- **Vultr:** the lablab Raise Your Hack Vultr track (https://lablab.ai/ai-hackathons/raise-your-hack/live) shows a vote-count leaderboard topped by "Autonomous Agents from APIs - Zero Code Builder". It's unclear whether that is the judged result, so it's not logged. Vultr-built projects from Hack This Fall 2025 (RudraOne, Nir Deep Researcher, RingoAI) appeared only in a search snippet and are unverified. lablab also lists an upcoming Vultr "Agent Rush" hackathon (Nov 3–8, 2026).
- **devpost.com/software pages all return 403,** so I couldn't get "Built with" stacks or repos (Jayu, Mochi, Cart-to-Kitchen, etc.). The blog sources list more winners I didn't log: Chrome 2024 Opale and Orma, Gemini Everies (ARCore), Trippy (Firebase) and PenApple (game), plus GKE regional winners CardOS, NeroFashion, V-Commerce Studio and Cartmate.
- **Bolt ranks 4–10** (Klinva, Ecobolt, CallVance, ModelMash, Legion, Bored? Opposite!, HealthPlan AI) appear on the blog without descriptions.
- **Amazon Nova AI Hackathon 2026** (Devpost; winners due around Apr 8, 2026): no winners page found.
- **Not searched:** Perplexity Sonar, Elastic, MongoDB, TiDB, Snowflake and Meta Llama Impact hackathon winners.
