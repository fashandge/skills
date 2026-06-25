#!/usr/bin/env python3
"""Query Gemini / ChatGPT / Grok / Claude / DeepSeek in parallel in a self-spawned logged-in Chrome.

Instead of attaching to a pre-running Chrome on port 9222, this spawns its own
**logged-in** Chrome via the ``logged-in-chrome`` project in COW (copy-on-write)
mode: an instant APFS clone of your real Chrome profile, so every
site is already signed in — including Gemini/Google, whose rotating tokens can't
be snapshotted into a cookie file.

By default the browser is **headed and left open** after answering so you can keep
using it; a detached watcher removes the temp profile when you close the window.
Pass ``--headless`` to run with no window (auto-closes when done), or
``--no-keep-open`` to auto-close the headed window.

- Opens a fresh tab for each requested chatbot
- Sends the same question to one or more chatbots in parallel
- Captures the full rendered response text as shown on the page

Requires:
  - the ``logged-in-chrome`` project importable as ``browser.src.logged_in_chrome``
    (it lives at ~/projects/browser/src; ~/projects is on sys.path via the ml env's
    editable ``projects`` install, so the import resolves with no PYTHONPATH needed)
  - a system Google Chrome install + playwright / playwright-stealth in the ml env

Example:
  python scripts/ask_chatbots.py --question "la weather tomorrow"
  python scripts/ask_chatbots.py --chatbots gemini,chatgpt,grok,claude,deepseek --question "compare VRT vs ETN"
  python scripts/ask_chatbots.py --headless --question "la weather tomorrow"
  python scripts/ask_chatbots.py --no-keep-open --question "la weather tomorrow"
  python scripts/ask_chatbots.py --chatbots chatgpt,gemini,grok,claude --skip-summary --question "compare VRT vs ETN"
"""

from __future__ import annotations

import argparse
import asyncio
import re

# logged-in-chrome lives at ~/projects/browser/src. ~/projects is on sys.path (the
# editable `projects` install), so import the module by its absolute namespace path —
# no PYTHONPATH or sys.path hacks needed.
from browser.src import logged_in_chrome

URLS = {
    "gemini": "https://gemini.google.com/",
    "chatgpt": "https://chatgpt.com/",
    "grok": "https://grok.com/",
    "claude": "https://claude.ai/new",
    "deepseek": "https://chat.deepseek.com/",
}

DEFAULT_CHATBOTS = ["gemini", "chatgpt"]
VALID_CHATBOTS = set(URLS)


def parse_chatbots(value: str | None) -> list[str]:
    if not value:
        bots = DEFAULT_CHATBOTS
    else:
        bots = [x.strip().lower() for x in value.split(",") if x.strip()]

    deduped: list[str] = []
    seen = set()
    for bot in bots:
        if bot not in VALID_CHATBOTS:
            raise SystemExit(
                f"Unknown chatbot '{bot}'. Valid options: gemini, chatgpt, grok, claude, deepseek"
            )
        if bot not in seen:
            deduped.append(bot)
            seen.add(bot)
    return deduped


async def open_chatbot(ctx, bot: str):
    page = await ctx.new_page()
    await page.goto(URLS[bot], wait_until="domcontentloaded")
    await page.wait_for_timeout(5000)
    return page


async def last_nonempty_inner_text(locator) -> str:
    count = await locator.count()
    for i in range(count - 1, -1, -1):
        try:
            text = (await locator.nth(i).inner_text()).strip()
        except Exception:
            continue
        if text:
            return text
    return ""


