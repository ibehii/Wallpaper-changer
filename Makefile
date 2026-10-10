.PHONY: all install install-bin test clean uninstall

all: install

install:
	pip install .

install-bin:
	pip install .
	@BIN_SRC=$$(which wchanger 2>/dev/null || echo "$$HOME/.local/bin/wchanger"); \
	if [ -w /bin ] || [ "$$(id -u)" -eq 0 ]; then \
		ln -sf "$$BIN_SRC" /bin/wchanger; \
		echo "[+] Linked /bin/wchanger -> $$BIN_SRC"; \
	elif command -v sudo >/dev/null 2>&1; then \
		sudo ln -sf "$$BIN_SRC" /bin/wchanger; \
		echo "[+] Linked /bin/wchanger -> $$BIN_SRC"; \
	else \
		echo "[!] Error: write permission to /bin required (run with sudo)"; \
		exit 1; \
	fi

test:
	python3 -m unittest discover -s tests

clean:
	rm -rf build dist *.egg-info __pycache__ tests/__pycache__

uninstall:
	pip uninstall -y wchanger
	@if [ -w /bin ] || [ "$$(id -u)" -eq 0 ]; then \
		rm -f /bin/wchanger; \
	elif command -v sudo >/dev/null 2>&1; then \
		sudo rm -f /bin/wchanger; \
	fi
