# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import datetime
import tomllib
from pathlib import Path

# Read project metadata from pyproject.toml
pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
pyproject_data = tomllib.loads(pyproject_path.read_text())

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "bfabricPy"
release = pyproject_data.get("project", {}).get("version", "")
version = release.split("+")[0] if release else ""

# Dynamic copyright year (same pattern as bfabric.py)
current_year = datetime.datetime.now().year
copyright = f"2014-{current_year} Functional Genomics Center Zurich"
author = "the bfabricpy authors"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinxcontrib.autodoc_pydantic",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_book_theme"
html_static_path = ["_static"]

# Theme options for sidebar navigation
html_theme_options = {
    "navigation_depth": 4,
    "collapse_navigation": False,
    "show_toc_level": 3,
}

# -- MyST Parser configuration -----------------------------------------------
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "dollarenv",
    "fieldlist",
    "html_admonition",
    "html_image",
    "linkify",
    "replacements",
    "smartquotes",
    "strikethrough",
    "substitution",
    "tasklist",
]

# Support for admonitions (from MkDocs)
myst_enable_checkboxes = True
myst_heading_anchors = 3
