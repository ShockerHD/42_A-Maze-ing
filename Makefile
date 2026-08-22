MLX_WHEEL = mlx-2.2-py3-none-any.whl
MLX_SRC = mlx_CLXV-2.2/mlx_CLXV

# uv resolves `mlx` to $(MLX_WHEEL) via [tool.uv.sources], so the wheel has to
# be in place before `uv sync` -- otherwise resolution fails outright.
install: $(MLX_WHEEL)
	uv sync
	@$(MAKE) --no-print-directory mlx-native

$(MLX_WHEEL):
	@echo "$(MLX_WHEEL) missing: get the MLX wheel from the subject"
	@exit 1

# The wheel is tagged py3-none-any but ships a prebuilt x86-64 libmlx.so, so on
# any other architecture the import blows up with a misleading "cannot open
# shared object file". Rebuild MiniLibX from the sources next to the wheel and
# drop the result into the venv. `uv sync` re-extracts the wheel, so this has to
# run after it, and `run` re-checks in case someone synced by hand. The rm
# before the cp matters: uv hardlinks venv files to its global cache, so writing
# in place would edit the cached wheel contents too.
mlx-native:
	@if [ "$$(uname -m)" = "x86_64" ]; then exit 0; fi; \
	so=$$(ls .venv/lib/python*/site-packages/mlx/libmlx.so 2>/dev/null); \
	if [ -z "$$so" ]; then exit 0; fi; \
	if ! file -L "$$so" | grep -q x86-64; then exit 0; fi; \
	if [ ! -d "$(MLX_SRC)" ]; then \
		echo "$(MLX_SRC) missing: unpack the MiniLibX sources from the subject"; \
		exit 1; \
	fi; \
	echo "libmlx.so is x86-64 on $$(uname -m): rebuilding MiniLibX"; \
	$(MAKE) -C $(MLX_SRC) libmlx.so || exit 1; \
	rm -f "$$so"; \
	cp $(MLX_SRC)/libmlx.so "$$so"

run: mlx-native
	uv run a_maze_ing.py config.txt

debug:
	uv run python -m pdb a_maze_ing.py config.txt

build:
	cd mazegen && uv run python -m build --outdir ..

clean:
	find . -type d -name '__pycache__' -prune -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache .venv maze_out.txt mazegen/mazegen.egg-info mazegen/.venv

lint:
	uv run flake8 .
	uv run mypy . --warn-return-any --warn-unused-ignores \
		--ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	uv run flake8 .
	uv run mypy . --strict

.PHONY: install run debug build clean lint lint-strict mlx-native
