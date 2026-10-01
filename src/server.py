"""The same functions, wrapped as an MCP server.

Any MCP client (Claude Code, Cursor, VS Code, goose) can start this file and
call its tools. You never write a loop here: the client runs the loop.

Run it:  python src/server.py   (it waits silently on stdin; that's normal)

Never print() in this file. Over stdio, stdout IS the protocol, and one stray
print corrupts the message stream.
"""

from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from patches import count_noise_complaints, get_gardens, sincerity

mcp = FastMCP("great-pumpkin")

# Literal becomes an "enum" in the tool's JSON Schema, so clients can see the 5
# allowed values. FastMCP builds the whole schema from type hints + docstring.
Borough = Literal["BRONX", "BROOKLYN", "MANHATTAN", "QUEENS", "STATEN ISLAND"]


@mcp.tool()
def scout_patches(
    borough: Borough,
    limit: Annotated[int, Field(ge=1, le=10)] = 5,
) -> list[dict]:
    """Find NYC community gardens (pumpkin patches) in one borough.

    Map neighborhoods to their borough first (Astoria -> QUEENS,
    Bushwick -> BROOKLYN, East Village -> MANHATTAN).
    Each result has a zipcode you can pass to audit_noise.
    """
    return get_gardens(borough, limit)


@mcp.tool()
def audit_noise(
    zipcode: Annotated[str, Field(pattern=r"^\d{5}$", description="5-digit NYC zip code")],
    days: Annotated[int, Field(ge=1, le=30)] = 7,
) -> dict:
    """Count 311 noise complaints in one zip over the last N days and score it.

    Returns noise_complaints, sincerity_score (0-100, higher is quieter) and a label.
    """
    return {"zipcode": zipcode, "days": days, **sincerity(count_noise_complaints(zipcode, days))}


if __name__ == "__main__":
    mcp.run()  # stdio transport by default
