# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "perun"
copyright = "2023, Juan Pedro Gutiérrez Hermosillo Muriedas"
author = "Juan Pedro Gutiérrez Hermosillo Muriedas"
release = "0.8.9"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.duration",
    "sphinx.ext.doctest",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "autoapi.extension",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_title = "perun"
html_static_path = ["_static"]
# html_logo = "images/logo.svg"

# html_theme_options = {
#     "logo_only": False,
#     "style_nav_header_background": "#2980B9"
#

# AUTOAPI
autoapi_type = "python"
autoapi_dirs = ["../perun"]
