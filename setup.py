from setuptools import setup, find_packages

setup(
    name             = 'scp_crawler',
    version          = '1.0',
    packages         = find_packages(),
    entry_points     = {'scrapy': ['settings = scp_crawler.settings']},
    install_requires = ['Scrapy', 'beautifulsoup4']
)
