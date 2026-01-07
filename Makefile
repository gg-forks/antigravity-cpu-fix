#.ONESHELL:
SHELL=/bin/bash
.DEFAULT_GOAL=_help

# OS Detection
AG_OS := $(shell uname -s)

# Defaults
_AG_SRC_LINUX := /usr/share/antigravity
_AG_SRC_MAC := /Applications/Antigravity.app/Contents
_AG_CONF_LINUX := $(HOME)/.config
_AG_CONF_MAC := $(HOME)/Library/Application Support


# Logic - allow AG_SRC and AG_CONF override from environment
ifndef AG_CONF
    # $(info Getting AG_CONF from defaults, didn't receive it as env var.)
    ifeq ($(AG_OS),Darwin)
        AG_CONF := $(_AG_CONF_MAC)
    else
        AG_CONF := $(_AG_CONF_LINUX)
    endif
endif

ifndef AG_SRC
    # $(info Getting AG_SRC from defaults, didn't receive it as env var.)
    ifeq ($(AG_OS),Darwin)
        AG_SRC := $(_AG_SRC_MAC)
    else
        # Linux: prefer apt (/usr/share), fallback to /opt
        AG_SRC := $(_AG_SRC_LINUX)
        ifneq (,$(wildcard /opt/Antigravity/resources/.))
            AG_SRC := /opt/Antigravity
        endif
        ifneq (,$(wildcard /usr/share/antigravity/resources/.))
            AG_SRC := /usr/share/antigravity
        endif
    endif
endif


# Checks/defaults
_AG_CHECK_AG_SRC_DIR := $(shell [ -d "$(AG_SRC)" ] && echo 1)

AG_FILE_01_MAIN_JS = $(AG_SRC)/resources/app/out/jetskiAgent/main.js
_AG_CHECK_MAIN_JS := $(shell [ -f "$(AG_FILE_01_MAIN_JS)" ] && echo 1)
_AG_CHECK_MAIN_WRITABLE := $(shell [ -w "$(AG_FILE_01_MAIN_JS)" ] && echo 1)

AG_FILE_02_PRODUCT_JSON = $(AG_SRC)/resources/app/product.json
_AG_CHECK_PRODUCT_JSON := $(shell [ -f "$(AG_FILE_02_PRODUCT_JSON)" ] && echo 1)
_AG_CHECK_PRODUCT_WRITABLE := $(shell [ -w "$(AG_FILE_02_PRODUCT_JSON)" ] && echo 1)
# Extract version from product.json, trimming whitespace
AG_VERSION := $(if $(wildcard $(AG_FILE_02_PRODUCT_JSON)),$(shell jq -r '.version' "$(AG_FILE_02_PRODUCT_JSON)" | sed 's/^[[:space:]]*//;s/[[:space:]]*$$//'))

AG_FILE_03_SETTINGS_JSON = $(AG_CONF)/Antigravity/User/settings.json
_AG_CHECK_SETTINGS := $(shell [ -f "$(AG_FILE_03_SETTINGS_JSON)" ] && echo 1)
# --- END default vals SECTION ---



.PHONY: doctor
doctor: ##H@@	Check paths and health (Dry Run)
	@echo "=== Antigravity Doctor ==="
	@echo "Detected OS:         $(AG_OS)"
	@echo ""
	@echo "AG_SRC (Source):     $(AG_SRC)"
	@echo "  (Override with: AG_DIR=/your/path make doctor)"
	@echo ""
	@echo "Main Entry Point:    $(AG_FILE_01_MAIN_JS)"
	@echo "Product Metadata:    $(AG_FILE_02_PRODUCT_JSON)"
	@echo "Antigravity Version: $(AG_VERSION)"
	@echo ""
	@echo "AG_CONF (Config):    $(AG_CONF)"
	@echo "  (Override with: AG_CONF=/your/path make doctor)"
	@echo ""
	@echo "Settings File:       $(AG_FILE_03_SETTINGS_JSON)"
	@echo "Backups:              .bak files next to originals"
	@echo ""
	@echo "--- Checks ---"
# check main.js (jetSki agent)
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
ifeq ($(_AG_CHECK_AG_SRC_DIR),1)
	@echo "[OK] AG_SRC found: $(AG_SRC)"
