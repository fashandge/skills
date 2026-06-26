# Testing ask-chatbots

## Mocking the chatbot functions

The `ASKERS` dict is defined at module level and captures references to the real
`ask_gemini`, `ask_chatgpt`, etc. at import time. Standard `@mock.patch.object`
on `ask_chatbots.ask_gemini` patching the module attribute does NOT reach into
the dict — the dict still holds the original reference.

To mock correctly, patch BOTH:

```python
# The ask_gemini function is called directly for the summary step:
ask_chatbots.ask_gemini = fg

# ASKERS dict must also be patched for the initial queries:
ask_chatbots.ASKERS["gemini"] = fg
```

Restore in `tearDown`:

```python
def tearDown(self):
    ask_chatbots.ASKERS["gemini"] = self._saved_askers["gemini"]
    ask_chatbots.ask_gemini = self._saved_ask_fns["ask_gemini"]
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
