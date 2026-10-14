.PHONY: all install install-bin install-extension pack-extension uninstall-extension test clean uninstall

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

install-extension:
	@UUID="wchanger@ibehii.github.com"; \
	DEST="$$HOME/.local/share/gnome-shell/extensions/$$UUID"; \
	echo "[*] Compiling extension GSettings schemas..."; \
	glib-compile-schemas extension/schemas/; \
	echo "[*] Installing GNOME Shell extension to $$DEST..."; \
	mkdir -p "$$DEST"; \
	cp -r extension/metadata.json extension/extension.js extension/prefs.js extension/stylesheet.css extension/schemas "$$DEST/"; \
	echo "[+] Extension installed successfully!"; \
	echo "[i] To enable now, run: gnome-extensions enable $$UUID"; \
	echo "[i] Note: On Wayland sessions, log out and log back in to reload GNOME Shell."

pack-extension:
	@mkdir -p dist
	@UUID="wchanger@ibehii.github.com"; \
	cd extension && gnome-extensions pack --force --out-dir=../dist/
	@echo "[+] Packaged extension created in dist/"

uninstall-extension:
	@UUID="wchanger@ibehii.github.com"; \
	DEST="$$HOME/.local/share/gnome-shell/extensions/$$UUID"; \
	rm -rf "$$DEST"; \
	echo "[+] Removed GNOME Shell extension $$UUID"

test:
	python3 -m unittest discover -s tests

clean:
	rm -rf build dist *.egg-info __pycache__ tests/__pycache__

uninstall: uninstall-extension
	pip uninstall -y wchanger
	@if [ -w /bin ] || [ "$$(id -u)" -eq 0 ]; then \
		rm -f /bin/wchanger; \
	elif command -v sudo >/dev/null 2>&1; then \
		sudo rm -f /bin/wchanger; \
	fi
