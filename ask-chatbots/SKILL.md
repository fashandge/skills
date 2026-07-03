---
name: ask-chatbots
description: Query Gemini, ChatGPT or more chatbots (Grok, Claude, and DeepSeek, when specified) in parallel via a self-spawned logged-in Chrome. Output goes to a temp file; optional wiki integration via the /wiki skill.
---

# Ask Chatbots

Use this when you want to ask the same question to multiple AI chatbots and compare responses.

**Supported chatbots**: gemini, chatgpt, grok, claude, deepseek

**Default**: gemini + chatgpt

## Trigger phrases

- compare chatbot answers
- ask Gemini / ChatGPT / Grok / Claude / DeepSeek the same question
- run parallel chatbot queries

## How it works

Spawns its own Chrome via the `logged-in-chrome` project in COW (copy-on-write) mode — an instant APFS clone of your real Chrome profile, so every site is already signed in. Opens a tab per chatbot, sends the prompt, captures the full rendered response, optionally asks Gemini for a synthesis.

## Usage

```bash
ML=/opt/homebrew/Caskroom/miniconda/base/envs/ml/bin/python

# Default: Gemini + ChatGPT, headed window left open, summary only
$ML ~/skills/ask-chatbots/scripts/ask_chatbots.py --question "la weather tomorrow"

# All five chatbots, include individual responses
$ML ~/skills/ask-chatbots/scripts/ask_chatbots.py \
  --chatbots gemini,chatgpt,grok,claude,deepseek \
  --include-responses \
  --question "compare VRT vs ETN for a swing trade"

# Save to wiki (no content on stdout, agent calls /wiki skill)
$ML ~/skills/ask-chatbots/scripts/ask_chatbots.py \
  --wiki \
  --question "best places to hike in bay area"
```

## CLI flags

| Flag | Default | Description |
|---|---|---|
| `--question` | *(required)* | Prompt sent to each chatbot |
| `--chatbots` | `gemini,chatgpt` | Comma-separated list |
| `--timeout-seconds` | `300` | Per-chatbot wait cap |
| `--skip-summary` | off | Skip the Gemini synthesis step |
| `--include-responses` | off | Print per-bot responses alongside the summary |
| `--headless` | off | No visible browser window |
| `--no-keep-open` | off | Close browser after capture (default: leave it open) |
| `--stdout` | off | Print output to stdout instead of a temp file |
| `--wiki` | off | Write output to a temp file, print only the path. The **agent** then delegates to the `/wiki` skill (passing the file path, not the content) to save as an Obsidian note. |

## Output modes

### Default
Writes responses to a temp file at `/var/folders/.../ask-chatbots-XXXX.txt`. Prints the file path followed by the full file content to stdout.

### `--stdout`
Prints everything to stdout (same output, no temp file).

### `--wiki`
Writes all output to a temp file (same as default). Prints **only the file path** — no content on stdout. The agent is responsible for:
1. Delegating to the `/wiki` skill with a **slim pointer, not inlined content**: the question asked, the temp file path, and which section of the file to use as the body:
   - **Multi-bot**: the `=== GEMINI SUMMARY ===` section
   - **Single-bot**: the `=== {BOT} FULL RESPONSE ===` section (or the whole file if it's the only content)

   `/wiki` reads the file itself. Do NOT paste the file content into the `/wiki` prompt — re-inlining it dilutes `/wiki`'s own instructions in its attention budget and produces worse articles (same rationale as `research-notes`' slim handoff).
2. After `/wiki` returns: cleaning up the temp file and reporting the wiki note path to the user

## Agent delivery rules

**Default / `--stdout`**: print the script's stdout verbatim. No framing or reformatting.

**`--wiki`**: the script prints only the temp file path. Delegate to `/wiki` with the question + temp file path + section pointer (no inlined content), wait for `/wiki` to return, clean up the temp file, then print only the wiki note path returned by `/wiki` as the final response.

## Implementation

All DOM interaction, response capture, waiting logic, and output formatting is self-contained in the script at `~/skills/ask-chatbots/scripts/ask_chatbots.py`. The script's docstring has the full implementation notes.

For testing patterns (mocking `ASKERS`, the page object, Chrome context, and output mode verification), see `references/testing.md`.
