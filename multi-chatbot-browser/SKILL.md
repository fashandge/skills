---
name: multi-chatbot-browser
description: Query Gemini, ChatGPT, and Grok in parallel by spawning a self-managed logged-in headless Chrome (copy-on-write clone of the real profile, so every site is already signed in), capture full responses as rendered, and optionally ask Gemini for a final cross-chatbot summary.
---

# Multi-Chatbot Browser Queries

Use this skill when the user wants to ask the same question to multiple AI chatbots and compare responses side by side.

Supported chatbots:
- gemini
- chatgpt
- grok

Default selection:
- gemini
- chatgpt

Behavior:
- Spawn a self-managed, **logged-in** Chrome via the `logged-in-chrome` project in **COW (copy-on-write) mode** — an instant APFS clone of the real Chrome profile, so every site (Gemini/Google included) is already signed in. Headless by default; pass `--headed` for a visible window. Do **not** depend on a pre-running Chrome or a CDP port.
- Open a fresh tab for each requested chatbot.
- Send the same prompt to each chatbot in parallel.
- Wait for each chatbot response independently, with a per-chatbot timeout.
- Capture the full response text as it appears in the page body.
- By default, after collecting multiple chatbot responses, ask Gemini for a final synthesis.
- If `--skip-summary` is set, skip the Gemini synthesis step.
- Do not summarize, paraphrase, or trim the per-chatbot responses unless the user explicitly asks for that.

## Why COW mode (robustness)

- **Self-contained**: `AsyncLoggedInChrome` launches its own Chrome and a temp profile, then auto-cleans both on exit (context-manager teardown + `atexit` backstop + startup orphan sweep). There is no Chrome window to launch or tear down by hand, and nothing to leave running on port 9222.
- **Always logged in**: a copy-on-write clone of the real profile carries *every* site's live session. This is the only mode that keeps **Gemini/Google** signed in, because their rotating `__Secure-1PSID*` tokens cannot be snapshotted into a cookie file.
- **Headless by default**: no visible window; runs unattended. The project applies stealth + a clean User-Agent under headless so Cloudflare-gated sites (ChatGPT, Grok) still pass. Pass `--headed` to watch the run in a real window (useful for debugging or to handle an unexpected login prompt).

## Trigger phrases

Use this skill when the user asks to:
- compare chatbot answers
- ask Gemini / ChatGPT / Grok the same question
- run parallel chatbot queries
- capture full responses from AI websites

## Companion script

A ready-to-run script lives at:

```bash
~/skills/multi-chatbot-browser/scripts/multi_chatbot_browser.py
```

It imports the module as `browser.src.logged_in_chrome` from the `logged-in-chrome`
project (at `~/projects/browser/src`). `~/projects` is on `sys.path` via the `ml`
env's editable `projects` install, so the import resolves with no `PYTHONPATH`
needed. It spawns the COW browser itself (headless by default).

Run it with the `ml` env Python:

```bash
ML=/opt/homebrew/Caskroom/miniconda/base/envs/ml/bin/python

# Default: Gemini + ChatGPT, with a final Gemini synthesis
$ML ~/skills/multi-chatbot-browser/scripts/multi_chatbot_browser.py \
  --question "la weather tomorrow"

# Three chatbots
$ML ~/skills/multi-chatbot-browser/scripts/multi_chatbot_browser.py \
  --chatbots gemini,chatgpt,grok \
  --question "compare VRT vs ETN for a swing trade"

# Custom timeout, skip the synthesis step
$ML ~/skills/multi-chatbot-browser/scripts/multi_chatbot_browser.py \
  --chatbots gemini,chatgpt,grok \
  --timeout-seconds 90 \
  --skip-summary \
  --question "best way for browser automation for AI agents"

# Visible window (e.g. to debug or clear a login prompt)
$ML ~/skills/multi-chatbot-browser/scripts/multi_chatbot_browser.py \
  --headed \
  --question "la weather tomorrow"
```

The script is the full working example; it implements the logic described below.

## Command-line flags

- `--chatbots` — comma-separated subset of `gemini,chatgpt,grok` (default `gemini,chatgpt`).
- `--question` — the prompt sent to each chatbot (required).
- `--timeout-seconds` — per-chatbot wait cap (default 120).
- `--skip-summary` — skip the final Gemini synthesis.
- `--headed` — show a visible Chrome window (default: headless).

## Input parsing rules

- If no chatbot list is provided, default to `gemini,chatgpt`.
- Accept one or more of: `gemini`, `chatgpt`, `grok`.
- Deduplicate the list while preserving order.
- Fail fast on unknown chatbot names.

## Response capture rules

- Capture the full rendered page body text after the answer is ready.
- Preserve line breaks and punctuation exactly as extracted from the page.
- Do not extract only the final paragraph unless the user explicitly requests a concise answer.
- Keep the assistant response body, not random page chrome or suggestion chips.
- For ChatGPT, strip transient `Thought for ...` lines when they appear in the captured body.
- For Gemini, treat each submitted prompt as a separate turn and capture only the new response after that turn.

## Waiting rules

Because each chatbot loads differently, use a chatbot-specific completion check:

- Gemini: wait for a new response block after the current turn baseline, then wait for the text to stabilize (stable across 2 polls). Short factual answers are valid.
- ChatGPT: wait for a substantive assistant turn, not an intermediate `Thinking` / `Thought for ...` stub.
- Grok: wait for a substantive rendered response, not just an echoed copy of the user prompt.

If the page is still streaming, keep waiting until the answer looks complete or the timeout expires.

## Summary rules

- If more than one chatbot was queried and `--skip-summary` is not set, submit a final prompt to Gemini asking it to:
  - summarize common points
  - identify disagreements or differences in emphasis
  - print a side-by-side comparison
- Reuse the Gemini tab from the original query when one exists; otherwise open a Gemini tab for the final synthesis.
- Capture Gemini's summary as a separate later turn, not as a replacement for Gemini's original answer.

## Notes and pitfalls

- Gemini often uses a contenteditable input rather than a textarea.
- ChatGPT may expose both a hidden textarea and a visible contenteditable editor.
- Grok commonly uses a ProseMirror contenteditable editor.
- The browser is spawned fresh each run, so every chatbot gets a clean new tab — there is no tab reuse and no leftover conversation state.
- Logins come from the COW clone of the real profile. If a chatbot is **not** signed in there, sign into it in your normal Chrome first, then re-run.
- COW mode exposes the *entire* real profile to automation; that is intentional here (Gemini needs it), but keep questions/prompts non-sensitive accordingly.
- Use `/opt/homebrew/Caskroom/miniconda/base/envs/ml/bin/python` for Python execution in this environment.
- Requires a system Google Chrome install plus `playwright` / `playwright-stealth` in the `ml` env (the `logged-in-chrome` project's dependencies).

## Verification

A successful run prints one section per requested chatbot, each containing the full text response captured from that page:

```text
=== GEMINI FULL RESPONSE ===
...

=== CHATGPT FULL RESPONSE ===
...

=== GROK FULL RESPONSE ===
...

=== GEMINI SUMMARY ===
...
```

If summary is enabled and more than one chatbot was queried, it also prints the final Gemini synthesis block. The temp Chrome profile is removed automatically when the run ends.
