from setuptools import setup, find_packages

setup(
    name="reservations",
    version="1.0.0",
    packages=find_packages(),
    py_modules=['main'],
    install_requires=[
        "click>=8.0",
        "gspread>=6.0", 
        "pandas>=2.0",
        "google-auth>=2.0"
    ],
    entry_points={
        "console_scripts": [
            "reservations=main:cli"
        ]
    },
    python_requires=">=3.9",
)

