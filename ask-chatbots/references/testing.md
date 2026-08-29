# Testing ask-chatbots

## Output mode matrix

Each mode has different stdout expectations. Test all of them:

| Mode | Flags | Temp file? | Stdout has path? | Stdout has content? |
|---|---|---|---|---|
| Default | *(none)* | Yes (.txt) | Yes | Yes |
| `--stdout` | `--stdout` | No | No | Yes |
| `--wiki` | `--wiki` | Yes (.txt) | Yes | No (one-line path only) |
| `--include-responses` | `--include-responses` | Yes | Yes | Yes + per-bot sections |

Edge cases:
- **Single-bot default**: always prints the response (no summary for one bot)
- **`--skip-summary` without `--include-responses`**: auto-prints individual responses (otherwise empty output)
- **`--skip-summary --include-responses`**: prints individual responses, no summary
- **`--wiki` single-bot**: temp file contains `=== {BOT} FULL RESPONSE ===` section; agent extracts it for wiki

## Mocking the chatbot functions

The `ASKERS` dict is defined at module level and captures references to the real
`ask_gemini`, `ask_chatgpt`, etc. at import time. Standard `@mock.patch.object`
on `ask_chatbots.ask_gemini` patching the module attribute does NOT reach into
the dict — the dict still holds the original reference. Patch the dict entries
directly.

The synthesis step inside `run()` also goes through `ASKERS[judge]` — but the
judge is chosen by `pick_summarizer()`, which by default returns the first bot
NOT in the queried set (e.g. queried `gemini,chatgpt` → judge is `claude`). A
multi-bot test that doesn't use `--skip-summary` must therefore ALSO patch the
judge's `ASKERS` entry (or pin the judge with `--summarizer` to a bot it
already mocks):

```python
# Initial queries AND the synthesis step both resolve through ASKERS:
ask_chatbots.ASKERS["gemini"] = fg
ask_chatbots.ASKERS["chatgpt"] = fc
ask_chatbots.ASKERS["claude"] = fj   # default judge for the gemini,chatgpt set
```

`pick_summarizer(chatbots, override)` and `build_synthesis_prompt(...)` are pure
functions — test judge selection and prompt content (COVERAGE / CONTRADICTIONS /
SOURCES requirements, the self-debias paragraph when the judge is a respondent)
without any browser mocking.

Restore in `tearDown`:

```python
def setUp(self):
    self._saved_askers = {k: ask_chatbots.ASKERS[k] for k in ask_chatbots.ASKERS}
    self._saved_fns = (ask_chatbots.ask_gemini, ask_chatbots.ask_chatgpt)
    ask_chatbots.ASKERS["gemini"] = ask_chatbots.ask_gemini = fg
    ask_chatbots.ASKERS["chatgpt"] = ask_chatbots.ask_chatgpt = fc

def tearDown(self):
    ask_chatbots.ASKERS.clear()
    ask_chatbots.ASKERS.update(self._saved_askers)
    ask_chatbots.ask_gemini, ask_chatbots.ask_chatgpt = self._saved_fns
```

## Mocking the page object

The Playwright page is a `MagicMock` (not `AsyncMock`), since `page.locator()` is
sync. Only async methods like `goto()` and `wait_for_timeout()` need `AsyncMock`:

```python
p = mock.MagicMock()
p.goto = mock.AsyncMock()
p.wait_for_timeout = mock.AsyncMock()
# .locator() returns a MagicMock via default auto-creation — correct for sync
```

Using `AsyncMock` for the page causes `'coroutine' object has no attribute 'first'`
when the real `ask_gemini` calls `page.locator(...).first`.

## Fake Chrome context

The `AsyncLoggedInChrome` mock must support the async context manager protocol.
The `__aenter__` should construct a minimal context + page tree:

```python
class FakeChrome:
    def __init__(self, **kw): pass
    async def __aenter__(self):
        ctx = mock.MagicMock()
        page = mock.MagicMock()
        page.goto = mock.AsyncMock()
        page.wait_for_timeout = mock.AsyncMock()
        ctx.new_page = mock.AsyncMock(return_value=page)
        self.browser = mock.MagicMock(contexts=[ctx])
        return self
    async def __aexit__(self, *a): pass
    def detach(self): pass
```

Decorate test class with:
```python
@mock.patch.object(ask_chatbots.logged_in_chrome, "AsyncLoggedInChrome", FakeChrome)
```

## Temp file cleanup

All tests that use the default or `--wiki` modes create temp files. Always
`os.unlink(path)` in the test body (or in `tearDown` if tracking paths).
Never leave temp files behind — they litter `/var/folders/.../T/`.
