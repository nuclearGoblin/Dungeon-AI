# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Dungeon AI'
copyright = '2024, nuclearGoblin'
author = 'nuclearGoblin'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

import sys, os
sys.path.insert(0, os.path.abspath('../../'))
#sys.path.insert(0, os.path.abspath('_extensions'))

extensions = [#'sphinx.ext.autosummary',
              'sphinx.ext.autodoc'
              #,'attributetable'
              ]

templates_path = ['_templates']
exclude_patterns = ['build','_templates']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']

# -- Options for autosummary -------------------------------------------------
autodoc_default_flags = ['members']
autosummary_generate = True