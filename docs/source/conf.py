# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Wiki'
copyright = '2025, Tatsuki Yano'
author = 'Tatsuki Yano'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "myst_parser",
]

myst_enable_extensions = [
    #"colcon_fence",
    "deflist",
    "tasklist",
]

templates_path = ['_templates']
exclude_patterns = []

language = 'ja'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_title = "Wiki"

#html_theme = 'alabaster'

# uv add guro
# 他のテーマも使える
html_theme = "furo"

html_static_path = ['_static']
