from setuptools import setup, find_packages

setup(
    name='playlist_scraper',
    version='0.1.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'fastapi',
        'uvicorn',
        'requests',
        'python-dotenv',  # Added to handle environment variables
    ],
    entry_points={
        'console_scripts': [
            'playlist_scraper = src.api:run',
        ],
    },
)
