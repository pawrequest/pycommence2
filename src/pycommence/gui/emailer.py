from dataclasses import dataclass
from pathlib import Path


@dataclass
class Email:
    """Dataclass representing an email"""
    to_address: str
    subject: str
    body: str
    attachment_paths: list[Path] | None = None

    def __post_init__(self):
        if self.attachment_paths is None:
            self.attachment_paths = []

    def send(self, sender: 'EmailHandler') -> None:
        sender.create_open_email(self)
