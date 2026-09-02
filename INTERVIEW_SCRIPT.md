# CogniCare — Interview Presentation Script

---

## Part 1: Setting the Background (Why This Project, What Problem It Solves)

> *"I built CogniCare — a multilingual AI companion for elderly care that connects through Telegram."*

> *"The problem I wanted to solve is deeply personal and very real: loneliness and cognitive decline among the elderly. Millions of seniors live alone or with limited family contact. Studies consistently show that regular, meaningful conversation can slow cognitive decline and reduce feelings of isolation. But family members are busy — they live in different cities, have demanding jobs, and often feel guilty about not calling often enough."*

> *"Existing solutions fall short. Smart speakers like Alexa offer generic interactions — they don't remember yesterday's conversation, they don't know who they're talking to, and they certainly can't speak in Marathi or Hindi with the warmth of a real companion. Care apps require the elderly to learn new interfaces, which creates friction. And simply setting phone reminders to 'call grandma' doesn't solve the depth-of-conversation problem."*

> *"What CogniCare does is different: it proactively reaches out to the elderly person every day through Telegram — a platform they may already use — asks them personalized, memory-aware questions in their native language, and then surfaces insights to family caregivers through a web dashboard. It's not replacing human connection; it's creating a bridge that keeps the conversation going between the moments when family can be present."*

---

## Part 2: Defining Technologies (Why This Stack)

> *"Let me walk through the tech choices and why each one matters."*

> *"On the backend, I used **Python with FastAPI**. The reason is straightforward: my core logic revolves around LLM calls, RAG pipelines, and async task processing — all of which have the best library support in Python. FastAPI gives me async endpoints, automatic OpenAPI docs, and excellent performance for webhook handling, which is critical because Telegram sends updates in real time."*

> *"For the LLM, I chose **Groq** with the Llama 3.1 8B model. I evaluated OpenAI, Anthropic, and local models. Groq was the right choice for three reasons: speed — their custom LPU hardware delivers sub-second inference, which matters because the elderly person is waiting on the other end of a Telegram chat; cost — the free tier is generous for a project of this scale; and quality — Llama 3.1 handles multilingual generation well enough for conversational questions in Marathi, Hindi, and Tamil."*

> *"The memory system uses **RAG — Retrieval-Augmented Generation** — with a **Chroma vector store**. Each interaction is embedded and stored. When generating the next question, the system retrieves the most relevant past conversations and weaves them into context. This is what makes the bot feel like it genuinely remembers the person, rather than asking the same generic questions repeatedly. I chose Chroma over Pinecone or Weaviate because it runs in-process, which keeps infrastructure simple for this project's scale."*

> *"Task scheduling is handled by **Celery with Redis**. This was essential because I have multiple asynchronous workloads: daily question dispatch at configurable times, weekly report generation, stale recommendation cleanup, and real-time Telegram message processing. Celery's queue-based architecture lets each workload scale independently and retry on failure without blocking others."*

> *"The database is **Supabase** — a hosted PostgreSQL with a REST API. I chose it over raw PostgreSQL or MongoDB because it gives me a managed database, built-in auth, and row-level security without writing backend auth logic. The relational model fits well here: elders have interactions, interactions have insights, insights feed recommendations — that's a natural relational structure."*

> *"On the frontend, I used **Next.js with React** for the caregiver dashboard. The key requirement was real-time updates — when a caregiver marks a recommendation as done or dismisses it, the dashboard needs to reflect that immediately. Next.js with server-side rendering also gives fast initial loads, and the component architecture made it straightforward to build the tabbed dashboard layout."*

> *"Communication with the elderly happens exclusively through **Telegram**. I chose Telegram over WhatsApp or SMS for several reasons: the Bot API is free and well-documented, it supports rich formatting and inline keyboards, voice messages are first-class, and critically — Telegram bots can be created instantly without any business verification process. For the elderly, it's just another chat app. For development, it's the most accessible platform to build on."*

---

## Part 3: Action and Problem Solving (Project Flow + Challenges)

### The Flow

> *"Let me walk through the end-to-end flow."*

> *"**Step 1: Onboarding.** A caregiver signs in through the web dashboard, clicks 'Add Elder via Telegram,' enters the elder's name, age, preferred language, and time zone. The system generates a unique deep-link — something like `t.me/Cog_Care_Bot?start=elder_UUID`. The caregiver shares this link with the elder. When the elder taps it, Telegram opens a conversation with the bot, and the system links their Telegram account to their elder profile."*

> *"**Step 2: Daily Questions.** Every day at the configured time, the Celery scheduler dispatches questions. The interviewer agent loads the elder's profile, retrieves the top 5 most relevant past interactions from the vector store, and sends both to Groq. The LLM generates a personalized, warm question that references something the elder previously shared — maybe asking how their garden is doing, or what they cooked yesterday. The question goes out through Telegram."*

