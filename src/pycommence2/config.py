from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings

CategoryName = str


class Sort(BaseModel):
    field: str
    ascending: bool = True


class PycommenceSettings(BaseSettings):
    sorts: dict[CategoryName, list[Sort]] = {}

    @classmethod
    def default(cls):
        return cls()

    @classmethod
    def from_toml(cls, path: Path) -> 'PycommenceSettings':
        import tomllib

        with open(path, 'rb') as f:
            data = tomllib.load(f)
        return cls(**data) if data else cls()
