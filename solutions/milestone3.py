"""SOLUTION · Milestone 3: a second tool, and the model chains them.

Run it:  python solutions/milestone3.py "Rank 3 pumpkin patches in Queens from most to least sincere."

Builds on milestone2.py (search for "M3"):
  1. A second tool card, audit_noise, that takes a zipcode.
  2. execute_tool runs count_noise_complaints, then sincerity() does the math.
     The model picks the zip; plain code computes the score.
  3. max_turns goes up, because the model now makes one call per garden.

Works with any provider that speaks the OpenAI chat format (OpenAI, Anthropic,
Gemini, DeepSeek, OpenRouter, Ollama...). You pick one in .env.
"""

import json
import os
import sys

from pathlib import Path

from dotenv import load_dotenv
from openai import APIError, OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))  # so we can import patches
from patches import count_noise_complaints, get_gardens, sincerity  # noqa: E402

load_dotenv()  # reads .env so you don't have to export variables by hand

# Fail loudly and clearly if .env is missing or half filled in.
for var in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
    if not os.environ.get(var):
        sys.exit(f"Missing {var}. Copy .env.example to .env and fill in "
                 "LLM_BASE_URL, LLM_API_KEY and LLM_MODEL (see README > Setup).")

if os.environ["LLM_BASE_URL"] == "practice":  # no key or internet: see src/practice_model.py
    from practice_model import PracticeClient as OpenAI  # noqa: F811

# max_retries: if the provider says "too many requests", the SDK waits and retries.
client = OpenAI(base_url=os.environ["LLM_BASE_URL"], api_key=os.environ["LLM_API_KEY"],
                max_retries=5)
MODEL = os.environ["LLM_MODEL"]

# The tool card. This JSON is the ONLY part of your code the model ever reads.
BOROUGHS = ["BRONX", "BROOKLYN", "MANHATTAN", "QUEENS", "STATEN ISLAND"]

# M2: v2 of the card says exactly what borough accepts and how to get there.
FIND_PUMPKIN_PATCHES = {
    "type": "function",
    "function": {
        "name": "find_pumpkin_patches",
        "description": "Find NYC community gardens (pumpkin patches) in one borough.",
        "parameters": {
            "type": "object",
            "properties": {
                "borough": {
                    "type": "string",
                    "enum": BOROUGHS,
                    "description": "One of the 5 NYC boroughs. Map neighborhoods to their "
                                   "borough first (Astoria -> QUEENS, Bushwick -> BROOKLYN, "
                                   "East Village -> MANHATTAN).",
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": 10,
                          "description": "How many gardens to return (1-10)."},
            },
            "required": ["borough"],
        },
    },
}
# M3: the second tool. Results from find_pumpkin_patches include a zipcode to pass here.
AUDIT_NOISE = {
    "type": "function",
    "function": {
        "name": "audit_noise",
        "description": "Count 311 noise complaints in one NYC zip code over the last N days "
                       "and return a sincerity score (0-100, higher is quieter). "
                       "Call once per garden zipcode.",
        "parameters": {
            "type": "object",
            "properties": {
                "zipcode": {"type": "string", "pattern": "^[0-9]{5}$",
                            "description": "5-digit zip code, e.g. 11102."},
                "days": {"type": "integer", "minimum": 1, "maximum": 30,
                         "description": "How many days back to count. Default 7."},
            },
            "required": ["zipcode"],
        },
    },
}
TOOLS = [FIND_PUMPKIN_PATCHES, AUDIT_NOISE]


def execute_tool(name: str, args: dict) -> str:
    """Run the function the model asked for. Always return a string, never raise."""
    try:
        if name == "find_pumpkin_patches":
            gardens = get_gardens(args.get("borough", ""), args.get("limit", 5))
            if not gardens:
                # M2: an empty list teaches the model nothing. A hint lets it fix the call.
                return json.dumps({
                    "error": f"No gardens found for borough {args.get('borough')!r}.",
                    "hint": f"Use one of: {', '.join(BOROUGHS)}. "
                            "Map neighborhoods to their borough (Astoria -> QUEENS).",
                })
            return json.dumps(gardens)
        if name == "audit_noise":
            # M3: the model chose the zip. Code does the counting and the math.
            count = count_noise_complaints(args["zipcode"], args.get("days", 7))
            return json.dumps({"zipcode": args["zipcode"], **sincerity(count)})
        return json.dumps({"error": f"Unknown tool: {name}"})
    except Exception as e:
        # Errors go back to the model as a result, so it can explain or retry.
        return json.dumps({"error": f"{type(e).__name__}: {e}"})


def run_agent(prompt: str, max_turns: int = 12) -> str:  # M3: more turns for more calls
    messages = [{"role": "user", "content": prompt}]

    for turn in range(max_turns):
        # STEP 1 · SEND: the conversation so far + the tool menu.
        response = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS)
        msg = response.choices[0].message

        # STEP 2 · CHECK: no tool calls means the model is done talking.
        if not msg.tool_calls:
            return msg.content or ""

        # Keep the model's request in the history, or it forgets what it asked.
        messages.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [
                {"id": c.id, "type": "function",
                 "function": {"name": c.function.name, "arguments": c.function.arguments}}
                for c in msg.tool_calls
            ],
        })

        for call in msg.tool_calls:
            # STEP 3 · RUN: the model only *asked*. Your code does the work.
            print(f"\n[turn {turn + 1}] tool call -> {call.function.name}({call.function.arguments})")
            try:
                args = json.loads(call.function.arguments or "{}")
                result = execute_tool(call.function.name, args)
            except json.JSONDecodeError:
                result = json.dumps({"error": "Arguments were not valid JSON."})
            print(f"[turn {turn + 1}] tool result <- {result[:300]}")

            # STEP 4 · REPORT: send the result back, tagged with the same id.
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

    raise RuntimeError(f"No final answer after {max_turns} turns.")


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "Rank 3 pumpkin patches in Queens from most to least sincere."
    print(f"Linus asks: {question}")
    try:
        print("\nAnswer:\n" + run_agent(question))
    except APIError as e:
        # Provider problems (busy, bad key, Ollama not running) get one clear line.
        sys.exit(f"\nThe model provider said no: {e}\n"
                 "429 = too many requests: wait a minute, or switch LLM_MODEL / provider. "
                 "See README > Troubleshooting.")