# Reads an element's text like innerText (layout-aware line breaks) but rewrites every
# <a href> into inline Markdown `[text](url)` so body links survive capture instead of
# being flattened away. Works on an offscreen clone, so the live page is untouched.
LINKED_INNER_TEXT_JS = """
(el) => {
  const cleanUrl = (raw) => {
    try {
      const u = new URL(raw);
      // ChatGPT appends utm_source=chatgpt.com (and friends) to every source link.
      if (u.searchParams.get('utm_source') === 'chatgpt.com') {
        ['utm_source', 'utm_medium', 'utm_campaign'].forEach(p => u.searchParams.delete(p));
      }
      return u.toString().replace(/\\?$/, '');
    } catch {
      return raw;
    }
  };
  const clone = el.cloneNode(true);
  clone.querySelectorAll('a[href]').forEach(a => {
    const href = a.href ? cleanUrl(a.href) : '';
    if (!href) return;
    const t = (a.textContent || '').replace(/\\s+/g, ' ').trim();
    a.textContent = t ? `[${t}](${href})` : `(${href})`;
  });
  clone.style.position = 'absolute';
  clone.style.left = '-99999px';
  clone.style.top = '0';
  document.body.appendChild(clone);
  const text = clone.innerText;
  clone.remove();
  return text;
}
"""


async def last_nonempty_linked_text(locator) -> str:
    """Like last_nonempty_inner_text, but preserves <a href> links as inline Markdown."""
    count = await locator.count()
    for i in range(count - 1, -1, -1):
        try:
            handle = await locator.nth(i).element_handle()
            if handle is None:
                continue
            text = (await handle.evaluate(LINKED_INNER_TEXT_JS)).strip()
        except Exception:
            continue
        if text:
            return text
    return ""


async def wait_for_stable_text(
    extractor,
    baseline: str,
    *,
    polls: int = 60,
    delay_ms: int = 2000,
    stable_rounds: int = 3,
    min_length: int = 20,
) -> str:
    last_seen = ""
    stable_count = 0

    for _ in range(polls):
        await asyncio.sleep(delay_ms / 1000)
        current = (await extractor()).strip()
        if not current or current == baseline or len(current) < min_length:
            continue

        if current == last_seen:
            stable_count += 1
        else:
            last_seen = current
            stable_count = 1

        if stable_count >= stable_rounds:
            return current

    return last_seen or (await extractor()).strip()


async def extract_gemini_response(page) -> str:
    return await last_nonempty_inner_text(
        page.locator("message-content, div.response-container-content")
    )


def gemini_response_locator(page):
    return page.locator("message-content, div.response-container-content")


async def extract_new_gemini_response(page, baseline_count: int) -> str:
    locator = gemini_response_locator(page)
    count = await locator.count()
    for i in range(count - 1, baseline_count - 1, -1):
        try:
            text = (await locator.nth(i).inner_text()).strip()
        except Exception:
            continue
        if text:
            return text
    return ""


async def gemini_response_complete(text: str) -> bool:
    cleaned = text.strip()
    if len(cleaned) < 15:  # short factual answers are valid; stability gate guards mid-stream
        return False

    low = cleaned.lower()
    if low in {"gemini said", "answer now", "defining the user's need"}:
        return False

    scaffold_markers = [
        "gemini said",
        "answer now",
        "defining the user's need",
    ]
    if any(marker in low for marker in scaffold_markers) and len(cleaned) < 250:
        return False

    return True


async def extract_chatgpt_response(page) -> str:
    assistant_turns = page.locator(
        'section[data-testid^="conversation-turn-"]'
    ).filter(has=page.locator('[data-message-author-role="assistant"]'))
    text = await last_nonempty_linked_text(assistant_turns)
    if text:
        return re.sub(r"\nThought for \d+s\s*\n?", "\n", text).strip()
    text = await last_nonempty_linked_text(
        page.locator('[data-message-author-role="assistant"]')
    )
    return re.sub(r"\nThought for \d+s\s*\n?", "\n", text).strip()


async def chatgpt_response_complete(page, text: str) -> bool:
    cleaned = text.strip()
    if len(cleaned) < 40:
        return False

    # Reused ChatGPT tabs often surface a short assistant preamble plus
    # "Thinking" before the substantive body arrives.
    if re.search(r"Thought for .*seconds?$", cleaned) or cleaned.endswith("Thinking"):
        if len(cleaned) < 400:
            return False

    assistant_turns = page.locator(
        'section[data-testid^="conversation-turn-"]'
    ).filter(has=page.locator('[data-message-author-role="assistant"]'))
    count = await assistant_turns.count()
    if count == 0:
        return False

    last_turn = assistant_turns.nth(count - 1)
    assistant_blocks = await last_turn.locator('[data-message-author-role="assistant"]').count()
    if assistant_blocks < 2 and len(cleaned) < 400:
        return False

    return True


