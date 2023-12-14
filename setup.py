from setuptools import find_packages, setup

setup(
    name="scp_crawler",
    version="1.0",
    packages=find_packages(),
    entry_points={"scrapy": ["settings = scp_crawler.settings"], "console_scripts": ["scp_pp = scp_crawler:postprocessing"]},
    install_requires=["Scrapy", "beautifulsoup4", "tqdm", "httpx", "typer"],
)
