---
name: recent-usps-mails
description: Show a summary of USPS Informed Delivery mail from the last 10 days, split into important and other sections. Optionally send the summary (with images) to Discord. Use when the user asks about recent mail, USPS deliveries, what mail came, or wants to check Informed Delivery.
---

# recent-usps-mails

Show a 10-day rolling summary of USPS Informed Delivery mail from the local cache at `~/.cache/usps-informed-delivery/`. The cache is populated by the twice-daily cron job that fetches and classifies new emails.

## Steps

1. Run the summary command:

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/ml/bin/python /Users/jianfuchen/projects/email/src/usps_informed_delivery.py --summary
```

This fetches any new unprocessed emails first (so the cache is fresh), then renders the full 10-day summary with two sections:
- **IMPORTANT MAIL** (count) — government, banks, financial, insurance, utilities, healthcare, legal, tax, DMV, courts, IRS
- **OTHER MAIL** (count) — marketing, promotions, flyers, advertisements

Each piece shows: date, sender name, recipient name, brief description, and the scanned image via `MEDIA:` path.

Mails within each section are ordered by time descending (newest first).

2. Present the output to the user.

## Posting to Discord

If the user asks to send/post to Discord, use `openclaw message send` to post each section separately (so each image attaches to its section). The default Discord channel is `1500320074270249061`.

For each section (IMPORTANT MAIL, then OTHER MAIL), send a message with the text and attach the image:

```bash
openclaw message send \
  --channel discord \
  --target 1500320074270249061 \
  -m 'MESSAGE TEXT HERE' \
  --media /path/to/image.jpg \
  --json
```

Notes:
- `openclaw message send` only supports one `--media` attachment per call.
- If a section has multiple mail pieces with images, send one message per piece, or send the text in one message and images in follow-up messages.
- If the user specifies a different channel, use that channel ID instead.
- The image paths are in `~/.cache/usps-informed-delivery/images/`.
