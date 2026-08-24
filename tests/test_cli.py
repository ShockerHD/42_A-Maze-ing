"""Every error path out of main(): non-zero, explained, never a traceback.

Only the paths that fail before the window opens are exercised here --
main() blocks in mlx_loop once a maze survives validation, and a test
suite has no business opening a window.
"""

from pathlib import Path

import pytest

from a_maze_ing import EXIT_ERROR, EXIT_USAGE, main
from tests.test_config import VALID, write


def run(
    capsys: pytest.CaptureFixture[str], *argv: str
) -> tuple[int, str]:
    """main() with *argv*, returning its code and what it said on stderr."""
    code = main(["a_maze_ing.py", *argv])
    return code, capsys.readouterr().err


def test_too_many_arguments_is_a_usage_error(
    capsys: pytest.CaptureFixture[str]
) -> None:
    code, err = run(capsys, "one.txt", "two.txt")
    assert code == EXIT_USAGE
    assert "usage:" in err


def test_missing_config_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, err = run(capsys, str(tmp_path / "nope.txt"))
    assert code == EXIT_ERROR
    assert "cannot read" in err
    assert "Traceback" not in err


def test_unreadable_config_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write(tmp_path, VALID)
    path.chmod(0o000)
    try:
        code, err = run(capsys, str(path))
    finally:
        path.chmod(0o644)  # or the tmp dir cannot be cleaned up
    assert code == EXIT_ERROR
    assert "cannot read" in err
    assert "Traceback" not in err


def test_malformed_line_is_reported_with_its_line_number(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, err = run(capsys, str(write(tmp_path, VALID + "GARBAGE\n")))
    assert code == EXIT_ERROR
    assert "config.txt:7" in err
    assert "Traceback" not in err


@pytest.mark.parametrize(
    "body, expected",
    [
        (VALID.replace("WIDTH=15", "WIDTH=0"), "WIDTH"),
        (VALID.replace("ENTRY=0,0", "ENTRY=99,0"), "ENTRY"),
        (VALID.replace("ENTRY=0,0", "ENTRY=14,14"), "different cells"),
        (VALID + "ALGORITHM=prim\n", "ALGORITHM"),
    ],
)
def test_invalid_values_name_the_key_that_is_wrong(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    body: str,
    expected: str,
) -> None:
    code, err = run(capsys, str(write(tmp_path, body)))
    assert code == EXIT_ERROR
    assert expected in err
    assert "Traceback" not in err


def test_unwritable_output_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    body = VALID.replace(
        "OUTPUT_FILE=maze_out.txt",
        f"OUTPUT_FILE={tmp_path / 'no-such-dir' / 'maze.txt'}",
    )
    code, err = run(capsys, str(write(tmp_path, body)))
    assert code == EXIT_ERROR
    assert "cannot write" in err
    assert "Traceback" not in err
