.PHONY: compare

compare:
	time python3 main.py -c ./configs/base/fast.base.json
	time python3 main.py -c ./configs/base/fast.dev.json