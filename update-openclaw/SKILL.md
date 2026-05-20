---
name: update-openclaw
description: Update or roll back the openclaw npm package safely on macOS. Use when the user asks to update openclaw, upgrade openclaw, install a new openclaw version, downgrade openclaw, or roll back openclaw to a specific version.
---

# update-openclaw

`openclaw` on this machine is installed as an npm-global package under brew's node@22, **not** as a homebrew formula. `which openclaw` resolves to `/opt/homebrew/bin/openclaw`, which symlinks into `/opt/homebrew/lib/node_modules/openclaw/`.

The launchd-managed gateway runs from a path baked into `~/Library/LaunchAgents/ai.openclaw.gateway.plist`. After any version change, the plist must be re-pointed at the new install — that's what `openclaw doctor --fix` does.

## Default stance: don't update

The user previously hit serious regressions in `2026.4.26` (chat.history latency, plugin-runtime-deps churn, OAuth refresh race) and rolled back to `2026.4.23`. Before suggesting any update, check the upstream changelog or releases for fixes referencing the user's known issues:

- `plugin-runtime-deps` staged install loops
- `acpx` / `pi-mono` runtime initialization cost
- OAuth `refresh_token_reused` cascades

If those keywords don't appear as fixes in newer releases, recommend staying on the current version.

## Update procedure

Always use this sequence. Don't use `openclaw update` (the self-updater) — it can produce mixed old/new installs that leave the launchd plist pointing at stale code.

```bash
# 1. Note current version (for rollback)
openclaw --version

# 2. Stop the gateway cleanly
launchctl bootout gui/$(id -u)/ai.openclaw.gateway

# 3. Wipe staged plugin runtime deps (different versions use different layouts)
rm -rf ~/.openclaw/plugin-runtime-deps

# 4. Install via brew's npm explicitly (avoid PATH ambiguity)
/opt/homebrew/bin/npm -g install openclaw@<version>

# 5. Verify the install actually replaced the binary
openclaw --version

# 6. Run doctor to rewrite launchd plist + reinstall bundled deps
openclaw doctor --fix

# 7. Wait for the install to fully settle — DO NOT kickstart again
#    On versions with plugin-runtime-deps staging, first boot pegs CPU
#    for 1-2 minutes while installing into ~/.openclaw/plugin-runtime-deps/.
#    Interrupting forces it to start over.
sleep 30
ps aux | grep openclaw-gateway | grep -v grep   # cpu should drop toward 0%

# 8. Smoke test
launchctl print gui/$(id -u)/ai.openclaw.gateway | grep -E 'state|last exit'
tail ~/.openclaw/logs/gateway.log               # look for "[gateway] ready"
```

## Rollback procedure

Identical to update, just install the older version in step 4. Stable releases of openclaw use date-based versions like `2026.4.23`, `2026.4.22`. List published versions:

```bash
npm view openclaw versions --json | tail -30
```

Recovery target if the user's been on `2026.4.26+` and it's slow: `2026.4.23` (last version without `memory-core` plugin and without `plugin-runtime-deps` staging architecture).

## Watch out for

1. **Multiple node-manager openclaw installs.** If the user has nvm/asdf/fnm/volta active, they may have a second openclaw that shadows brew's. Always verify after install:
   ```bash
   which openclaw                                          # should be /opt/homebrew/bin/openclaw
   /opt/homebrew/bin/openclaw --version                    # the brew install
   /Users/$USER/.nvm/versions/node/*/bin/openclaw --version 2>&1   # any nvm leftover
   ```
   If a duplicate exists, remove it through its own npm:
   ```bash
   /Users/$USER/.nvm/versions/node/<version>/bin/npm -g uninstall openclaw
   ```

2. **Bundled plugin deps prompt.** After `openclaw doctor`, you may get:
   ```
   Bundled plugin runtime deps are missing. Install missing bundled plugin runtime deps now?
   ```
   - If `openclaw --version` matches what you expect: **say Yes**, that's the new version's deps installing.
   - If the listed dep versions look wrong (e.g., `acpx@0.6.1` when on `2026.4.23` which uses `acpx@0.5.3`): **say No** — you ran doctor through a shadowed install. Verify `which openclaw` from a fresh shell first.

3. **OAuth tokens may need re-auth.** Doctor can ask to refresh expiring OAuth tokens. Saying Yes is safe — failed refreshes don't corrupt stored credentials. If a provider stays expired afterward (e.g., openai-codex with `refresh_token_reused`), the user needs:
   ```bash
   openclaw models auth login --provider openai-codex
   ```

4. **`agentRuntime.id` config key.** Newer versions support `agents.defaults.agentRuntime.id` to select runtimes (`pi`, `claude-cli`, `codex`). Older versions don't and `doctor --fix` strips the key during config migration. This is fine — pi remains the default embedded runtime either way.

5. **Don't restart the gateway repeatedly during/after install.** On versions with plugin-runtime-deps staging (2026.4.26+), each `launchctl kickstart -k` may force the staged-deps install to start over from scratch (1-2 min CPU spin per restart). Set the change, then wait — let hot-reload pick it up if the change is hot-reloadable, or accept one clean restart.

