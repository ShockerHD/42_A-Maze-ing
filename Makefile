MLX_DIR = mlx_CLXV
MLX_WHEEL = $(MLX_DIR)/mlx-2.2-py3-none-any.whl

install:
	uv sync
	$(MAKE) mlx

# MLX is not a pyproject dependency -- the wheel is built from the local
# mlx_CLXV sources, so `uv sync` prunes it every time. Reinstall it after.
mlx: $(MLX_WHEEL)
	uv pip install --python .venv/bin/python $(MLX_WHEEL)

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