ifeq ($(_AG_CHECK_MAIN_JS),1)
	@echo "[OK] main.js found"
ifeq ($(_AG_CHECK_MAIN_WRITABLE),1)
	@echo "   [INFO] main.js is writable (No sudo needed for patch)"
else
	@echo "   [WARN] main.js NOT writable (sudo or change owner REQUIRED)"
endif
else
	@echo "[FAIL] main.js NOT found in resources/app/out/jetskiAgent/"
endif
# check product.json (verification sha)
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
ifeq ($(_AG_CHECK_PRODUCT_JSON),1)
	@echo "[OK] product.json found (Version: $(AG_VERSION))"
	@if [ "$(AG_VERSION)" = "1.104.0" ]; then \
		echo "   [OK] Version 1.104.0 exact match"; \
	else \
		echo "   [WARN] Unexpected version: \"$(AG_VERSION)\" (Expected: \"1.104.0\")"; \
	fi
ifeq ($(_AG_CHECK_PRODUCT_WRITABLE),1)
	@echo "   [INFO] product.json is writable (No sudo needed)"
else
	@echo "   [WARN] product.json NOT writable (sudo or change owner REQUIRED)"
endif
else
	@echo "[FAIL] product.json NOT found in resources/app/"
endif
else
	@echo "[FAIL] AG_SRC NOT found (Is Antigravity installed?)"
endif
# check settings
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
ifeq ($(_AG_CHECK_SETTINGS),1)
	@echo "[OK] Settings file found at $(AG_FILE_03_SETTINGS_JSON)"
else
	@echo "[FAIL] Settings file NOT found at $(AG_FILE_03_SETTINGS_JSON)"
endif
	@echo ""
	@echo "To proceed with the patch, correct any issues and run this command:"
	@echo ""
	@echo "   make  1_optimize_settings  2_patch_code  3_update_integrity"
	@echo ""
# --- END doctor TARGET ---



# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Help targets
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.PHONY: _help
_help:
	@printf "\nUsage: make <command>, valid commands:\n\n"
	@grep -h "##H@@" $(MAKEFILE_LIST) | grep -v IGNORE_ME | sed -e 's/##H@@//' | column -t -s $$'\t'

# Display variables & values
.PHONY: vars
vars: ##H@@	Display all Makefile variables (simple)
	@echo "=== Makefile Variables (file/command/line origin) ==="
	@$(foreach V,$(sort $(.VARIABLES)), \
		$(if $(filter file command line,$(origin $(V))), \
			printf "%-30s = " "$(V)" ; \
			printf "%s\n" "$($(V))" ; \
		) \
	)
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Development commands
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.PHONY: format
format: ##H@@	Run black & isort
	isort python/
	black python/
	ruff check --fix --silent --exit-zero python/
	-prettier --write .github/
	@echo OK.

.PHONY: lint
lint: ##H@@	Run ruff
	ruff check python/
	-yamllint -d '{rules: {line-length: {max: 100}}}' .github/workflows/
	@echo OK.


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Main "Patch" targets
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.PHONY: 1_optimize_settings
1_optimize_settings: ##H@@	Run settings optimization (Auto-detected OS path)
	@echo "Detected OS: $(OS)"
	@echo "AG_CONF (Config): $(AG_CONF)"
	python3 python/optimize_settings.py "$(AG_CONF)"

.PHONY: 2_patch_code
2_patch_code: ##H@@	Run code patcher (Auto-detected OS path)
	@echo "Detected OS: $(OS)"
	@echo "AG_SRC (Source): $(AG_SRC)"
	# This usually requires sudo
	python3 python/patch_code.py "$(AG_SRC)"

.PHONY: 3_update_integrity
3_update_integrity: ##H@@	Update integrity manifest
	@echo "Detected OS: $(OS)"
	@echo "AG_SRC (Source): $(AG_SRC)"
	# This usually requires sudo
	python3 python/update_integrity.py "$(AG_SRC)"

# TODO: do not automate this step, just output the commands that likely would with helpful comments
.PHONY: rollback
rollback: ##H@@	Restore from backups
	@echo "You can manually restore by copying main.js and product.json from \"archive/ag-$(AG_VERSION)\""
	@echo "  and removing any of the sections added to the settings file manually."
	@echo "MAKE SURE THE VERSION MATCHES BEFORE DOING SO."
