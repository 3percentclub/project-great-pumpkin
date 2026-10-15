---
name: sincerity-audit
description: Use when asked to find, rank, or audit NYC pumpkin patches (community gardens) by how quiet and sincere they are.
---

# Sincerity audit: find Linus the most sincere pumpkin patch

Use the `scout_patches` and `audit_noise` tools.

1. **Pick the borough.** Map any neighborhood to its borough first
   (Astoria → QUEENS, Bushwick → BROOKLYN, East Village → MANHATTAN).
2. **Scout.** Call `scout_patches` once for that borough with `limit` 5.
3. **Filter by Neighborhood.**
   - If the user specified a neighborhood (e.g., Bensonhurst, Astoria), inspect the returned gardens from Step 2.
   - **CRITICAL:** Keep ONLY the gardens whose address, name, or NTA explicitly matches the requested neighborhood.
   - **IF ZERO MATCHES REMAIN:** STOP IMMEDIATELY. Do NOT call `audit_noise`. Do NOT generate a table. Reply strictly: *"No community gardens were found in [Neighborhood]."*
4. **Audit.** For the matching gardens only, call `audit_noise` once per *distinct* zipcode.
5. **Rank & Report.**
   - Sort the matching gardens by `sincerity_score` (highest first).
   - Display a Markdown table containing **ONLY** those matched gardens:

     | Rank | Garden | Address | Zip | Noise (7d) | Score | Label |

   - Conclude with one sentence naming the top-ranked garden for that neighborhood.
6. **If a tool call fails**, say which garden or zip failed and leave that row out.