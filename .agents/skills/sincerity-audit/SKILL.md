---
name: sincerity-audit
description: Use when asked to find, rank, or audit NYC pumpkin patches (community gardens) by how quiet and sincere they are.
---

# Sincerity audit: find Linus the most sincere pumpkin patch

Use the `scout_patches` and `audit_noise` tools.

1. **Pick the borough.** Map any neighborhood to its borough first
   (Astoria → QUEENS, Bushwick → BROOKLYN, East Village → MANHATTAN).
2. **Scout.** Call `scout_patches` once for that borough with `limit` 5.
3. **Audit.** Call `audit_noise` once per *distinct* zipcode from step 2
   (default 7 days). Gardens that share a zip share a score.
4. **Rank.** Sort gardens by `sincerity_score`, highest first. Use the score
   and label the tool returns. Never compute or adjust the score yourself.
5. **Report** a short Markdown table, then one sentence naming the winner:

   | Rank | Garden | Address | Zip | Noise (7d) | Score | Label |

6. **If a tool call fails**, say which garden or zip failed and leave that
   row out. Never invent a count.
