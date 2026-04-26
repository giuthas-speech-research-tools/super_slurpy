
# Optional autodoc tweaks to play nicely with Cython's C-types
autodoc_mock_imports = []

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'slurpy'
copyright = '2026, Pertti Palo, Catherine Laporte'
author = 'Pertti Palo, Catherine Laporte'
release = '0.4.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',  # If using Google/NumPy docstrings
    'sphinx.ext.viewcode',  # Optional: links to source code
    'sphinx_autodoc_typehints',  # Optional: formats typehints beautifully
    'myst_parser',
    "sphinx_copybutton",        # For copying code listings
]

# Napoleon settings
napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_use_ivar = True

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'furo'
html_static_path = ['_static']

source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
    '.markdown': 'markdown',
}

# 1. The core Sphinx setting to stop prefixing everything with the module name
add_module_names = False

# 2. Specifically tell autodoc to format type hints as short names
autodoc_typehints_format = "short"

# 3. If you are using sphinx_autodoc_typehints, this is the magic flag
typehints_fully_qualified = False

# 4. Tells Sphinx to try and simplify type names even if they are imported
python_use_unqualified_type_names = True

# 2. Removes the parent module path from the Sidebar/Table of Contents
toc_object_entries_show_parents = 'hide'

# 3. Ensures the class signature in the doc doesn't show the full path
autodoc_class_signature = "separated"

# Tells the index to ignore these prefixes when sorting
modindex_common_prefix = ["super_slurpy."]

# Strip standard terminal prompts when copying
copybutton_prompt_text = (
    r">>> |\.\.\. |\$ |In \[\d*\]: | {2,5}\.\.\.: | {5,8}: ")
copybutton_prompt_is_regexp = True
