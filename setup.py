from setuptools import setup, find_packages

setup(
    name="wlc-platform",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'flask',
        'flask-cors',
        'requests',
        'pandas',
        'ifcopenshell==0.8.2'
    ],
) 