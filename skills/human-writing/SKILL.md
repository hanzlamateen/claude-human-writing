---
name: human-writing
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/lint_writing.py *)
description: Use when writing or revising anything other people will read (PR descriptions, issues, commit messages, review replies, docs, READMEs, release notes, status updates, emails, Slack messages, posts, stories), when asked to make text sound human or less like AI or Claude, or to check a draft for AI tells. Holds the rules, a two-pass revision process, before-and-after examples, the evidence behind them and a linter.
---

# Human writing

The rules are in [WRITING.md](WRITING.md) in this folder. Claude Code loads them into every session already; in claude.ai, read that file first. This file is the process for drafts that matter, with examples. The evidence is in [references/storyscope.md](references/storyscope.md) (the study these rules start from) and [references/surface-tells.md](references/surface-tells.md) (word and punctuation tells from other studies).

The main lesson from the study: detectors still caught AI stories after the surface tics were edited out, because the giveaways were in the structure. What gets said, in what order, and what gets left unsaid. So revise the shape first and the words second.

## Process

1. Before drafting, settle two things. Who is reading, and what should they do or know when they finish? The opening sentence should serve that and nothing else.

2. Draft.

3. Shape pass. Go through these questions and fix what they turn up:
   - Does it open with the point, or with background the reader has to wade through?
   - Is there a sentence that explains what the facts mean, or why they matter? Cut it, or swap it for a fact.
   - Does the ending summarise, moralise or look ahead? Cut it, unless it holds real actions with owners or the format asks for it.
   - Is anything presented as settled that isn't? Say what's still open.
   - Is the tone the same for the outage as for the typo? Make the serious part sound serious.
   - Is this the default template? Would anyone miss each section if it went?
   - Does every claim point at something real: a name, number, file, version, quote or link?
   - Is the reader addressed? Does it ask them for what you need?

4. Surface pass. Run the linter on the draft:

   ```
   python3 ${CLAUDE_SKILL_DIR}/scripts/lint_writing.py draft.md      # or pipe text in with -
   ```

   Outside Claude Code, the script is `scripts/lint_writing.py` in this skill's folder. Errors (em dashes, chatbot phrases, AI attribution) must go. Warnings are judgment calls: fix the ones that are reflexes and keep the ones that are right for that sentence. Then look at the stats line. A sentence-length spread (cv) under about 0.35 means the rhythm is too even.

5. Read it once as the recipient. Any sentence that would make a colleague think "a bot wrote this" gets rewritten, even if the linter passed it.

When you fix a dash, rewrite the sentence. Two sentences usually work best, then a comma, then parentheses. A colon or semicolon in every spot where a dash used to be is a new tic, not a fix.

## Examples

### PR description

Before:

```
## Summary
This PR introduces a robust retry mechanism for the pairing flow — ensuring a seamless experience for users on slow networks.

## Changes
- **Retry logic:** Added exponential backoff to the pairing request
- **Timeout handling:** Increased the timeout from 15s to 60s
- **Error messages:** Improved error messaging for clarity

## Test plan
- [x] Unit tests pass
- [x] Manually tested pairing flow

Overall, this change significantly improves reliability and user experience.
```

After:

```
Pairing failed on slow connections because the Hub gave up after 15 seconds, and a cold Portal can take 40 to answer. The Hub now waits up to 60 seconds and retries twice.

Example: pair a Hub over a phone hotspot. Before, "Pairing failed" after 15 seconds, every time. Now it pairs on the first try, about 35 seconds in.

The error now says what to do ("Check the code and try again") instead of just "Pairing failed".

Tested with the pairing unit tests and a real pairing over a throttled link (400 ms added delay). I haven't tested the retry path against a Portal that is actually down.
```

What changed: the reason comes first, with real numbers. The bold-label bullets and the stock "Summary / Test plan" frame are gone. "Robust" and "seamless" became the actual behaviour. The closing claim about reliability is gone because the example already shows it, and the untested part is admitted rather than hidden.

### Commit message

Before: `feat: enhance pairing reliability with robust retry mechanism — ensures seamless pairing on slow networks`

After:

```
Wait up to 60s for the pairing reply and retry twice

A cold Portal can take 40s to answer, so the old 15s limit failed
every pairing over a slow link.
```

### Issue

Before:

```
## Overview
Users may potentially experience issues when attempting to update the desktop app. This could impact the overall user experience and is worth investigating further.
```

After:

```
In simple words: on Fedora 42 the desktop app downloads the update, asks for a restart, and then opens the old version again.

Example: on 0.2.77, click "Update now", then "Restart". The About page still says 0.2.77. Expected 0.2.78.

Seen on two machines. Ubuntu 24.04 updates fine. I haven't found the cause yet; the update log ends after "staged".
```

### Status update

Before: "Here's a quick update on where things stand! We've made great progress this week — the pairing fix is merged and the update flow is looking solid. Next steps: continue testing and finalize the release."

After: "Pairing fix is merged (#1581). The Fedora update bug is still open and I don't know the cause yet, so the release waits on it. I'll have an answer or a workaround by Thursday."

### Reply to a reviewer

Before: "Great catch! You're absolutely right — I've updated the logic to handle this edge case. Let me know if you have any other questions!"

After: "Fixed in 3f2a1c9. Empty lists now return 200 with `[]` instead of 404, and there's a test for it."

### Story paragraph

Before:

```
Sarah's chest tightened as she stepped into the kitchen. The air smelled of burnt coffee and something else — something like regret. Rain streaked the window, mirroring the tears she refused to let fall. In that moment she understood that forgiveness was never about her father. It was about her.
```

After:

```
Sarah was angry, and she knew it, which made it worse. Her father had made coffee for two, as if nothing had happened.
"You're up early," he said.
She took the cup. She didn't drink it.
```

The emotion is named instead of acted out in her chest. There's no smell, no rain matching her mood and no stated lesson. Dialogue and an action carry the rest.

## Fiction

The study measured stories, so for fiction its findings apply directly. Next to the general rules:

- Name an emotion now and then ("she was afraid"). AI shows fear through a tight chest and cold sweat 81% of the time; people do it 38% of the time.
- Ease off smell and other sensory detail, and let the weather and the rooms stay out of the characters' moods.
- Don't let the narrator or a character explain the theme. No philosophical debates in dialogue unless the characters would really have them.
- Tell it out of order when that helps: open late, flash back, hold a reveal that makes earlier scenes read differently.
- Give it a subplot or two, more places and more dialogue. Introduce people through what they say or do, not a description.
- Let the protagonist be partly in the wrong. Let the ending stay unresolved, or turn on something outside the protagonist's control, rather than an inner realisation.
- Name real books, songs, brands and places when the characters would. Speak to the reader if the voice allows it.
- Against Claude's own habits: escalate, and make the climax bigger than the opening. Vary the voices so characters don't all sound like the narrator. Break a convention on purpose. Skip the epilogue, and end on the avalanche, not the quiet morning after.