> *"**Step 3: Elder Responds.** The elder types or sends a voice note back. If it's a voice message, the system transcribes it using Whisper. The response is embedded, stored in the vector database for future memory recall, and an insight agent analyzes sentiment, engagement level, and flags any concerns — if the elder mentions feeling lonely or unwell, an escalation alert goes to the caregiver immediately."*

> *"**Step 4: Caregiver Dashboard.** The web dashboard shows the interaction history with sentiment badges — green for positive, yellow for neutral, red for concerning. Caregivers see AI-generated recommendations based on the interactions, and they can mark them as done, dismiss them, or write a custom suggestion that gets sent to the elder on Telegram. Every Friday, a weekly report summarizes the elder's emotional trends, key memories, and engagement patterns."*

### Challenges and How I Overcame Them

> *"Now let me talk about the real challenges I faced — because there were many."*

> *"**Challenge 1: Multilingual question quality.** The first version of the interviewer prompt produced questions that were either too generic or got truncated mid-sentence in Devanagari script. Marathi characters use more tokens than English, so responses would hit the max token limit and cut off. I solved this by increasing the token budget, adding a mandatory question-mark check with automatic retry, and adding multilingual fallback questions so the system never fails silently. The prompt itself is the heart of the app — it instructs the LLM to weave memory references naturally, almost like a real conversation partner, not a quiz show."*

> *"**Challenge 2: The webhook infrastructure.** Getting Telegram to reliably deliver messages was harder than expected. I initially set up a local tunnel with Cloudflare, but the URL changes on every restart — so Telegram kept sending updates to a dead endpoint. Then I deployed to Render's free tier, but Render free web services sleep after inactivity and the health check killed the Celery worker because it doesn't open an HTTP port. The solution was running the API and worker together via Honcho in a single web service container — the API handles the port, the worker stays alive alongside it, and Telegram's webhook stays registered."*

> *"**Challenge 3: The family feedback loop.** This sounds simple — let caregivers react to AI recommendations — but it required careful database design. The recommendations table, family interactions table, and elder profiles all needed correct foreign key constraints. I discovered that `family_interactions` referenced `recommendations` without `ON DELETE CASCADE`, which meant deleting an elder would fail with a foreign key violation. The fix required deleting child records in the correct dependency order before removing the elder profile."*

> *"**Challenge 4: RAG memory quality.** The naive approach of just embedding the last N interactions wasn't enough — the bot would ask similar questions or miss important context. I implemented a hybrid retrieval strategy: semantic search via Chroma's vector store combined with recency weighting, so recent memories get a relevance boost. The result is that the bot can reference something the elder mentioned two weeks ago with natural context, rather than awkwardly re-asking."*

> *"**Challenge 5: Real-time frontend updates.** The caregiver dashboard polls the backend every 5 seconds for new interactions and recommendations. Initially, this created a flickering issue with modals — React was treating component instances as new types on every re-render, causing mount/unmount cycles. The fix was extracting the modal as a stable component reference and memoizing the auth header to break the infinite re-render chain."*

> *"Throughout development, I kept notes on every bug and its root cause. That discipline was essential — when it came time to debug the Render deployment, the Telegram webhook issue, or the foreign key constraint, I could trace back through my notes to the exact code change that introduced or resolved each problem."*

---

## Closing Summary

> *"To summarize: CogniCare is a production-deployed system that sends daily multilingual conversations to elderly users through Telegram, analyzes their responses using RAG-powered memory and sentiment analysis, and presents actionable insights to family caregivers through a web dashboard. The stack is Python/FastAPI + Celery/Redis + Supabase on the backend, Next.js on the frontend, and Telegram as the communication layer — all chosen to balance capability, cost, and the specific needs of elderly users who need simplicity, not complexity."*

---

## Tips for Delivery

- **Pace yourself** — this script is ~8-10 minutes spoken at a natural pace
- **Pause after challenges** — let the interviewer absorb the problem before you explain the solution
- **Have the dashboard open** — if possible, show the live app while walking through the flow
- **Be ready for follow-ups on**: why Supabase over Firebase, how you'd handle 1000+ users, the RAG retrieval strategy in more detail, and how voice transcription works end-to-end

---

## Quick Reference: Project Overview

| Aspect | Details |
|--------|---------|
| **Project Name** | CogniCare |
| **Problem** | Elderly loneliness and cognitive decline due to infrequent meaningful conversation |
| **Solution** | AI-powered daily conversational companion via Telegram with caregiver dashboard |
| **Backend** | Python, FastAPI, Celery, Redis |
| **Frontend** | Next.js, React |
| **Database** | Supabase (PostgreSQL) |
| **LLM** | Groq (Llama 3.1 8B) |
| **Memory** | RAG with Chroma vector store |
| **Communication** | Telegram Bot API |
| **Languages** | English, Hindi, Marathi, Tamil |
| **Deployment** | Render (backend), Vercel (frontend) |
