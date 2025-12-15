SHELL=/bin/bash
PYTHON_VENV = source .venv/bin/activate &&

install: .venv

data: scp scp_int goi

fresh: clean data

clean:
	rm -Rf ./data/*

.venv:
	python -m venv .venv
	$(PYTHON_VENV) python -m pip install .

crawl: scp scp_int goi

scp: scp_crawl scp_postprocess

scp_crawl: data/scp_titles.json data/scp_hubs.json data/scp_items.json data/scp_tales.json data/goi.json data/scp_supplement.json

data/scp_titles.json: .venv
	$(PYTHON_VENV) python -m scrapy crawl scp_titles -o data/scp_titles.json

data/scp_items.json: .venv
	$(PYTHON_VENV) python -m scrapy crawl scp -o data/scp_items.json

data/scp_hubs.json: .venv
	$(PYTHON_VENV) python -m scrapy crawl scp_hubs -o data/scp_hubs.json

data/scp_tales.json: .venv
	$(PYTHON_VENV) python -m scrapy crawl scp_tales -o data/scp_tales.json

goi: data/goi.json

data/goi.json: .venv
	$(PYTHON_VENV) python -m scrapy crawl goi -o data/goi.json

supplement: supplement_crawl supplement_postprocess

supplement_crawl: data/scp_supplement.json

data/scp_supplement.json: .venv
	$(PYTHON_VENV) python -m scrapy crawl scp_supplement -o data/scp_supplement.json

supplement_postprocess: supplement_crawl data/processed/supplement

data/processed/supplement: .venv
	$(PYTHON_VENV) python -m scp_crawler.postprocessing run-postproc-supplement

scp_postprocess: scp_crawl data/processed/goi data/processed/items data/processed/tales data/processed/supplement

data/processed/goi: .venv
	$(PYTHON_VENV) python -m scp_crawler.postprocessing run-postproc-goi

data/processed/items: .venv
	$(PYTHON_VENV) python -m scp_crawler.postprocessing run-postproc-items

data/processed/tales: .venv
	$(PYTHON_VENV) python -m scp_crawler.postprocessing run-postproc-tales

scp_int: data/scp_int_titles.json data/scp_int_items.json data/scp_int_tales.json

data/scp_int_titles.json: .venv
	$(PYTHON_VENV) python -m scrapy crawl scp_int_titles -o data/scp_int_titles.json

data/scp_int_items.json: .venv
	$(PYTHON_VENV) python -m scrapy crawl scp_int -o data/scp_int_items.json

data/scp_int_tales.json: .venv
	$(PYTHON_VENV) python -m scrapy crawl scp_int_tales -o data/scp_int_tales.json


clean_data:
	rm -Rf data/*
