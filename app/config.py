import sys
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

__all__ = ["MazeConfig", "load_config"]

Coord = tuple[int, int]


class MazeConfig(BaseModel):
    """A validated maze configuration."""

    model_config = {
        "extra": "ignore",
        "frozen": True,
        "populate_by_name": True,
        "str_strip_whitespace": True,
    }

    width: int = Field(alias="WIDTH", ge=2)
    height: int = Field(alias="HEIGHT", ge=2)
    entry: Coord = Field(alias="ENTRY")
    exit: Coord = Field(alias="EXIT")
    output_file: Path = Field(alias="OUTPUT_FILE")
    perfect: bool = Field(alias="PERFECT")
    seed: int | None = Field(alias="SEED", default=None)
    algorithm: Literal["kruskal", "dfs"] = Field(
        alias="ALGORITHM", default="kruskal"
    )

    @field_validator("entry", "exit", mode="before")
    @classmethod
    def _parse_coord(cls, value: Any) -> Any:
        """Turn an ``"x,y"`` string into an ``(x, y)`` tuple."""
        if not isinstance(value, str):
            return value
        parts = value.split(",")
        if len(parts) != 2:
            raise ValueError("expected two comma-separated integers, e.g. 3,4")
        return (int(parts[0]), int(parts[1]))

    @field_validator("algorithm", mode="before")
    @classmethod
    def _normalise_algorithm(cls, value: Any) -> Any:
        """Accept ``DFS``, ``Dfs`` and friends."""
        return value.lower() if isinstance(value, str) else value

    @model_validator(mode="after")
    def _check_cells(self) -> "MazeConfig":
        """Entry and exit must be distinct cells inside the grid."""
        for name, (x, y) in (("ENTRY", self.entry), ("EXIT", self.exit)):
            if not (0 <= x < self.width and 0 <= y < self.height):
                raise ValueError(
                    f"{name}={x},{y} is outside the "
                    f"{self.width}x{self.height} maze"
                )
        if self.entry == self.exit:
            raise ValueError("ENTRY and EXIT must be different cells")
        return self


_KNOWN_KEYS = frozenset(
    field.alias or name for name, field in MazeConfig.model_fields.items()
)


def load_config(path: str | Path) -> MazeConfig:
    """Read and validate the configuration file at *path*."""
    path = Path(path)
    pairs: dict[str, str] = {}
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            key, separator, value = line.split("#", 1)[0].partition("=")
            key, value = key.strip().upper(), value.strip()
            if not separator:
                if key:
                    raise ValueError(f"{path}:{number}: expected KEY=VALUE")
                continue
            if not key:
                raise ValueError(f"{path}:{number}: missing key before '='")
            if not value:
                raise ValueError(f"{path}:{number}: {key} has no value")
            if key in pairs:
                raise ValueError(f"{path}:{number}: duplicate key {key}")
            if key not in _KNOWN_KEYS:
                print(
                    f"warning: {path}:{number}: ignoring unknown key {key}",
                    file=sys.stderr,
                )
                continue
            pairs[key] = value
    return MazeConfig.model_validate(pairs)
