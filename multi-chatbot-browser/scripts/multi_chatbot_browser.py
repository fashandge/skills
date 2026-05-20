#!/usr/bin/env python3
"""Query Gemini / ChatGPT / Grok in the existing local Chrome session.

- Opens a new tab for each requested chatbot, or reuses matching tabs with
  ``--reuse-tabs``
- Sends the same question to one or more chatbots in parallel
- Captures the full rendered response text as shown on the page

Requires:
  - local Chrome running with remote debugging on 127.0.0.1:9222
  - playwright installed in the active Python environment
  - requests installed (usually already present)

Example:
  python scripts/multi_chatbot_browser.py --question "la weather tomorrow"
  python scripts/multi_chatbot_browser.py --chatbots gemini,chatgpt,grok --question "compare VRT vs ETN"
  python scripts/multi_chatbot_browser.py --chatbots gemini,chatgpt,grok --timeout-seconds 45 --question "compare VRT vs ETN"
  python scripts/multi_chatbot_browser.py --chatbots chatgpt,gemini,grok --skip-summary --question "compare VRT vs ETN"
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from typing import Iterable

import requests
from playwright.async_api import async_playwright
from playwright._impl._errors import TargetClosedError

URLS = {
    "gemini": "https://gemini.google.com/",
    "chatgpt": "https://chatgpt.com/",
    "grok": "https://grok.com/",
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
                f"Unknown chatbot '{bot}'. Valid options: gemini, chatgpt, grok"
            )
        if bot not in seen:
            deduped.append(bot)
            seen.add(bot)
    return deduped


def ensure_browser_ws() -> str:
    try:
        data = requests.get("http://127.0.0.1:9222/json/version", timeout=5).json()
    except Exception as exc:
        raise SystemExit(
            "Could not reach Chrome CDP at http://127.0.0.1:9222/json/version. "
            "Make sure local Chrome is running with remote debugging enabled."
        ) from exc
    ws = data.get("webSocketDebuggerUrl")
    if not ws:
        raise SystemExit("Chrome CDP did not return a webSocketDebuggerUrl")
    return ws


async def open_new_page(ctx, bot: str):
    page = await ctx.new_page()
    await page.goto(URLS[bot], wait_until="domcontentloaded")
    await page.wait_for_timeout(5000)
    return page


async def find_or_open_page(ctx, bot: str):
    for page in ctx.pages:
        try:
            if page.is_closed():
                continue
            url = page.url
        except Exception:
            continue
        if bot == "gemini" and "gemini.google.com" in url:
            return page
        if bot == "chatgpt" and ("chatgpt.com" in url or "chat.openai.com" in url):
            return page
        if bot == "grok" and "grok.com" in url:
            return page
    return await open_new_page(ctx, bot)


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
    if len(cleaned) < 40:
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
    text = await last_nonempty_inner_text(assistant_turns)
    if text:
        return re.sub(r"\nThought for \d+s\s*\n?", "\n", text).strip()
    text = await last_nonempty_inner_text(
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
    if len(cleaned) < 40:
        return False

    question_norm = " ".join(question.split()).strip().lower()
    cleaned_norm = " ".join(cleaned.split()).strip().lower()
    if cleaned_norm == question_norm:
        return False

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


async def run(
    chatbots: list[str],
    question: str,
    reuse_tabs: bool,
    timeout_seconds: int,
    skip_summary: bool,
) -> int:
    ws = ensure_browser_ws()
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(ws)
        ctx = browser.contexts[0]

        pages = {}
        for bot in chatbots:
            page = await (find_or_open_page(ctx, bot) if reuse_tabs else open_new_page(ctx, bot))
            if page.is_closed():
                page = await open_new_page(ctx, bot)
            pages[bot] = page
            try:
                await page.bring_to_front()
                await page.wait_for_timeout(1000)
            except TargetClosedError:
                page = await open_new_page(ctx, bot)
                pages[bot] = page
                await page.bring_to_front()
                await page.wait_for_timeout(1000)

        async def ask_one(bot: str) -> tuple[str, str]:
            await pages[bot].bring_to_front()
            if bot == "gemini":
                coro = ask_gemini(pages[bot], question)
            elif bot == "chatgpt":
                coro = ask_chatgpt(pages[bot], question)
            elif bot == "grok":
                coro = ask_grok(pages[bot], question)
            else:
                raise RuntimeError(f"Unsupported chatbot: {bot}")

            try:
                return bot, await asyncio.wait_for(coro, timeout=timeout_seconds)
            except asyncio.TimeoutError:
                return (
                    bot,
                    f"[Timed out after {timeout_seconds}s waiting for {bot} response]",
                )

        pairs = await asyncio.gather(*(ask_one(bot) for bot in chatbots))
        results = dict(pairs)

        for bot in chatbots:
            print(f"\n=== {bot.upper()} FULL RESPONSE ===")
            print(results[bot])

        should_summarize = not skip_summary and len(chatbots) > 1
        if should_summarize:
            gemini_page = pages.get("gemini")
            if gemini_page is None or gemini_page.is_closed():
                gemini_page = await (
                    find_or_open_page(ctx, "gemini") if reuse_tabs else open_new_page(ctx, "gemini")
                )
                pages["gemini"] = gemini_page

            summary_prompt = build_gemini_summary_prompt(question, chatbots, results)
            try:
                summary = await asyncio.wait_for(
                    ask_gemini(gemini_page, summary_prompt), timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                summary = f"[Timed out after {timeout_seconds}s waiting for gemini summary]"

            print("\n=== GEMINI SUMMARY ===")
            print(summary)

        await browser.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--chatbots",
        default=",".join(DEFAULT_CHATBOTS),
        help="Comma-separated list of chatbots: gemini, chatgpt, grok (default: gemini,chatgpt)",
    )
    parser.add_argument(
        "--reuse-tabs",
        action="store_true",
        help="Reuse an existing tab for a chatbot if one is already open",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=120,
        help="Maximum seconds to wait for each chatbot response (default: 120)",
    )
    parser.add_argument(
        "--skip-summary",
        action="store_true",
        help="Skip the final Gemini summary/comparison step",
    )
    parser.add_argument("--question", required=True, help="Question to send to each chatbot")
    args = parser.parse_args(argv)

    chatbots = parse_chatbots(args.chatbots)
    if args.timeout_seconds <= 0:
        raise SystemExit("--timeout-seconds must be greater than 0")
    return asyncio.run(
        run(
            chatbots,
            args.question,
            args.reuse_tabs,
            args.timeout_seconds,
            args.skip_summary,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
