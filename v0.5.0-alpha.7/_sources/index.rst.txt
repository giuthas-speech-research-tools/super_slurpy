.. slurpy documentation master file, created by
   sphinx-quickstart on Sat Apr 25 21:52:22 2026.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Super SLURPy documentation
==========================

Super SLURPy is a Python version of the Speech and Language Ultrasound Research
Package (`SLURP <https://github.com/cathylaporte/SLURP>`_). It provides a Python
API and a Python program. The latter is simply called ``slurpy`` and launches the
GUI.

Slurpy tracks the tongue contour in ultrasound videos.

.. toctree::
   :maxdepth: 2
   :titlesonly:
   :caption: Contents:

   Installation.markdown
   Cli.markdown
   Gui.markdown
   Parameters.markdown
   Changelog.markdown
   Contributors.markdown

.. toctree::
   :maxdepth: 2
   :titlesonly:
   :caption: API Reference:

   api/modules

Contributors and contributing
-----------------------------

We welcome contributions. Please get in touch before putting too much work in
so that we can coordinate efforts. 

For a list of people involved in development, see the Contributors section in the sidebar.

A note on the name(s)
---------------------

The 'super' in the package/project name is there only to avoid a conflict with
a different project called ``slurpy``. And maybe because it's kinda super to have
a Python version of SLURP. 

The commandline command is shorter (as are many class and file names) to make
life easier when using the program. It's also fine to refer to the project by
the shorter name, just as long as you are aware that the long name is used on
PyPI and thus for installing.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`