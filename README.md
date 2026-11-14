# Handoff 🤝

**One project memory. Any teammate. Any model.**

Handoff is a shared AI workspace for group projects. Every teammate can use the AI they like (Claude, GPT or Gemini), and they all share one project memory. Nobody has to re-explain the project, and nobody redoes work someone else already finished.

Built for **DeltaHacks X Backboard.io**, on top of [Backboard.io](https://backboard.io)'s persistent memory API.

---

## The problem

On a group project, everyone uses a different AI. One person works with Claude for an hour, then the next teammate opens ChatGPT and spends 20 minutes re-explaining everything, or redoes work that was already done. The project's context is locked inside one person's chat.

Team plans from AI companies don't fix this either: they lock the whole team into a single model.

## What Handoff does

| | |
|---|---|
| **Pick any model** | Each teammate chooses Claude, GPT or Gemini from a dropdown. Every model reads the same project memory. |
| **Hand off with @** | Type `@Kevin turn this into 5 slides` in the chat. The task appears in Kevin's **Handoffs** panel, and his welcome message tells him about it the moment he opens the project. |
| **Session notes, automatically** | When you leave a project, Handoff writes a short note (Done / Decided / In progress / Next task) and saves it to the project memory, tagged with your name and the model you used. |
| **Where things stand** | The sidebar shows each teammate's latest status, with yours first. **History** shows what every session finished, filterable by person. |
| **Quick-start prompts** | "Catch me up since my last session", "What's waiting on me?", "Does my part match our decisions?" |
| **Shared files** | Drag a draft or data file into the project, and every teammate's AI can read it. |
| **Memory you control** | See exactly what Backboard remembers, and remove anything wrong or outdated. |

## A 60-second example

The demo project is **Campus Coffee Cart Pitch**: three students pitching a coffee cart called *Bean There*.

1. **Ibrahim (Claude)** shares his market research (busiest 8–10am, about $4 a cup) and types *"@Sarah can you work out the budget?"*
2. **Sarah (GPT-4o)** opens the project and is told Ibrahim handed her a task. She asks *"What's waiting on me?"*, and GPT-4o answers with the details from Ibrahim's Claude session. She posts the budget and types *"@Kevin can you turn all of this into the 5 slides?"*
3. **Kevin (Gemini)** asks to be caught up. Gemini summarises both teammates' work and suggests what goes on each slide.

Three people, three different AI models, one shared memory.

## How it uses Backboard

- **One assistant per project.** Each project is a Backboard assistant that owns the shared memory and the uploaded files.
- **Per-message model switching.** Every message names its own provider and model, so the same conversation can move from Claude to GPT to Gemini and the memory carries over.
- **Auto memory.** Chat messages use Backboard's `Auto` memory mode, which pulls facts out of the conversation and recalls them for later sessions and other models.
- **Session notes as memories.** Notes are saved with `add_memory` and metadata (author, model, time). The app also keeps its own copy, because Backboard's auto-memory can merge or rewrite stored memories over time.
- **Document indexing.** Uploaded files are indexed by Backboard so any model can answer questions about them.

## Run it yourself (Windows)

You need a free [Backboard.io](https://backboard.io) API key.

1. Download this repository (green **Code** button → **Download ZIP**) and unzip it.
2. Double-click **`start.bat`**. The first time, it asks for your Backboard API key, installs what it needs, and opens the app in your browser at `http://localhost:8501`.
3. Click **Start**, then **Try the demo** and pick Ibrahim, Sarah or Kevin. Use the switch-teammate buttons to see the project from each person's side.

On Mac or Linux:

```bash
pip install -r requirements.txt
export BACKBOARD_API_KEY=your_key_here
python -m streamlit run app.py
```

Your key stays on your computer in `backboard_key.txt`, which is never uploaded.

## Built with

Python · Streamlit · Backboard.io (memory, model routing, document indexing) · Claude · GPT-4o · Gemini

## What's next

- **More models.** Backboard gives access to 17,000+ models through one API, so the model picker can grow far beyond the three in this demo.
- **Real accounts and data.** Google sign-in, a real database, and email invites and notifications.
- **A paid team plan.** A free tier with limits on cheap models, a Pro/Team plan, and bring-your-own-key for power users.
- **Integrations.** Google Docs, Notion and GitHub, so session notes and handoffs live where the work already happens.
- **A hosted version**, so anyone can try it from a link.

---

*Memory powered by [Backboard.io](https://backboard.io).*
