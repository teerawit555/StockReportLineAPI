from __future__ import annotations

import os
from dataclasses import dataclass

from utils.logger import get_logger


logger = get_logger(__name__)


@dataclass(slots=True)
class LineService:
    channel_access_token: str
    user_id: str

    API_URL = "https://api.line.me/v2/bot/message/push"
    MAX_TEXT_LENGTH = 4500

    @classmethod
    def from_env(cls) -> "LineService":
        token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
        user_id = os.getenv("LINE_USER_ID", "").strip()
        if not token:
            raise ValueError("LINE_CHANNEL_ACCESS_TOKEN is required.")
        if not user_id:
            raise ValueError("LINE_USER_ID is required.")
        return cls(channel_access_token=token, user_id=user_id)

    def push_message(self, message: str) -> bool:
        chunks = self._split_message(message)
        success = True
        for index, chunk in enumerate(chunks, start=1):
            logger.info("Sending LINE message chunk %s/%s.", index, len(chunks))
            success = self._push_chunk(chunk) and success
        return success

    def _push_chunk(self, text: str) -> bool:
        try:
            import requests
        except ImportError:
            logger.error("requests is not installed. Run: pip install -r requirements.txt")
            return False

        headers = {
            "Authorization": f"Bearer {self.channel_access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "to": self.user_id,
            "messages": [
                {
                    "type": "text",
                    "text": text,
                }
            ],
        }

        try:
            response = requests.post(
                self.API_URL,
                headers=headers,
                json=payload,
                timeout=20,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            response_text = getattr(getattr(exc, "response", None), "text", "")
            if response_text:
                logger.error("LINE API response: %s", response_text[:500])
            logger.exception("Failed to send LINE message: %s", exc)
            return False
        return True

    @classmethod
    def _split_message(cls, message: str) -> list[str]:
        if len(message) <= cls.MAX_TEXT_LENGTH:
            return [message]

        chunks: list[str] = []
        current: list[str] = []
        current_length = 0

        for line in message.splitlines():
            if len(line) > cls.MAX_TEXT_LENGTH:
                for piece in cls._split_long_line(line):
                    if current:
                        chunks.append("\n".join(current))
                        current = []
                        current_length = 0
                    chunks.append(piece)
                continue

            line_length = len(line) + 1
            if current and current_length + line_length > cls.MAX_TEXT_LENGTH:
                chunks.append("\n".join(current))
                current = []
                current_length = 0
            current.append(line)
            current_length += line_length

        if current:
            chunks.append("\n".join(current))
        return chunks

    @classmethod
    def _split_long_line(cls, line: str) -> list[str]:
        return [
            line[index : index + cls.MAX_TEXT_LENGTH]
            for index in range(0, len(line), cls.MAX_TEXT_LENGTH)
        ]
