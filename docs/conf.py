# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "perun"
copyright = "2023, Juan Pedro Gutiérrez Hermosillo Muriedas"
author = "Juan Pedro Gutiérrez Hermosillo Muriedas"
release = "0.8.10"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    # "sphinx.ext.duration",
    # "sphinx.ext.doctest",
    "autoapi.extension",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    # "sphinx_gallery.gen_gallery"
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_title = "perun"
html_static_path = ["_static"]
html_logo = "images/logo.svg"

# html_theme_options = {
#     "logo_only": False,
#     "style_nav_header_background": "#2980B9"
#

# AUTOAPI
autoapi_type = "python"
autoapi_dirs = ["../perun"]

autoapi_template_dir = "_templates/autoapi"

autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    "show-module-summary",
    "imported-members"
]
autodoc_typehints="signature"

# Gallery
# sphinx_gallery_conf = {
#     "examples_dirs": '../examples',
#     "gallery_dirs": 'auto_examples'
# }
