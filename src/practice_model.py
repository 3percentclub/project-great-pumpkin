"""A tiny stand-in for a real model, so the lab works with no key and no internet.

Use it by setting LLM_BASE_URL=practice in .env. It is NOT AI: it's a few rules
that behave the way a real model tends to, so you can still see the lesson:

- It only knows what the tool card says. If `borough` is free text, it passes
  the place name you typed ("Astoria"). If `borough` has an enum, it maps the
  neighborhood to one of the allowed values, like a real model reading the spec.
- If a tool result has a "hint", it reads it and tries again.
- If an `audit_noise` tool exists, it calls it once per garden zip.

It mimics just enough of the openai client for loop.py:
client.chat.completions.create(...).choices[0].message
"""

import json
import re
from types import SimpleNamespace as NS

NEIGHBORHOODS = {
    "astoria": "QUEENS", "flushing": "QUEENS", "jamaica": "QUEENS", "queens": "QUEENS",
    "bushwick": "BROOKLYN", "williamsburg": "BROOKLYN", "brooklyn": "BROOKLYN",
    "east village": "MANHATTAN", "harlem": "MANHATTAN", "manhattan": "MANHATTAN",
    "mott haven": "BRONX", "bronx": "BRONX", "st. george": "STATEN ISLAND",
    "staten island": "STATEN ISLAND",
}


def _place(text: str) -> str:
    """Pull the place out of 'Find a pumpkin patch in Astoria'."""
    match = re.search(r"\bin ([A-Za-z .]+?)(?: from|[?.!]|$)", text)
    return match.group(1).strip() if match else "Queens"


def _to_borough(place: str) -> str:
    return NEIGHBORHOODS.get(place.lower(), place.upper())


def _call(n: int, name: str, args: dict):
    return NS(id=f"practice_{n}", type="function",
              function=NS(name=name, arguments=json.dumps(args)))


def _reply(content=None, tool_calls=None):
    return NS(choices=[NS(message=NS(content=content, tool_calls=tool_calls))])


def _create(model, messages, tools, **_):
    names = {t["function"]["name"]: t["function"] for t in tools}
    card = names["find_pumpkin_patches"]["parameters"]["properties"]["borough"]
    prompt = messages[0]["content"]
    results = [json.loads(m["content"]) for m in messages if m["role"] == "tool"]
    n = len(messages)

    # Turn 1: ask for gardens. Free text in, free text out. Enum means "map it first".
    if not results:
        place = _place(prompt)
        borough = _to_borough(place) if "enum" in card else place
        return _reply(tool_calls=[_call(n, "find_pumpkin_patches", {"borough": borough, "limit": 3})])

    last = results[-1]
    if isinstance(last, dict) and "hint" in last:  # the error told us how to fix the call
        return _reply(tool_calls=[_call(n, "find_pumpkin_patches",
                                        {"borough": _to_borough(_place(prompt)), "limit": 3})])

    gardens = next((r for r in results if isinstance(r, list) and r), [])
    if "audit_noise" in names and gardens and len(results) == 1:
        zips = sorted({g["zipcode"] for g in gardens})
        return _reply(tool_calls=[_call(n + i, "audit_noise", {"zipcode": z}) for i, z in enumerate(zips)])

    if not gardens:
        return _reply(content="I couldn't find any pumpkin patches there. (Good grief.)")
    scores = {r["zipcode"]: r for r in results if isinstance(r, dict) and "sincerity_score" in r}
    lines = []
    for g in gardens:
        s = scores.get(g["zipcode"])
        extra = f" · sincerity {s['sincerity_score']} ({s['label']})" if s else ""
        lines.append(f"- {g['gardenname']}, {g['address']} ({g['zipcode']}){extra}")
    if scores:
        lines.sort(key=lambda line: -int(re.search(r"sincerity (\d+)", line).group(1)))
    return _reply(content="[practice model] Pumpkin patches I found:\n" + "\n".join(lines))


class PracticeClient:
    def __init__(self, **_):
        self.chat = NS(completions=NS(create=_create))
