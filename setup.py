from setuptools import setup, find_packages
import os
from pathlib import Path


# 读取版本号
def get_version():
    version_file = Path(__file__).parent / "src" / "version.py"
    if version_file.exists():
        namespace = {}
        exec(version_file.read_text(), namespace)
        return namespace["__version__"]
    return "0.1.0"


# 读取依赖
def read_requirements(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


setup(
    name="smart-memo",
    version=get_version(),
    author="FanFanFan",
    author_email="your.email@example.com",
    description="一个基于AI的智能备忘录应用",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/smart-memo",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/smart-memo/issues",
        "Documentation": "https://github.com/yourusername/smart-memo/wiki",
        "Source Code": "https://github.com/yourusername/smart-memo",
    },
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Office/Business :: Scheduling",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Environment :: X11 Applications :: Qt",
        "Natural Language :: Chinese (Simplified)",
    ],
    python_requires=">=3.9",
    install_requires=read_requirements("requirements.txt"),
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-qt>=4.2.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "pylint>=2.17.0",
            "mypy>=1.5.1",
            "autopep8>=2.0.0",
            "flake8>=6.1.0",
        ],
    },
    package_data={
        "smart_memo": [
            "assets/*.png",
            "assets/*.wav",
            "assets/*.ico",
        ],
    },
    entry_points={
        "console_scripts": [
            "smart-memo=src.main:main",
        ],
        "gui_scripts": [
            "smart-memo-gui=src.main:main",
        ],
    },
    zip_safe=False,
)
