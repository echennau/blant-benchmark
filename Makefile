.PHONY: compare

compare:
# 	time python3 main.py -c ./configs/base/fast.base.json
	time python3 main.py -c ./configs/dev/batch.dev.json

plot:
	python3 plot.py -d ./dev-sebas_output.csv
# 	python3 plot.py -i ./base_output.csv

sanity:
	time python3 main.py -c ./configs/test.json