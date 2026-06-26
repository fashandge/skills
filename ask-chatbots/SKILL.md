---
name: ask-chatbots
description: Query Gemini, ChatGPT, Grok, Claude, and DeepSeek in parallel via a self-spawned logged-in Chrome. Output goes to a temp file; only the file path is printed to stdout (zero LLM tokens spent on response body).
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

Spawns its own Chrome via the `logged-in-chrome` project in COW (copy-on-write) mode — an instant APFS clone of your real Chrome profile, so every site is already signed in. Opens a tab per chatbot, sends the prompt, captures the full rendered response, optionally asks Gemini for a synthesis. Output is written to a temp file; only the file path is printed to stdout.

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

# Headless, no browser window
$ML ~/skills/ask-chatbots/scripts/ask_chatbots.py \
  --headless \
  --question "la weather tomorrow"
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

## Output

- **Default**: writes responses to a temp file at `/var/folders/.../ask-chatbots-XXXX.txt`. Prints the file path followed by the full file content to stdout.
- **`--stdout`**: prints everything to stdout (same output, no temp file).
- **`--headless` or `--no-keep-open`**: browser auto-closes; output still printed.
- **`--include-responses`**: includes each bot's `=== {BOT} FULL RESPONSE ===` section.
- **Single chatbot**: always writes the full response (no summary for one bot).

## Agent delivery rule

**Print the script's stdout verbatim as the final response.** Do not add framing commentary, reformatting, or bullet-point rewrites on top of what the script printed. The script prints the file path then the content — both are the answer.

## Implementation

All DOM interaction, response capture, waiting logic, and output formatting is self-contained in the script at `~/skills/ask-chatbots/scripts/ask_chatbots.py`. The script's docstring has the full implementation notes.
