MLX_WHEEL = mlx-2.2-py3-none-any.whl

# uv resolves `mlx` to $(MLX_WHEEL) via [tool.uv.sources], so the wheel has to
# be in place before `uv sync` -- otherwise resolution fails outright.
install: $(MLX_WHEEL)
	uv sync

$(MLX_WHEEL):
	@test -d $(MLX_DIR) || { echo "$(MLX_DIR)/ missing: get the MLX sources from the subject"; exit 1; }
	$(MAKE) -C $(MLX_DIR)

run:
	uv run a_maze_ing.py config.txt

debug:
	uv run python -m pdb a_maze_ing.py config.txt

clean:
	find . -type d -name '__pycache__' -prune -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache .venv uv.lock
	@test -d $(MLX_DIR) && $(MAKE) -C $(MLX_DIR) clean || true

lint:
	uv run flake8 .
	uv run mypy . --warn-return-any --warn-unused-ignores \
		--ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	uv run flake8 .
	uv run mypy . --strict

.PHONY: install mlx run debug clean lint lint-strict
