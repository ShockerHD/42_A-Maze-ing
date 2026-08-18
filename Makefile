MLX_WHEEL = mlx-2.2-py3-none-any.whl

# uv resolves `mlx` to $(MLX_WHEEL) via [tool.uv.sources], so the wheel has to
# be in place before `uv sync` -- otherwise resolution fails outright.
install: $(MLX_WHEEL)
	uv sync

$(MLX_WHEEL):
	@echo "$(MLX_WHEEL) missing: get the MLX wheel from the subject"
	@exit 1

run:
	uv run a_maze_ing.py config.txt

debug:
	uv run python -m pdb a_maze_ing.py config.txt

clean:
	find . -type d -name '__pycache__' -prune -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache .venv maze_out.txt

lint:
	uv run flake8 .
	uv run mypy . --warn-return-any --warn-unused-ignores \
		--ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	uv run flake8 .
	uv run mypy . --strict

.PHONY: install run debug clean lint lint-strict
