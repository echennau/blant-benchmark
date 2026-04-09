BLANT_DIR  := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../DEV)
NET_DIR    := $(BLANT_DIR)/networks
YEAST_EL   := $(NET_DIR)/yeast.el
SYEAST_EL  := $(NET_DIR)/syeast.el

# Prefer yeast.el; fall back to syeast.el
ifeq ($(wildcard $(YEAST_EL)),)
    NETWORK := $(SYEAST_EL)
else
    NETWORK := $(YEAST_EL)
endif

PYTHON  := python3
SCRIPT  := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/benchmark.py)
OUT     := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/output.csv)
TIMEOUT := 600
RUNS    := 3

.PHONY: run clean

run:
	$(PYTHON) $(SCRIPT) \
		--network $(NETWORK) \
		--timeout $(TIMEOUT) \
		--runs $(RUNS) \
		--out $(OUT)

clean:
	rm -f $(OUT)
