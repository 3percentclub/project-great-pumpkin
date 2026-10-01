"""A hand-rolled agent loop. No framework, about 40 lines of real logic.

Run it:  python src/loop.py "Find a pumpkin patch in Queens"

Works with any provider that speaks the OpenAI chat format (OpenAI, Anthropic,
Gemini, DeepSeek, OpenRouter, Ollama...). You pick one in .env.
"""

import json
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

from patches import get_gardens

load_dotenv()  # reads .env so you don't have to export variables by hand

# Fail loudly and clearly if .env is missing or half filled in.
for var in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
    if not os.environ.get(var):
        sys.exit(f"Missing {var}. Copy .env.example to .env and fill in "
                 "LLM_BASE_URL, LLM_API_KEY and LLM_MODEL (see README > Setup).")

client = OpenAI(base_url=os.environ["LLM_BASE_URL"], api_key=os.environ["LLM_API_KEY"])
MODEL = os.environ["LLM_MODEL"]

# The tool card. This JSON is the ONLY part of your code the model ever reads.
# v1 is vague on purpose. Milestone 2 asks you to fix it.
FIND_PUMPKIN_PATCHES = {
    "type": "function",
    "function": {
        "name": "find_pumpkin_patches",
        "description": "Find pumpkin patches (NYC community gardens).",
        "parameters": {
            "type": "object",
            "properties": {
                "borough": {"type": "string", "description": "Where to look."},
                "limit": {"type": "integer", "description": "How many results."},
            },
            "required": ["borough"],
        },
    },
}
TOOLS = [FIND_PUMPKIN_PATCHES]


def execute_tool(name: str, args: dict) -> str:
    """Run the function the model asked for. Always return a string, never raise."""
    try:
        if name == "find_pumpkin_patches":
            gardens = get_gardens(args["borough"], args.get("limit", 5))
            return json.dumps(gardens)
        return json.dumps({"error": f"Unknown tool: {name}"})
    except Exception as e:
        # Errors go back to the model as a result, so it can explain or retry.
        return json.dumps({"error": f"{type(e).__name__}: {e}"})


def run_agent(prompt: str, max_turns: int = 6) -> str:
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
    question = " ".join(sys.argv[1:]) or "Find a pumpkin patch in Queens"
    print(f"Linus asks: {question}")
    print("\nAnswer:\n" + run_agent(question))
