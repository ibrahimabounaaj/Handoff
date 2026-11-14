# Handoff

**One project memory. Any teammate. Any model.**

Handoff is a shared AI workspace for group projects. Every teammate can use a different AI model (Claude, GPT, Gemini), and they all share one project memory powered by [Backboard.io](https://backboard.io). When you open a project, your AI already knows who did what, what was decided, and what's left, so nobody has to re-explain anything.

## Features

- One shared memory per project, readable by any model
- Automatic "project status" briefing when you join
- Switch models per message; memory carries over
- Upload drafts and data files (indexed by Backboard for RAG)
- Session notes written automatically when you leave
- Timeline filter by teammate
- Invites, accounts and a demo mode for switching between teammates

## How it works

Each project is one Backboard assistant that holds the shared memory and documents. Each teammate gets their own thread on that assistant, and every message is sent with `memory="Auto"` plus the teammate's chosen `llm_provider` / `model_name`. Session notes are stored with `add_memory`, tagged with author, model and time.

## Run it

```bash
pip install -r requirements.txt
export BACKBOARD_API_KEY=your_key      # Windows: set BACKBOARD_API_KEY=your_key
streamlit run app.py
```

On Windows you can also double-click `start.bat`.

## Built with

Backboard.io · Python · Streamlit · Claude · GPT · Gemini