async def extract_grok_response(page) -> str:
    text = await last_nonempty_inner_text(
        page.locator("#last-reply-container .response-content-markdown")
    )
    return text.strip()


async def grok_response_complete(text: str, question: str) -> bool:
    cleaned = text.strip()
    if len(cleaned) < 15:  # short factual answers are valid; stability gate guards mid-stream
        return False

    question_norm = " ".join(question.split()).strip().lower()
    cleaned_norm = " ".join(cleaned.split()).strip().lower()
    if cleaned_norm == question_norm:
        return False

    return True


def claude_response_locator(page):
    return page.locator(".font-claude-response")


async def extract_new_claude_response(page, baseline_count: int) -> str:
    locator = claude_response_locator(page)
    count = await locator.count()
    for i in range(count - 1, baseline_count - 1, -1):
        try:
            response = locator.nth(i)
            markdown = response.locator(".standard-markdown, .progressive-markdown")
            markdown_count = await markdown.count()
            parts = []
            for j in range(markdown_count):
                part = (await markdown.nth(j).inner_text()).strip()
                if part:
                    parts.append(part)
            text = "\n\n".join(parts).strip()
            if not text:
                text = (await response.inner_text()).strip()
        except Exception:
            continue
        if text:
            return text
    return ""


async def claude_response_complete(text: str, question: str) -> bool:
    cleaned = text.strip()
    if not cleaned:
        return False

    transient_markers = [
        "identified need",
        "searching the web",
        "i'll research",
        "let me get more detail",
        "assessing ",
        "synthesized ",
    ]
    if len(cleaned) < 500 and any(marker in cleaned.lower() for marker in transient_markers):
        return False

    question_norm = " ".join(question.split()).strip().lower()
    cleaned_norm = " ".join(cleaned.split()).strip().lower()
    if cleaned_norm == question_norm:
        return False

    return True


async def claude_response_finished(page) -> bool:
    # Primary signal: each assistant turn is wrapped in <div data-is-streaming="true|false">,
    # which stays "true" through tool use / web search even while the visible text is frozen
    # — more reliable than text stability, the Stop button, or a11y status strings.
    flags = page.locator("[data-is-streaming]")
    n = await flags.count()
    if n:
        if await page.locator('[data-is-streaming="true"]').count():
            return False
        last = await flags.nth(n - 1).get_attribute("data-is-streaming")
        return last == "false"

    # Fallbacks if the attribute ever disappears (DOM change): stop button / a11y status.
    if await page.locator('button[aria-label*="Stop" i]:visible').count():
        return False

    try:
        body = await page.locator("body").inner_text(timeout=2000)
    except Exception:
        return False

    if "Claude is responding" in body:
        return False
    if "Claude finished the response" in body:
        return True

    # Claude can briefly omit the accessible status marker on short responses;
    # in that case the absence of the stop button is enough after text exists.
    return True


async def ask_gemini(page, question: str) -> str:
    prompt = page.locator('[contenteditable="true"]:visible').first
    await prompt.click()
    await prompt.fill(question)
    baseline_count = await gemini_response_locator(page).count()
    await prompt.press("Enter")

    last_seen = ""
    stable_count = 0
    for _ in range(60):
        await asyncio.sleep(2)
        current = (await extract_new_gemini_response(page, baseline_count)).strip()
        if not current:
            continue
        if not await gemini_response_complete(current):
            continue

        if current == last_seen:
            stable_count += 1
        else:
            last_seen = current
            stable_count = 1

        if stable_count >= 2:
            return current

    return last_seen or (await extract_new_gemini_response(page, baseline_count)).strip()


async def ask_chatgpt(page, question: str) -> str:
    prompt = page.locator('[contenteditable="true"]:visible, textarea:visible').first
    await prompt.click()
    await prompt.fill(question)
    baseline = await extract_chatgpt_response(page)
    await prompt.press("Enter")

    last_seen = ""
    stable_count = 0
    for _ in range(60):
        await asyncio.sleep(2)
        current = (await extract_chatgpt_response(page)).strip()
        if not current or current == baseline:
            continue
        if not await chatgpt_response_complete(page, current):
            continue

        if current == last_seen:
            stable_count += 1
        else:
            last_seen = current
            stable_count = 1

        if stable_count >= 2:
            return current

    return last_seen or (await extract_chatgpt_response(page)).strip()


