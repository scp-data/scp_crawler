

DATA_FILES = data/scp_titles.json data/scp.json

PYTHON_VENV = source .venv/bin/activate &&

data: $(DATA_FILES)

.venv:
	python -m venv .venv
	source ./venv/bin/activate && python -m pip install .

data/scp_items.json: .venv
	$(PYTHON_VENV) python -m scrapy crawl scp -o data/scp_items.json

data/scp_titles.json: .venv
	python -m scrapy crawl scp_titles -o data/scp_titles.json

data/scp_tales.json: .venv
	python -m scrapy crawl scp_tales -o data/scp_tales.json

data/scp_int_items.json: .venv
	python -m scrapy crawl scp -o data/scp_int_items.json

data/scp_int_titles.json: .venv
	python -m scrapy crawl scp_titles -o data/scp_int_titles.json

data/scp_int_tales.json: .venv
	python -m scrapy crawl scp_tales -o data/scp_int_tales.json

data/goi.json: .venv
	python -m scrapy crawl goi -o data/goi.json
