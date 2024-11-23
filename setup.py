from setuptools import setup, find_packages

setup(
    name="ml_app",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'flask',
        'requests',
    ],
)
