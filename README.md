# 🎃 Project Great Pumpkin

**3percentclub Builders Track · Week 3: Tool calling, MCP & Skills**

Linus is looking for the most sincere pumpkin patch in New York City. You'll
build the agent that finds it using **real NYC Open Data**: GreenThumb
community gardens and 311 noise complaints.

You will:

1. Read a hand-rolled **agent loop** (no framework) and watch real tool calls.
2. **Break** a vague tool spec, then **fix the spec** so the model fixes itself.
3. Add a second tool so the model **chains** calls into a sincerity score.
4. *(Stretch)* Wrap the same functions as an **MCP server** and use them in a real agent.
5. *(Bonus)* Give the agent a **Skill**: a Markdown playbook for the whole job.

It takes about 60 minutes. Each milestone ends with a ✅ **Checkpoint**. If you hit
an error, check [Troubleshooting](#troubleshooting) first.

```
src/patches.py      the "hands": plain Python that calls NYC Open Data (no AI)
src/loop.py         the agent loop: you'll run, read, and fix this
src/server.py       the same tools as an MCP server
solutions/          finished versions of Milestones 2 and 3 (spoilers!)
.agents/skills/     the bonus Skill
tests/              pytest checks for the data functions
```

---

## Setup (5 min)

You need **Python 3.10 or newer** (`python3 --version`) and an API key for a
model that supports **tool calling**. The city data needs no key.

**No install option:** on this repo's GitHub page, click **Code → Codespaces →
Create codespace**. Python and the dependencies are installed for you, and a
`.env` file is created. Skip to step 4.

**1. Get the code**

```bash
git clone <repo link from the chat>
cd project-great-pumpkin
```

**2. Make a virtual environment and turn it on**

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows (PowerShell):

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

Your prompt should now start with `(.venv)`. Every command below assumes it does.

**3. Install**

```bash
pip install -r requirements.txt
```

**4. Add your model settings**

```bash
cp .env.example .env        # Windows: copy .env.example .env
```

Open `.env` and fill in the three variables for **one** provider:

| Variable | What it is |
|---|---|
| `LLM_BASE_URL` | Your provider's OpenAI-compatible URL (listed in `.env.example`) |
| `LLM_API_KEY` | Your key |
| `LLM_MODEL` | A model name your key can use, and it **must support tool calling** |

The code uses the `openai` Python package for every provider. `LLM_BASE_URL` decides
who answers: OpenAI, Anthropic, Gemini, DeepSeek, OpenRouter, or Ollama.

**No key? Two free options:**

- **OpenRouter free models.** Make a free account at openrouter.ai, create a key,
  and use the OpenRouter block that is already filled in at the top of `.env.example`.
  Its `LLM_MODEL=openrouter/free` sends each request to whichever free model has
  room right now, so one busy model won't block you. The model can change between
  turns, which is fine for this lab.
- **Ollama (runs on your laptop).** Install it from ollama.com, pull a model from
  ollama.com/search?c=tools, and use the Ollama block in `.env.example`.
  Small models often skip tool calls, so pick the biggest one your laptop can run.

**Not sure of the model name?** With `.env` filled in, ask your provider:

```bash
# macOS/Linux (load .env first: set -a; source .env; set +a)
curl -s "$LLM_BASE_URL/models" -H "Authorization: Bearer $LLM_API_KEY"
```

### Smoke test (no AI needed)

```bash
python src/patches.py
```

You should see something like this (names and counts come from live data and will vary):

```
Gardens in QUEENS:
  - 12001 142nd Place Community Garden | 12001 142nd Place, South Ozone Parks | 11436
  - 97th Street Community Garden | 33-28 97th Street | 11368
  - Arverne Gardens | 308 Beach 58th Street | 11692
Gardens in 'Astoria' (should be empty): []
Noise complaints in 11102, last 7 days: 53
```

If you see `Using the offline snapshot`, the city API is busy. That's fine: the lab
uses a saved copy of the same data in `data/`.

If this works, your Python and internet are fine. Any later error is about the model settings in `.env`.

---

## Milestone 1 · The loop (15 min)

The model **never runs your code**. It reads a JSON *tool card*, asks for a call,
and **your loop** runs the function and sends back the result.

```bash
python src/loop.py "Find a pumpkin patch in Queens"
```

Read the raw JSON it prints. Every `tool call ->` line is the model *asking*.
Every `tool result <-` line is *your code* answering:

```
[turn 1] tool call -> find_pumpkin_patches({"borough": "QUEENS"})
[turn 1] tool result <- [{"gardenname": "12001 142nd Place Community Garden", ...
```

**Your task:** open `src/loop.py` and find `run_agent`. Find the 4 steps of the
loop, which are marked with `STEP` comments:

1. **SEND** the messages and the tool menu to the model.
2. **CHECK** for `tool_calls`. If there are none, the model is done.
3. **RUN** the function the model asked for (`execute_tool`).
4. **REPORT** the result back as a `{"role": "tool", "tool_call_id": ...}` message.
   Then go back to step 1.

Questions to answer for yourself:

- Why must `tool_call_id` match the call's `id`?
- What stops the loop from running forever? (Look for `max_turns`.)
- Why does `execute_tool` return errors instead of raising them?

✅ **Checkpoint 1:** the final answer names a garden **in Queens, with an address**.

---

## Milestone 2 · Break it, then fix it (15 min)

Now ask the way a real person would, using a neighborhood:

```bash
python src/loop.py "Find a pumpkin patch in Astoria"
```

Watch the raw JSON. The model sends something like `{"borough": "Astoria"}`.
Astoria is a neighborhood, not a borough, so the function returns `[]` with no
explanation. You'll get either "I couldn't find any" or a confused guess. Good grief.

A smart model sometimes guesses `QUEENS` on its own. If yours does, run it once or
twice more and watch for `"borough": "Astoria"` in the raw JSON. When it gets it
right, that's luck, not the spec. The fix is about making it right *every* time.

The model did exactly what the tool card allowed. **Fix the spec, not the prompt.**

**Your task, in `src/loop.py`:**

1. In `FIND_PUMPKIN_PATCHES`, give `borough` an **`enum`** of the 5 boroughs:
   `BRONX`, `BROOKLYN`, `MANHATTAN`, `QUEENS`, `STATEN ISLAND`.
2. Rewrite its **description** to say: *map neighborhoods to their borough
   (Astoria → QUEENS, Bushwick → BROOKLYN).*
3. In `execute_tool`, when the result is empty, return an **error with a hint**
   instead of `[]`, for example:
   ```python
   {"error": "No gardens found for borough 'Astoria'.",
    "hint": "Use one of: BRONX, BROOKLYN, MANHATTAN, QUEENS, STATEN ISLAND."}
   ```
   Now if the model gets it wrong, it reads the hint and tries again by itself.

Run the Astoria question again.

✅ **Checkpoint 2:** the tool call shows `"borough": "QUEENS"` and the answer
names **a garden in Queens**.

Spoiler: [`solutions/milestone2.py`](solutions/milestone2.py)
(run it with `python solutions/milestone2.py "Find a pumpkin patch in Astoria"`).

---

## Milestone 3 · Sincerity score (15 min)

Linus wants the *most sincere* patch, which means the quietest one. Add a second
tool so the model can check 311 noise complaints for each garden's zip code.

`src/patches.py` already has what you need:

- `count_noise_complaints(zipcode, days=7)` returns a live count from 311.
- `sincerity(count)` returns the score. The score is
  `max(0, 100 - noise_complaints // 2)`, labeled **Sincere** (60 or more),
  **Mostly sincere** (30 or more), otherwise **Chaotic patch**.

**Your task, in your Milestone 2 loop:**

1. Import `count_noise_complaints` and `sincerity` from `patches`.
2. Write a second tool card, `audit_noise`, with a `zipcode` string (5 digits) and
   an optional `days` integer. Add it to `TOOLS`.
3. In `execute_tool`, handle `"audit_noise"`: count, then return
   `json.dumps({"zipcode": ..., **sincerity(count)})`.
4. Raise `max_turns` to about 12, because the model now makes one call per garden.

Notice who does what: the **model** picks which zips to check, and **plain code**
does the counting and the math. Never let the model do arithmetic you can do in code.

```bash
python src/loop.py "Rank 3 pumpkin patches in Queens from most to least sincere."
```

✅ **Checkpoint 3:** you see `audit_noise` calls for at least **two different
zips**, and they come back with **two different scores**.

Spoiler: [`solutions/milestone3.py`](solutions/milestone3.py).

---

## Milestone 4 · MCP (stretch)

Your loop only exists inside `loop.py`. **MCP** (Model Context Protocol) lets you
wrap the same functions *once* so that **any** MCP client can use them. Open
`src/server.py`: it's the same two functions with type hints. FastMCP turns those
hints and docstrings into the tool cards for you.

Its tools are `scout_patches(borough, limit)` and `audit_noise(zipcode, days)`.

```bash
python src/server.py
```

It prints nothing and waits. That's correct: it's waiting for a client to talk
to it over stdin/stdout. Press `Ctrl+C` to stop it.

**Connect it to one client.** Two rules apply to every client:

- Use **absolute paths**, because the client may start your server from a different folder.
- Use **your venv's Python**, because the system Python doesn't have `mcp` installed.
  In **Codespaces** there is no `.venv`: use the path printed by `which python` instead.

Get both paths from the repo folder:

```bash
# macOS/Linux
echo "$(pwd)/.venv/bin/python"   "$(pwd)/src/server.py"
# Windows (PowerShell)
echo "$PWD\.venv\Scripts\python.exe"   "$PWD\src\server.py"
```

**Claude Code** (run from the repo folder):

```bash
claude mcp add great-pumpkin -- "$(pwd)/.venv/bin/python" "$(pwd)/src/server.py"
claude mcp list        # should show: great-pumpkin ... ✔ Connected
```

**Cursor:** create `.cursor/mcp.json` in the repo folder (format from Cursor's MCP docs):

```json
{
  "mcpServers": {
    "great-pumpkin": {
      "type": "stdio",
      "command": "/ABSOLUTE/PATH/project-great-pumpkin/.venv/bin/python",
      "args": ["/ABSOLUTE/PATH/project-great-pumpkin/src/server.py"]
    }
  }
}
```

**VS Code:** create `.vscode/mcp.json` in the repo folder. Note that the top-level key
is `servers`, not `mcpServers` (format from VS Code's MCP docs):

```json
{
  "servers": {
    "great-pumpkin": {
      "command": "/ABSOLUTE/PATH/project-great-pumpkin/.venv/bin/python",
      "args": ["/ABSOLUTE/PATH/project-great-pumpkin/src/server.py"]
    }
  }
}
```

On Windows, use `C:\\path\\to\\.venv\\Scripts\\python.exe` (double backslashes in JSON).

**goose** (CLI 1.52). Using your OpenRouter key from `.env` (no setup menu needed):

```bash
set -a; source .env; set +a                 # load your .env into this terminal
export OPENROUTER_API_KEY="$LLM_API_KEY"    # goose's name for the same key
goose run --provider openrouter --model "$LLM_MODEL" \
  --with-extension "great-pumpkin:$(pwd)/.venv/bin/python $(pwd)/src/server.py" \
  -t "Find community gardens in Bushwick"
```

Using a different provider? Run `goose configure` once (an interactive menu) to set it
up, then use the same command without `--provider` and `--model`.

or for a chat session:

```bash
goose session --with-extension "great-pumpkin:$(pwd)/.venv/bin/python $(pwd)/src/server.py"
```

Then ask in plain English: *"Find community gardens in Bushwick."*

✅ **Checkpoint 4:** the client shows a `scout_patches` call with `BROOKLYN`.
You wrote zero loop code for this, because the client ran the loop for you.

---

## Bonus · Skill

A **tool** is something the agent *can* do. A **Skill** is the playbook for *how*
to do a whole job. It's a Markdown file, and the agent loads it only when the task
matches its `description` line.

The finished Skill is at
[`.agents/skills/sincerity-audit/SKILL.md`](.agents/skills/sincerity-audit/SKILL.md).
It says: scout patches → audit noise for each zip → rank → report as a short table.

- **Claude Code** reads Skills from `.claude/skills/`, so copy it there:
  ```bash
  mkdir -p .claude/skills && cp -r .agents/skills/sincerity-audit .claude/skills/
  ```
  Restart Claude Code in this folder, connect the MCP server (Milestone 4), and ask:
  *"Audit the pumpkin patches in Astoria for Linus."*
- **Other clients:** check your client's docs for where it looks for Skills.

✅ **Checkpoint 5:** you get a ranked table of gardens with scores, without
explaining the format in your prompt.

Try changing a rule in `SKILL.md` (for example, "only show the top 3") and ask again.

---

## Troubleshooting

| You see | Why | Fix |
|---|---|---|
| `Missing LLM_BASE_URL` (or `LLM_API_KEY` / `LLM_MODEL`) | No `.env` file, it's in the wrong folder, or a value is blank | `cp .env.example .env` in the repo folder, then fill in the 3 variables |
| `401` / `AuthenticationError` | The key doesn't match the base URL (for example, an OpenAI key with the Anthropic URL) | Use the key and URL from the **same** provider block |
| `model not found` / `404` | `LLM_MODEL` isn't a name your provider knows | List your models with the `curl .../models` command in Setup |
| The model answers without calling any tool | The model doesn't support tool calling (common with small Ollama models) | Pick a bigger or tool-capable model |
| `ModuleNotFoundError: No module named 'openai'` (or `mcp`, `dotenv`) | The venv isn't active | Activate it (Setup step 2). Your prompt should show `(.venv)` |
| Windows: `Activate.ps1 cannot be loaded` | PowerShell blocks scripts by default | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, or use `cmd` and run `.venv\Scripts\activate.bat` |
| `RateLimitError: 429` ... `temporarily rate-limited upstream` | That free model is busy | Use `LLM_MODEL=openrouter/free`, or wait a minute and retry |
| `NYC Open Data unavailable (... 429 Too Many Requests ...). Using the offline snapshot.` | The whole class is hitting the city API at once | Nothing to fix: the lab switches to the snapshot in `data/` and keeps going. To skip the city API entirely, set `OFFLINE=1` in `.env` |
| `Rate limit exceeded: free-models-per-day` | OpenRouter allows a limited number of free requests per account per day | Use a different provider key, or Ollama |
| `RuntimeError: No final answer after N turns` | The model kept calling tools | Raise `max_turns`, or tighten the tool descriptions |
| MCP client says the server failed to start | Relative path or the wrong Python | Use absolute paths and the venv's Python (see Milestone 4) |

**Run the tests** (they use the live city API, no model key needed):

```bash
pip install -r requirements-dev.txt
pytest tests -q
```
