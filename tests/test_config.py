"""Config parsing and validation: the shapes a user can get wrong."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import load_config

VALID = """\
WIDTH=15
HEIGHT=15
ENTRY=0,0
EXIT=14,14
OUTPUT_FILE=maze_out.txt
PERFECT=TRUE
"""


def write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "config.txt"
    path.write_text(body, encoding="utf-8")
    return path


def test_valid_config_parses(tmp_path: Path) -> None:
    config = load_config(write(tmp_path, VALID))
    assert (config.width, config.height) == (15, 15)
    assert config.entry == (0, 0)
    assert config.exit == (14, 14)
    assert config.perfect is True
    assert config.seed is None
    assert config.algorithm == "kruskal"  # the documented default


def test_trailing_comment_is_stripped(tmp_path: Path) -> None:
    """The trap from the shipped config: ALGORITHM=dfs #kruskals.

    Parsed naively the value is "dfs #kruskals" and algorithm selection
    fails silently, which is the one outcome that must not happen.
    """
    config = load_config(write(tmp_path, VALID + "ALGORITHM=dfs #kruskals\n"))
    assert config.algorithm == "dfs"


def test_blank_lines_and_whole_line_comments_are_ignored(
    tmp_path: Path,
) -> None:
    body = "# a comment\n\n   \n" + VALID
    assert load_config(write(tmp_path, body)).width == 15


def test_whitespace_and_key_case_are_forgiven(tmp_path: Path) -> None:
    body = VALID.replace("WIDTH=15", "  width  =  15  ")
    assert load_config(write(tmp_path, body)).width == 15


@pytest.mark.parametrize(
    "value, expected",
    [("TRUE", True), ("true", True), ("True", True), ("1", True),
     ("FALSE", False), ("false", False), ("0", False)],
)
def test_perfect_accepts_the_usual_spellings(
    tmp_path: Path, value: str, expected: bool
) -> None:
    body = VALID.replace("PERFECT=TRUE", f"PERFECT={value}")
    assert load_config(write(tmp_path, body)).perfect is expected


def test_unknown_key_warns_but_does_not_crash(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = load_config(write(tmp_path, VALID + "NONSENSE=3\n"))
    assert config.width == 15
    assert "unknown key NONSENSE" in capsys.readouterr().err


def test_duplicate_key_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="duplicate key WIDTH"):
        load_config(write(tmp_path, VALID + "WIDTH=9\n"))


def test_line_without_a_separator_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="expected KEY=VALUE"):
        load_config(write(tmp_path, VALID + "GARBAGE\n"))


def test_missing_key_before_equals_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="missing key"):
        load_config(write(tmp_path, VALID + "=5\n"))


def test_empty_value_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="SEED has no value"):
        load_config(write(tmp_path, VALID + "SEED=\n"))


def test_missing_file_raises_oserror(tmp_path: Path) -> None:
    with pytest.raises(OSError):
        load_config(tmp_path / "nope.txt")


@pytest.mark.parametrize(
    "body",
    [
        VALID.replace("WIDTH=15", "WIDTH=0"),
        VALID.replace("WIDTH=15", "WIDTH=-4"),
        VALID.replace("WIDTH=15", "WIDTH=wide"),
        VALID.replace("HEIGHT=15", "HEIGHT=1"),
        VALID.replace("ENTRY=0,0", "ENTRY=99,0"),
        VALID.replace("ENTRY=0,0", "ENTRY=0,-1"),
        VALID.replace("ENTRY=0,0", "ENTRY=14,14"),   # same cell as EXIT
        VALID.replace("ENTRY=0,0", "ENTRY=abc"),
        VALID.replace("ENTRY=0,0", "ENTRY=1,2,3"),
        VALID.replace("PERFECT=TRUE", "PERFECT=maybe"),
        VALID + "ALGORITHM=prim\n",
        VALID + "SEED=later\n",
        "WIDTH=15\n",                                # everything else missing
    ],
)
def test_invalid_values_are_refused(tmp_path: Path, body: str) -> None:
    with pytest.raises(ValidationError):
        load_config(write(tmp_path, body))