async def ask_grok(page, question: str) -> str:
    prompt = page.locator('[contenteditable="true"]:visible').first
    await prompt.click()
    await prompt.fill(question)
    baseline = await extract_grok_response(page)
    await prompt.press("Enter")

    last_seen = ""
    stable_count = 0
    for _ in range(60):
        await asyncio.sleep(2)
        current = (await extract_grok_response(page)).strip()
        if not current or current == baseline:
            continue
        if not await grok_response_complete(current, question):
            continue

        if current == last_seen:
            stable_count += 1
        else:
            last_seen = current
            stable_count = 1

        if stable_count >= 2:
            return current

    return last_seen or (await extract_grok_response(page)).strip()


async def ask_claude(page, question: str) -> str:
    prompt = page.locator(
        'div.ProseMirror[contenteditable="true"], [contenteditable="true"]:visible, textarea:visible'
    ).first
    await prompt.click()
    try:
        await prompt.fill(question)
    except Exception:
        await page.keyboard.insert_text(question)

    baseline_count = await claude_response_locator(page).count()
    send_button = page.locator('button[aria-label*="Send" i]:visible').last
    if await send_button.count():
        await send_button.click()
    else:
        await prompt.press("Enter")

    last_seen = ""
    stable_count = 0
    # Higher budget than the other bots: Claude may run a web search before writing, so the
    # outer --timeout-seconds (not this inner loop) should govern how long it may take.
    for _ in range(150):
        await asyncio.sleep(2)
        current = (await extract_new_claude_response(page, baseline_count)).strip()
        if not current:
            continue
        if not await claude_response_complete(current, question):
            continue
        if not await claude_response_finished(page):
            last_seen = current
            stable_count = 0
            continue

        if current == last_seen:
            stable_count += 1
        else:
            last_seen = current
            stable_count = 1

        if stable_count >= 2:
            return current

    return last_seen or (await extract_new_claude_response(page, baseline_count)).strip()


def deepseek_response_locator(page):
    # Each finished assistant turn renders its body in this markdown node. The COW
    # profile clone carries prior conversation history, so baseline-count the nodes
    # before sending and read only the new one after.
    return page.locator(".ds-markdown.ds-assistant-message-main-content")


async def extract_new_deepseek_response(page, baseline_count: int) -> str:
    locator = deepseek_response_locator(page)
    count = await locator.count()
    for i in range(count - 1, baseline_count - 1, -1):
        try:
            text = (await locator.nth(i).inner_text()).strip()
        except Exception:
            continue
        if text:
            return text
    return ""


async def deepseek_response_complete(text: str, question: str) -> bool:
    cleaned = text.strip()
    if len(cleaned) < 15:  # short factual answers are valid; stability gate guards mid-stream
        return False

    question_norm = " ".join(question.split()).strip().lower()
    cleaned_norm = " ".join(cleaned.split()).strip().lower()
    if cleaned_norm == question_norm:
        return False

    return True


async def ask_deepseek(page, question: str) -> str:
    prompt = page.locator("textarea:visible").first
    await prompt.click()
    await prompt.fill(question)
    baseline_count = await deepseek_response_locator(page).count()
    await prompt.press("Enter")

    last_seen = ""
    stable_count = 0
    for _ in range(60):
        await asyncio.sleep(2)
        current = (await extract_new_deepseek_response(page, baseline_count)).strip()
        if not current:
            continue
        if not await deepseek_response_complete(current, question):
            continue

        if current == last_seen:
            stable_count += 1
        else:
            last_seen = current
            stable_count = 1

        if stable_count >= 2:
            return current

    return last_seen or (await extract_new_deepseek_response(page, baseline_count)).strip()


