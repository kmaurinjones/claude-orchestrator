#!/usr/bin/env python3
"""Setup configuration for claude-orchestrator package"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

# Read version from __init__.py
import re
with open("claude_orchestrator/__init__.py") as fp:
    version_match = re.search(r'^__version__ = [\'"]([^\'"]*)[\'"]', fp.read(), re.M)
    if version_match:
        VERSION = version_match.group(1)
    else:
        raise RuntimeError("Unable to find version string.")

setup(
    name="claude-orchestrator",
    version=VERSION,
    author="K. Maurin Jones",
    author_email="kmaurinjones@example.com",
    description="Orchestrate multiple Claude Code instances to work in parallel",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/kmaurinjones/claude-orchestrator",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        # No external dependencies - using only standard library
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=3.0",
            "black>=22.0",
            "isort>=5.0",
            "flake8>=4.0",
            "mypy>=0.950",
        ],
    },
    entry_points={
        "console_scripts": [
            "claude-orchestrator=claude_orchestrator.__main__:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)