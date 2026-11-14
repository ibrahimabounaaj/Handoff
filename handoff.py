"""
Handoff backend: every project is one Backboard assistant.
The assistant holds the shared memory + shared files for the whole team.
Each teammate gets their own thread on that assistant, with whatever model they pick.
"""
import asyncio
import os
from datetime import datetime

from backboard import BackboardClient

def _load_key():
    key = os.environ.get("BACKBOARD_API_KEY", "").strip()
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backboard_key.txt")
    if not key and os.path.exists(path):
        with open(path) as f:
            key = f.read().strip()
    if not key:
        raise RuntimeError("No Backboard API key. Put it in backboard_key.txt or set BACKBOARD_API_KEY.")
    return key


API_KEY = _load_key()

# Model menu shown in the UI -> (llm_provider, model_name)
# Check exact names in the Backboard dashboard model list and swap if any 404.
MODELS = {
    "Claude Sonnet 4.6": ("anthropic", "claude-sonnet-4-6"),
    "GPT-4.1 mini": ("openai", "gpt-4.1-mini"),
    "Gemini 2.5 Flash": ("google", "gemini-2.5-flash"),
    "GPT-4o": ("openai", "gpt-4o"),
}

SYSTEM_PROMPT = """You are the shared AI teammate for a group project.
Several teammates talk to you, each using a different AI model, but you all share one memory.
Every user message starts with a tag like [Ibrahim via Claude Sonnet] so you know who is talking.

Your job:
- Help with whatever the project needs (reports, assignments, slides, code).
- Keep track of decisions, who owns which part, what is finished, and what is next.
- Teammates can continue someone else's work OR work independently on their own part.
  Follow their lead. Never push them to pick up someone else's task.
- Never make anyone re-explain the project. Use what you remember.
- Keep everyone's work consistent with shared decisions (terminology, style, structure),
  and flag it if someone's work conflicts with a decision a teammate made.
"""


def _client():
    # New client per call keeps Streamlit's reruns and asyncio happy.
    try:
        return BackboardClient(api_key=API_KEY, timeout=120)
    except TypeError:
        return BackboardClient(api_key=API_KEY)


def run(coro):
    return asyncio.run(coro)


# ---------- projects ----------

async def _get_or_create_project(name: str) -> str:
    client = _client()
    found = await client.list_assistants(name=f"handoff:{name}", limit=1)
    if found:
        return found[0].assistant_id
    a = await client.create_assistant(name=f"handoff:{name}", system_prompt=SYSTEM_PROMPT)
    return a.assistant_id


def get_or_create_project(name: str) -> str:
    return run(_get_or_create_project(name))


# ---------- sessions ----------

async def _catch_up(assistant_id: str, user: str, model: str):
    """Starts a new thread for this teammate and returns (thread_id, briefing)."""
    provider, model_name = MODELS[model]
    client = _client()
    r = await client.send_message(
        f"[{user} via {model}] I'm opening the project. The sidebar already shows everyone's "
        "status, decisions and history, so do NOT list all of that. Using the session notes, "
        "tell me only: (1) what changed since my last session (who did it and with which model), "
        "and (2) anything that affects my part or that I need to stay consistent with. "
        "Max 3 short sentences, no headings, no bullet lists. If I have no earlier session, "
        "say in one sentence what the project is about instead. Then ask what I want to work on: "
        "I might pick up an open task or work on my own part.",
        assistant_id=assistant_id,
        memory="Readonly",  # reading only, don't store the catch-up itself
        llm_provider=provider,
        model_name=model_name,
    )
    return r.thread_id, r.content


def catch_up(assistant_id, user, model):
    return run(_catch_up(assistant_id, user, model))


async def _chat(assistant_id: str, thread_id, user: str, model: str, text: str):
    """Returns (reply, thread_id). If thread_id is None, a new thread is started on the project."""
    provider, model_name = MODELS[model]
    client = _client()
    target = {"thread_id": thread_id} if thread_id else {"assistant_id": assistant_id}
    r = await client.send_message(
        f"[{user} via {model}] {text}",
        **target,
        memory="Auto",  # save decisions/progress + retrieve shared memory
        llm_provider=provider,
        model_name=model_name,
    )
    return r.content, r.thread_id


def chat(assistant_id, thread_id, user, model, text):
    return run(_chat(assistant_id, thread_id, user, model, text))


