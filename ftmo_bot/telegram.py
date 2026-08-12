from __future__ import annotations

import requests

from ftmo_bot.formatting import split_telegram_message


class TelegramError(RuntimeError):
    pass


class TelegramClient:
    def __init__(self, token: str, chat_id: str, timeout_seconds: int = 20) -> None:
        self.endpoint = f"https://api.telegram.org/bot{token}/sendMessage"
        self.chat_id = chat_id
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()

    def send(self, text: str) -> None:
        for chunk in split_telegram_message(text):
            try:
                response = self.session.post(
                    self.endpoint,
                    json={"chat_id": self.chat_id, "text": chunk, "disable_web_page_preview": True},
                    timeout=self.timeout_seconds,
                )
            except requests.RequestException as exc:
                raise TelegramError("Telegram network request failed") from exc
            if response.status_code >= 400:
                try:
                    description = response.json().get("description", "unknown error")
                except ValueError:
                    description = "unknown error"
                raise TelegramError(f"Telegram HTTP {response.status_code}: {description}")