def build_gemini_summary_prompt(question: str, chatbots: list[str], results: dict[str, str]) -> str:
    parts = [
        f'Please read the following chatbot responses to the question: "{question}"',
        "",
        "Then do three things:",
        "1. Give a high-level summary of the common points across the responses.",
        "2. Identify the main disagreements or differences in emphasis.",
        "3. Provide a side-by-side comparison table across important aspects.",
        "",
        "Here are the responses.",
        "",
    ]
    for bot in chatbots:
        parts.append(f"=== {bot.upper()} RESPONSE ===")
        parts.append(results[bot])
        parts.append("")
    return "\n".join(parts).strip()


ASKERS = {
    "gemini": ask_gemini,
    "chatgpt": ask_chatgpt,
    "grok": ask_grok,
    "claude": ask_claude,
    "deepseek": ask_deepseek,
}


async def run(
    chatbots: list[str],
    question: str,
    timeout_seconds: int,
    skip_summary: bool,
    headed: bool = True,
    keep_open: bool = True,
) -> int:
    # Spawn our own logged-in Chrome (COW clone of the real profile → every site
    # signed in, Gemini included); headed by default. Temp profile auto-cleaned on exit.
    async with logged_in_chrome.AsyncLoggedInChrome(
        use_copy_on_write_profile=True, headless=not headed
    ) as cow:
        ctx = cow.browser.contexts[0]

        opened = await asyncio.gather(*(open_chatbot(ctx, bot) for bot in chatbots))
        pages = dict(zip(chatbots, opened))

        async def ask_one(bot: str) -> tuple[str, str]:
            try:
                answer = await asyncio.wait_for(
                    ASKERS[bot](pages[bot], question), timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                answer = f"[Timed out after {timeout_seconds}s waiting for {bot} response]"
            return bot, answer

        results = dict(await asyncio.gather(*(ask_one(bot) for bot in chatbots)))

        for bot in chatbots:
            print(f"\n=== {bot.upper()} FULL RESPONSE ===")
            print(results[bot])

        if not skip_summary and len(chatbots) > 1:
            gemini_page = pages.get("gemini")
            if gemini_page is None:
                gemini_page = await open_chatbot(ctx, "gemini")

            summary_prompt = build_gemini_summary_prompt(question, chatbots, results)
            try:
                summary = await asyncio.wait_for(
                    ask_gemini(gemini_page, summary_prompt), timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                summary = f"[Timed out after {timeout_seconds}s waiting for gemini summary]"

            print("\n=== GEMINI SUMMARY ===")
            print(summary)

        if keep_open:
            # Hand Chrome + its temp profile to a detached watcher and leave the
            # window open. The watcher removes the profile when you close the
            # browser. __aexit__ below only disconnects Playwright (Chrome stays up).
            cow.detach()
            print("\n[Browser left open — close the window when done; "
                  "its temporary profile is removed automatically.]")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--chatbots",
        default=",".join(DEFAULT_CHATBOTS),
        help="Comma-separated list of chatbots: gemini, chatgpt, grok, claude, deepseek (default: gemini,chatgpt)",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=300,
        help="Maximum seconds to wait for each chatbot response (default: 300)",
    )
    parser.add_argument(
        "--skip-summary",
        action="store_true",
        help="Skip the final Gemini summary/comparison step",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run with no visible window (default: a headed window left open for you). "
             "Implies the browser auto-closes when done.",
    )
    parser.add_argument(
        "--no-keep-open",
        action="store_true",
        help="Close the browser as soon as answers are captured (default: leave the "
             "headed window open; a watcher removes the temp profile when you close it).",
    )
    parser.add_argument("--question", required=True, help="Question to send to each chatbot")
    args = parser.parse_args(argv)

    chatbots = parse_chatbots(args.chatbots)
    if args.timeout_seconds <= 0:
        raise SystemExit("--timeout-seconds must be greater than 0")

    # Default: headed + keep the window open. --headless turns off both (a headless
    # window can't be closed by hand, so keeping it open would linger forever).
    headed = not args.headless
    keep_open = headed and not args.no_keep_open

    return asyncio.run(
        run(
            chatbots,
            args.question,
            args.timeout_seconds,
            args.skip_summary,
            headed,
            keep_open,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
