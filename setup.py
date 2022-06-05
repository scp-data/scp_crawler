from setuptools import find_packages, setup

setup(
    name="scp_crawler",
    version="1.0",
    packages=find_packages(),
    entry_points={"scrapy": ["settings = scp_crawler.settings"]},
    install_requires=["Scrapy", "beautifulsoup4", "tqdm", "httpx"],
)