async def _end_session(assistant_id: str, thread_id: str, user: str, model: str) -> dict:
    """Writes a handoff note for the next teammate and stores it in project memory."""
    provider, model_name = MODELS[model]
    client = _client()
    r = await client.send_message(
        f"[{user} via {model}] I'm ending my session. Write a session note for the team "
        "in this exact format:\n"
        "DONE: ...\nDECIDED: ...\nIN PROGRESS: ...\nNEXT TASK: ...\n"
        "Be specific (section names, numbers, file names). Max 80 words. No intro text.",
        thread_id=thread_id,
        memory="off",
        llm_provider=provider,
        model_name=model_name,
    )
    stamp = datetime.now().strftime("%b %d %H:%M")
    note = f"SESSION NOTE from {user} (used {model}, {stamp}):\n{r.content}"
    return await _store_note(client, assistant_id, user, model, stamp, note)


async def _store_note(client, assistant_id, user, model, stamp, note) -> dict:
    """Saves the note in Backboard (so every model sees it) and returns a copy for the app.
    The app keeps that copy because Backboard's auto-memory can later merge or rewrite memories."""
    res = await client.add_memory(
        assistant_id,
        content=note,
        metadata={"type": "handoff", "author": user, "model": model, "time": stamp},
    )
    mem_id = res.get("memory_id") if isinstance(res, dict) else None
    return {"id": str(mem_id or ""), "author": user, "model": model, "time": stamp, "text": note}


def end_session(assistant_id, thread_id, user, model):
    return run(_end_session(assistant_id, thread_id, user, model))


async def _quick_note(assistant_id: str, user: str, model: str, messages: list) -> dict:
    """Fallback when someone leaves before any reply came back: save what they said, no model call."""
    stamp = datetime.now().strftime("%b %d %H:%M")
    said = " | ".join(m.strip() for m in messages if m.strip())[:400]
    note = f"SESSION NOTE from {user} (used {model}, {stamp}):\nIN PROGRESS: {said}"
    return await _store_note(_client(), assistant_id, user, model, stamp, note)


def quick_note(assistant_id, user, model, messages):
    return run(_quick_note(assistant_id, user, model, messages))


# ---------- memory + files ----------

async def _get_memory(assistant_id: str):
    """Returns (session_notes, facts).
    session_notes: list of {"id", "author", "model", "time", "text"}; facts: list of (id, text)."""
    client = _client()
    res = await client.get_memories(assistant_id)
    notes, facts = [], []
    for m in res.memories:
        meta = getattr(m, "metadata", None) or {}
        if meta.get("type") == "handoff" or m.content.startswith(("SESSION NOTE", "HANDOFF NOTE")):
            author = meta.get("author")
            if not author:  # fall back to parsing "SESSION NOTE from Sarah (used ..."
                author = m.content.split(" from ", 1)[-1].split(" (", 1)[0]
            notes.append({
                "id": str(m.id),
                "author": author,
                "model": meta.get("model", ""),
                "time": meta.get("time", ""),
                "text": m.content,
            })
        else:
            facts.append((str(m.id), m.content))
    return notes, facts


def get_memory(assistant_id):
    return run(_get_memory(assistant_id))


async def _upload_draft(assistant_id: str, path: str) -> str:
    client = _client()
    doc = await client.upload_document_to_assistant(assistant_id, path)
    for _ in range(30):  # wait up to ~60s for indexing
        s = await client.get_document_status(doc.document_id)
        if s.status in ("indexed", "error"):
            return s.status
        await asyncio.sleep(2)
    return "processing"


def upload_draft(assistant_id, path):
    return run(_upload_draft(assistant_id, path))


# ---------- memory management ----------

async def _list_memories(assistant_id: str):
    client = _client()
    res = await client.get_memories(assistant_id)
    return [(str(m.id), m.content) for m in res.memories]


def list_memories(assistant_id):
    return run(_list_memories(assistant_id))


async def _delete_memory(assistant_id: str, memory_id: str):
    await _client().delete_memory(assistant_id, memory_id)


def delete_memory(assistant_id, memory_id):
    return run(_delete_memory(assistant_id, memory_id))


async def _reset_memories(assistant_id: str):
    await _client().reset_memories(assistant_id)


def reset_memories(assistant_id):
    return run(_reset_memories(assistant_id))
