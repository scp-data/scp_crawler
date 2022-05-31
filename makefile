SHELL=/bin/bash
PYTHON_VENV = source .venv/bin/activate &&

data: scp scp_int goi

install: .venv

fresh: clean data

clean:
	rm -Rf ./data/*

.venv:
	python -m venv .venv
	$(PYTHON_VENV) python -m pip install .

crawl: scp scp_int goi

scp: scp_crawl scp_postprocess

scp_crawl: data/scp_titles.json data/scp_hubs.json data/scp_items.json data/scp_tales.json

data/scp_titles.json: .venv
	$(PYTHON_VENV) python -m scrapy crawl scp_titles -o data/scp_titles.json

data/scp_items.json: .venv
	$(PYTHON_VENV) python -m scrapy crawl scp -o data/scp_items.json

data/scp_hubs.json: .venv
	$(PYTHON_VENV) python -m scrapy crawl scp_hubs -o data/scp_hubs.json

data/scp_tales.json: .venv
	$(PYTHON_VENV) python -m scrapy crawl scp_tales -o data/scp_tales.json

scp_postprocess: scp_crawl
	$(PYTHON_VENV) python ./scp_crawler/postprocessing.py


scp_int: data/scp_int_titles.json data/scp_int_items.json data/scp_int_tales.json

data/scp_int_titles.json: .venv
	$(PYTHON_VENV) python -m scrapy crawl scp_int_titles -o data/scp_int_titles.json

data/scp_int_items.json: .venv
	$(PYTHON_VENV) python -m scrapy crawl scp_int -o data/scp_int_items.json

data/scp_int_tales.json: .venv
	$(PYTHON_VENV) python -m scrapy crawl scp_int_tales -o data/scp_int_tales.json

goi: data/goi.json

data/goi.json: .venv
	$(PYTHON_VENV) python -m scrapy crawl goi -o data/goi.json


clean_data:
	rm -Rf data/*
