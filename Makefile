.PHONY: compare plot_compare plot_dev all

all:
	@echo "no default target."

plot_dev:
	python3 plot.py -d ./dev-sebas_output.csv

plot_compare:
	python3 plot.py -b ./base_output.csv -d ./dev-sebas_output.csv

compare:
	time python3 main.py -c ./configs/base/fast.base.json
	time python3 main.py -c ./configs/dev/fast.dev.json