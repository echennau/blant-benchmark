.PHONY: compare

plot:
	python3 plot.py -d ./dev-sebas_output.csv
# 	python3 plot.py -i ./base_output.csv

compare:
# 	time python3 main.py -c ./configs/base/fast.base.json
	time python3 main.py -c ./configs/dev/fast.dev.json