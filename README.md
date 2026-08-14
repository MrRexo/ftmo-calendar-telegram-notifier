# FTMO Calendar Telegram Notifier

**English** | [Polski](README.pl.md)

A lightweight Python service that fetches the FTMO economic calendar and sends Telegram notifications with:

- a daily P0/P1/P2 event summary,
- a special warning on every 13th day of the month: `Today is the 13th! Do not trade anything 🙂`,
- reminders 15 and 5 minutes before events restricted by FTMO,
- the released `actual` value and the restriction end time after publication,
- Telegram messages in Polish or English.

By default, the bot includes events from Monday to Friday between 07:00 and 20:00
in the configured `TIMEZONE`, inclusive. It sends no summary, reminder, release update,
or 13th-day warning on weekends.

## Notification preview

An example daily summary in Telegram:

<p align="center">
  <img src="docs/telegram-preview.png" alt="Example FTMO Telegram notification with priorities and restriction windows" width="484">
</p>

The service uses the public JSON endpoint consumed by the FTMO calendar page. It does
not require Selenium, Playwright, or a running browser.

## Priorities

| Priority | Meaning |
| --- | --- |
| P0 | event with `restriction=true` |
| P1 | high impact |
| P2 | medium impact |
| P3 | low impact |
| P4 | holiday or unknown type |

The P0 restriction applies to FTMO Account Standard. According to FTMO rules, it does
not apply to the Evaluation Process or FTMO Account Swing. Always confirm the current
rules for your account directly with FTMO.

## Requirements

- Linux with systemd, such as Debian 12 or Ubuntu 22.04/24.04,
- Python 3.11 or newer,
- `git`, `python3-venv`, and HTTPS access to FTMO and Telegram,
- a Telegram bot created through `@BotFather`,
- a Telegram chat ID.

## 1. Prepare the Telegram bot

1. Open a conversation with `@BotFather` in Telegram.
2. Run `/newbot` and save the token.
3. Send any message to your new bot.
4. Retrieve the `chat_id`, for example by opening:

   ```text
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```

Treat the token like a password. Do not commit it or expose it in shared shell history.

## 2. Install on Linux

Run the following commands from an account with `sudo` access:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv

sudo useradd --system \
  --home-dir /var/lib/ftmo-calendar-notifier \
  --create-home \
  --shell /usr/sbin/nologin \
  ftmo-notifier

sudo git clone https://github.com/MrRexo/ftmo-calendar-telegram-notifier.git \
  /opt/ftmo-calendar-telegram-notifier

sudo python3 -m venv /opt/ftmo-calendar-telegram-notifier/.venv
sudo /opt/ftmo-calendar-telegram-notifier/.venv/bin/pip install \
  -r /opt/ftmo-calendar-telegram-notifier/requirements.txt

sudo install -d -m 0750 -o ftmo-notifier -g ftmo-notifier \
  /var/lib/ftmo-calendar-notifier
```

## 3. Configure

Create a configuration file outside the repository:

```bash
sudo install -m 0600 -o root -g root /dev/null \
  /etc/ftmo-calendar-notifier.env
sudo nano /etc/ftmo-calendar-notifier.env
```

Minimal configuration:

```dotenv
TELEGRAM_BOT_TOKEN=paste_the_BotFather_token
TELEGRAM_CHAT_ID=paste_the_chat_id
TIMEZONE=Europe/Warsaw
MESSAGE_LANGUAGE=en
SUMMARY_TIME=07:00
EVENT_TIME_FROM=07:00
EVENT_TIME_TO=20:00
EXCLUDE_WEEKENDS=true
POLL_SECONDS=300
REMINDER_MINUTES=15,5
SUMMARY_IMPACTS=high,medium
SEND_SUMMARY_ON_START=true
SUMMARY_GRACE_MINUTES=180
STATE_FILE=/var/lib/ftmo-calendar-notifier/state.json
SNAPSHOT_FILE=/var/lib/ftmo-calendar-notifier/latest.json
REQUEST_TIMEOUT_SECONDS=20
```

`MESSAGE_LANGUAGE` selects the Telegram message language. Supported values are `en`
and `pl`. Economic event names remain exactly as returned by FTMO.

`SEND_SUMMARY_ON_START=true` sends one summary immediately after the first startup.
Deduplication in `state.json` prevents the same summary from being sent again after a
restart.

`EVENT_TIME_FROM` and `EVENT_TIME_TO` define the allowed event times in the local
`TIMEZONE`. `EXCLUDE_WEEKENDS=true` disables Saturdays and Sundays.

## 4. Run as a systemd service

```bash
sudo install -m 0644 \
  /opt/ftmo-calendar-telegram-notifier/deploy/ftmo-calendar-bot.service \
  /etc/systemd/system/ftmo-calendar-bot.service

sudo systemctl daemon-reload
sudo systemctl enable --now ftmo-calendar-bot.service
```

Check the service:

```bash
systemctl status ftmo-calendar-bot.service --no-pager
sudo journalctl -u ftmo-calendar-bot.service -n 50 --no-pager
```

After a successful startup, the log will contain `Daily summary sent`, and the first
summary will appear in the configured Telegram chat.

## Update

```bash
sudo git -C /opt/ftmo-calendar-telegram-notifier pull --ff-only
sudo /opt/ftmo-calendar-telegram-notifier/.venv/bin/pip install \
  -r /opt/ftmo-calendar-telegram-notifier/requirements.txt
sudo systemctl restart ftmo-calendar-bot.service
sudo systemctl status ftmo-calendar-bot.service --no-pager
```

## Tests

Tests never use a real Telegram token:

```bash
cd /opt/ftmo-calendar-telegram-notifier
.venv/bin/python -m unittest discover -s tests -v
```

## Security and data

- real tokens and chat IDs are not part of the repository,
- `.env`, `env.txt`, API snapshots, notification state, and Python cache files are ignored by Git,
- the systemd unit runs as a dedicated user without login access,
- `NoNewPrivileges`, `ProtectSystem`, `ProtectHome`, and `PrivateTmp` restrict the service,
- `/etc/ftmo-calendar-notifier.env` should have `0600` permissions.

## Disclaimer

This project is not affiliated with FTMO or Telegram. The calendar endpoint is not a
documented public integration API and may change. Notifications are an operational aid,
not a guarantee of compliance. Check the current FTMO calendar and rules before trading.