## Post-update: doctor config drift

`openclaw doctor --fix` rewrites `openclaw.json` and can silently break Discord channel routing. After every doctor run, diff the config against a pre-update backup and revert harmful changes:

### Known doctor mutations to watch for

1. **`messages.groupChat.visibleReplies: "message_tool"`** — Doctor adds this on 2026.5.x+. It requires agents to call a "message tool" to send replies in guild channels. The `claude-cli` and `pi` runtimes don't support this tool, so agent responses get generated but **silently never delivered** to Discord. Fix: delete the `messages.groupChat` key entirely, or set `visibleReplies` to `"automatic"`.

2. **`plugins.allow` pruning** — Doctor removes entries for plugins that aren't installed (e.g., `acpx`). This is usually fine but verify the `anthropic` plugin is still in the list if using `claude-cli` runtime.

### Config diff procedure

```bash
# Before updating, backup the config
cp ~/.openclaw/openclaw.json ~/backups/openclaw-$(date +%Y%m%d-%H%M).json

# After doctor, diff against backup
diff <(jq --sort-keys . ~/backups/openclaw-YYYYMMDD-HHMM.json) \
     <(jq --sort-keys . ~/.openclaw/openclaw.json)

# Revert a specific key (example: remove groupChat)
jq 'del(.messages.groupChat)' ~/.openclaw/openclaw.json > /tmp/fix.json \
  && mv /tmp/fix.json ~/.openclaw/openclaw.json
```

## Post-update: Discord channel debugging

If Discord shows "typing..." but no reply appears, or a specific channel stops responding while threads/other channels work:

### Symptom → Cause mapping

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| All channels: typing then silence | `visibleReplies: "message_tool"` | Delete `messages.groupChat` key |
| One channel stuck, threads work | Stale session (missing file or provider mismatch) | Delete session entry (see below) |
| All channels stuck after model ID change | All sessions bound to old provider | Clear all Discord sessions (see below) |
| All channels dead after update | Discord app caching stale bot state | Restart the Discord app |
| Agent processes but no Discord send | Config or delivery issue | Check `visibleReplies` and session state |

### Stale session fix

Discord channel sessions are stored in `~/.openclaw/agents/<agent>/sessions/sessions.json`. Sessions become stale when:
- The referenced `.jsonl` session file doesn't exist on disk
- The `modelProvider` in the session no longer matches the agent's configured model (e.g., after changing from `claude-cli/` to `anthropic/` model IDs)

The gateway silently fails to resume stale sessions. New threads work because they get fresh session keys.

```bash
# 1. Find the stuck session
jq 'to_entries[] | select(.key | contains("discord:channel:<CHANNEL_ID>")) | {key, sessionFile: .value.sessionFile, status: .value.status}' \
  ~/.openclaw/agents/<agent>/sessions/sessions.json

# 2. Check if the session file exists
ls -la <sessionFile path>

# 3. If missing, delete the stale session entry
jq 'del(."agent:<agent>:discord:channel:<CHANNEL_ID>")' \
  ~/.openclaw/agents/<agent>/sessions/sessions.json > /tmp/fix.json \
  && cp ~/.openclaw/agents/<agent>/sessions/sessions.json ~/.openclaw/agents/<agent>/sessions/sessions.json.bak \
  && mv /tmp/fix.json ~/.openclaw/agents/<agent>/sessions/sessions.json

# 4. Restart gateway
launchctl bootout gui/$(id -u)/ai.openclaw.gateway
launchctl load ~/Library/LaunchAgents/ai.openclaw.gateway.plist

# Bulk: clear ALL Discord sessions for ALL agents (e.g., after model provider change)
for agent in assistant stock-picker main; do
  f=~/.openclaw/agents/$agent/sessions/sessions.json
  if [ -f "$f" ]; then
    cp "$f" "$f.bak"
    jq '[to_entries[] | select(.key | contains("discord:channel") | not)] | from_entries' "$f" > /tmp/sess-fix.json
    mv /tmp/sess-fix.json "$f"
  fi
done
```

### Diagnostic log patterns

```bash
# Check if Discord messages are being dispatched to agents
grep 'agent.*discord.*processing' ~/.openclaw/logs/gateway.err.log | tail -5

# Look for agent model calls (should appear after Discord dispatch)
grep 'cli exec.*trigger=user' ~/.openclaw/logs/gateway.log | tail -5

# If dispatched but no cli exec → session resume failure or config issue
# If cli exec succeeds but no Discord reply → visibleReplies or delivery issue
```

## Verify the update worked

```bash
openclaw --version
ps aux | grep openclaw-gateway | grep -v grep | awk '{print "cpu="$3"%"}'    # 0.0% when idle
tail -1 ~/.openclaw/logs/gateway.log
```

For end-to-end confirmation, send "who are you?" through the user's TUI and watch:
- `chat.history` latency in the log (should be <2s on 2026.4.23, <1s ideal)
- gateway CPU stays near 0% between turns

For Discord verification:
- Send a test message in each bound Discord channel
- Confirm the bot responds (not just "typing...")
- If any channel fails, check stale sessions and config drift (see "Post-update" sections above)
- The user may need to restart their Discord app after the gateway restarts
