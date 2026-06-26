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

# 2. Create a full backup BEFORE any changes
backup-openclaw
# Note the backup filename printed (~/backups/openclaw-YYYYMMDD-HHMM.tar.gz) — you'll need it if rollback is required

# 3. Stop the gateway cleanly
launchctl bootout gui/$(id -u)/ai.openclaw.gateway

# 4. Wipe staged plugin runtime deps (different versions use different layouts)
rm -rf ~/.openclaw/plugin-runtime-deps

# 5. Install via brew's npm explicitly (avoid PATH ambiguity)
/opt/homebrew/bin/npm -g install openclaw@<version>

# 6. Verify the install actually replaced the binary
openclaw --version

# 7. Run doctor to rewrite launchd plist + reinstall bundled deps
openclaw doctor --fix

# 8. Wait for the install to fully settle — DO NOT kickstart again
#    On versions with plugin-runtime-deps staging, first boot pegs CPU
#    for 1-2 minutes while installing into ~/.openclaw/plugin-runtime-deps/.
#    Interrupting forces it to start over.
sleep 30
ps aux | grep openclaw-gateway | grep -v grep   # cpu should drop toward 0%

# 9. Smoke test
launchctl print gui/$(id -u)/ai.openclaw.gateway | grep -E 'state|last exit'
tail ~/.openclaw/logs/gateway.log               # look for "[gateway] ready"
```

If any step from 5 onward fails or the smoke test shows problems, proceed to **Restore from backup** below.

## Restore from backup

If the update fails or introduces regressions, restore from the backup created in step 2. This recovers config, sessions, agent state, and plugin data to the pre-update snapshot.

```bash
# 1. Stop the gateway
launchctl bootout gui/$(id -u)/ai.openclaw.gateway

# 2. Roll back the npm package to the previous version
/opt/homebrew/bin/npm -g install openclaw@<previous-version>

# 3. Restore config/state from the backup tarball
openclaw backup restore ~/backups/openclaw-YYYYMMDD-HHMM.tar.gz

# 4. Rewrite launchd plist for the restored version
openclaw doctor --fix

# 5. Wait for settle
sleep 30

# 6. Verify
openclaw --version
launchctl print gui/$(id -u)/ai.openclaw.gateway | grep -E 'state|last exit'
tail ~/.openclaw/logs/gateway.log
```

If `openclaw backup restore` is not available on the installed version, manually extract the tarball:

```bash
tar -xzf ~/backups/openclaw-YYYYMMDD-HHMM.tar.gz -C ~/.openclaw --strip-components=1
```

After restoring, diff the config to confirm no drift was introduced (see **Post-update: doctor config drift** below).

## Rollback procedure (version-only, no backup)

Identical to update, just install the older version in step 5. Stable releases of openclaw use date-based versions like `2026.4.23`, `2026.4.22`. List published versions:

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

3. **Provider ID normalization (`openai-codex` → `openai`)** — 2026.6.x renamed the `openai-codex` provider to `openai` as part of its "reliable model routing" overhaul. In a diff this looks like account keys changing from `openai-codex:<email>` to `openai:<email>` and `provider: "openai-codex"` → `provider: "openai"`. **This is legitimate, not a regression.** The OAuth token migrates intact under the new key. Confirm with `openclaw models` — look for `openai via codex ... status=usable` and the OAuth account still listed. If a token shows expired after the rename, the fix is `openclaw models auth login --provider openai` (note: `--provider openai-codex` from pitfall #3 above is the *old* name and will fail on 2026.6.x — use `openai`).

4. **Whole model entries pruned for discontinued models** — Doctor drops model entries for models the new version no longer ships (e.g., `anthropic/claude-opus-4-5` vanished on update to 2026.6.10, where available opus models became 4-6/4-7/4-8). This is scarier than the agentRuntime.id key-strip in pitfall #4 of "Watch out for" because the entire model block disappears. Verify against `openclaw models` output — if the model isn't in `Configured models` or `Aliases` anymore, the removal is correct; don't restore the stale entry from backup. *Do* restore the entry if the model is still listed as available — that's a doctor bug, not a migration.

### Config diff procedure

The `backup-openclaw` step (step 2) already saved a full snapshot. Extract just the config from it for diffing:

```bash
# Extract the config from the backup tarball for comparison
tar -xzf ~/backups/openclaw-YYYYMMDD-HHMM.tar.gz --include='*/openclaw.json' -O > /tmp/openclaw-pre-update.json

# After doctor, diff against the pre-update config
diff <(jq --sort-keys . /tmp/openclaw-pre-update.json) \
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
| `conflicting plugin install metadata for: codex, discord` in `openclaw models` output | Shared SQLite plugin-install index has stale/double entries left by the version change | Soft warning, not yet a breakage. If Discord goes silent, run `openclaw doctor --fix` again (it tries to reconcile the index); if it persists and a specific channel is dead, apply the stale-session fix below. Don't manually edit the SQLite. |

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
# Process name is NOT "openclaw-gateway" — it's node running dist/index.js.
# pgrep the node command instead of grepping ps for a binary that doesn't exist:
pgrep -fl 'openclaw/dist/index.js gateway' | head
ps -p "$(pgrep -f 'openclaw/dist/index.js gateway')" -o pid,%cpu,etime 2>/dev/null   # %cpu near 0 when idle
# Confirm it's actually listening (authoritative proof the gateway is up):
lsof -nP -iTCP:18789 -sTCP:LISTEN 2>/dev/null | head
# Portal state:
launchctl print gui/$(id -u)/ai.openclaw.gateway | grep -E '\tstate|last exit'

# Fastest provider/token health check after a version bump — confirms OAuth
# tokens survived migration and lists which provider IDs are now valid:
openclaw models
```

**Caveat on `ps aux | grep openclaw-gateway`** — earlier revisions of this skill used that form. On 2026.6.x the gateway process shows as `node .../openclaw/dist/index.js gateway --port 18789`, so grepping for `openclaw-gateway` returns nothing even when the gateway is fine. This is not a broken gateway — it's a stale pattern. Use the `pgrep -f 'openclaw/dist/index.js gateway'` form above.

**Caveat on `tail ~/.openclaw/logs/gateway.log`** — on 2026.6.x the gateway no longer appends to `gateway.log`/`gateway.err.log` (those files can sit stale for weeks while the gateway runs fine). Active health output goes to `config-health.json` and `config-audit.jsonl` in the same logs dir (fresh mtime = recent gateway doctor pass). Treat a stale `gateway.log` as a possible logging-path change, not a crashed gateway — confirm with `lsof` + `launchctl print` + `openclaw models` instead of relying on the log file.

**Provider/token survival after the 2026.6.x `openai-codex` → `openai` rename** — run `openclaw models` and find the line `openai via codex uses openai ... status=usable`; the OAuth account (e.g. `openai:<email>`) should still appear under `Providers w/ OAuth/tokens` with usage remaining. This single command replaced grepping the stale err-log for token status this session.

For end-to-end confirmation, send "who are you?" through the user's TUI and watch:
- `chat.history` latency in the log (should be <2s on 2026.4.23, <1s ideal)
- gateway CPU stays near 0% between turns

For Discord verification:
- Send a test message in each bound Discord channel
- Confirm the bot responds (not just "typing...")
- If any channel fails, check stale sessions and config drift (see "Post-update" sections above)
- The user may need to restart their Discord app after the gateway restarts
