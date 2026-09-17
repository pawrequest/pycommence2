from pathlib import Path

import platformdirs
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
        toml_path = Path(platformdirs.user_config_path('pcommence2', 'pawrequest')).resolve() / 'config.toml'
        toml_path.touch(exist_ok=True)
        return cls.from_toml(toml_path)

    @classmethod
    def from_toml(cls, path: Path) -> 'PycommenceSettings':
        import tomllib

        with open(path, 'rb') as f:
            data = tomllib.load(f)
        return cls(**data)
