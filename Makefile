BLANT_DEV  := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/DEV)
BLANT_BASE := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/BASE)
NET_DIR    := $(BLANT_DEV)/networks
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
TIMEOUT := 6000
RUNS    := 3

.PHONY: setup run clean

setup:
	git submodule update --init --recursive
	cd $(BLANT_DEV) && ./regression-test-all.sh -make
	cd $(BLANT_BASE) && ./regression-test-all.sh -make

run:
	$(PYTHON) $(SCRIPT) \
		--network $(NETWORK) \
		--timeout $(TIMEOUT) \
		--runs $(RUNS) \
		--out $(OUT)

clean:
	rm -f $(OUT)
	rm -rf $(BLANT_DEV) $(BLANT_BASE)
