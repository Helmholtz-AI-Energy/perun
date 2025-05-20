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
    "autoapi.extension",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
# html_title = ""
html_static_path = ["_static"]
html_logo = "images/full_logo_vertical.svg"

html_theme_options = {
    "sidebar_hide_name": True,
    "navigation_with_keys": True,
    "light_css_variables": {
        "color-brand-primary": "#00599f",
        "color-brand-content": "#8bb31f",
    },

}


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
