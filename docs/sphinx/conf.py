"""Sphinx configuration for the DSW KM Translation Tool docs."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

project = "DSW KM Translation Tool"
author = "depositar"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "myst_parser",
]

exclude_patterns = ["_build"]
html_theme = "furo"
html_title = "DSW KM Translation Tool"

autodoc_class_signature = "separated"
autodoc_default_options = {
    "exclude-members": "__init__",
}
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_typehints_format = "short"
napoleon_google_docstring = True
napoleon_numpy_docstring = False
myst_enable_extensions = [
    "colon_fence",
]
