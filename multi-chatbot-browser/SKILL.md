---
name: multi-chatbot-browser
description: Query Gemini, ChatGPT, and Grok in parallel using the existing local Chrome instance over CDP, optionally reuse tabs, capture full responses as rendered, and optionally ask Gemini for a final cross-chatbot summary.
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
- Use the existing local Chrome window connected to CDP on port 9222.
- By default, open a new tab for each requested chatbot.
- If --reuse-tabs is set, reuse an existing chatbot tab when available.
- Send the same prompt to each chatbot in parallel.
- Wait for each chatbot response independently, with a per-chatbot timeout.
- Capture the full response text as it appears in the page body.
- By default, after collecting multiple chatbot responses, ask Gemini for a final synthesis.
- If --skip-summary is set, skip the Gemini synthesis step.
- Do not summarize, paraphrase, or trim the per-chatbot responses unless the user explicitly asks for that.

## Trigger phrases

Use this skill when the user asks to:
- compare chatbot answers
- ask Gemini / ChatGPT / Grok the same question
- run parallel chatbot queries
- capture full responses from AI websites

## Companion script

A ready-to-run script lives at:

```bash
~/.hermes/skills/openclaw-imports/multi-chatbot-browser/scripts/multi_chatbot_browser.py
```

Examples:

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/ml/bin/python ~/.hermes/skills/openclaw-imports/multi-chatbot-browser/scripts/multi_chatbot_browser.py \
  --question "la weather tomorrow"

/opt/homebrew/Caskroom/miniconda/base/envs/ml/bin/python ~/.hermes/skills/openclaw-imports/multi-chatbot-browser/scripts/multi_chatbot_browser.py \
  --chatbots gemini,chatgpt,grok \
  --question "compare VRT vs ETN for a swing trade"

/opt/homebrew/Caskroom/miniconda/base/envs/ml/bin/python ~/.hermes/skills/openclaw-imports/multi-chatbot-browser/scripts/multi_chatbot_browser.py \
  --chatbots gemini,chatgpt,grok \
  --reuse-tabs \
  --timeout-seconds 90 \
  --question "best way for browser automation for AI agents"

/opt/homebrew/Caskroom/miniconda/base/envs/ml/bin/python ~/.hermes/skills/openclaw-imports/multi-chatbot-browser/scripts/multi_chatbot_browser.py \
  --chatbots gemini,chatgpt,grok \
  --reuse-tabs \
  --skip-summary \
  --question "compare reviews of browser-use/browser-use and vercel-labs/agent-browser"
```

## Command-line workflow

This skill assumes the local Chrome instance is already running with remote debugging enabled on port 9222.

Use the script above for the full working example; it implements the same logic described in this skill.

## Recommended invocation pattern

Use an explicit chatbot list and a single question.

Examples:

```bash
# Default: Gemini + ChatGPT
CHATBOTS="gemini,chatgpt"
QUESTION="la weather tomorrow"

# Gemini only
CHATBOTS="gemini"
QUESTION="what's the outlook for NVDA this quarter?"

# Gemini + ChatGPT + Grok
CHATBOTS="gemini,chatgpt,grok"
QUESTION="compare VRT vs ETN for a swing trade"

# Reuse existing tabs when available
CHATBOTS="gemini,chatgpt,grok"
QUESTION="SFO weather tomorrow"
```
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

- Gemini: wait for a new response block after the current turn baseline, then wait for the text to stabilize.
- ChatGPT: wait for a substantive assistant turn, not an intermediate `Thinking` / `Thought for ...` stub.
- Grok: wait for a substantive rendered response, not just an echoed copy of the user prompt.

If the page is still streaming, keep waiting until the answer looks complete or the timeout expires.

## Summary rules

- If more than one chatbot was queried and `--skip-summary` is not set, submit a final prompt to Gemini asking it to:
  - summarize common points
  - identify disagreements or differences in emphasis
  - print a side-by-side comparison
- Reuse the same Gemini tab when possible to avoid opening extra tabs.
- Capture Gemini's summary as a separate later turn, not as a replacement for Gemini's original answer.
- If Gemini was not one of the original requested chatbots, open or reuse a Gemini tab for the final synthesis.

## Notes and pitfalls

- Gemini often uses a contenteditable input rather than a textarea.
- ChatGPT may expose both a hidden textarea and a visible contenteditable editor.
- Grok commonly uses a ProseMirror contenteditable editor.
- By default, open fresh tabs for the requested chatbots.
- Only reuse existing chatbot tabs when `--reuse-tabs` is set.
- Always connect to the existing Chrome instance through CDP rather than launching a separate browser.
- On this environment, the most reliable connection path is: `GET http://127.0.0.1:9222/json/version` -> use `webSocketDebuggerUrl` -> `playwright.chromium.connect_over_cdp(...)`.
- The agent-browser CLI wrapper may fail with a 500 on this setup; direct Playwright CDP works reliably.
- If a chatbot has not been authenticated yet, stop and let the user handle login in the visible browser.
- Use `/opt/homebrew/Caskroom/miniconda/base/envs/ml/bin/python` for Python execution in this environment.

## Verification

A successful run should print one section per requested chatbot, each containing the full text response captured from that page.

If summary is enabled and more than one chatbot was queried, it should also print a final Gemini synthesis block.

Example output structure:

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
