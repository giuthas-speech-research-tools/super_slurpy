# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= uv run sphinx-build
SOURCEDIR     = source
BUILDDIR      = build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

gen-docs:
	@echo "Cleaning old generated files..."
	rm -rf source/src
	rm -rf source/api
	rm -rf build
	@echo "Generating new stubs..."
	uv run sphinx-apidoc -f -e -o source/api ../src/super_slurpy
	@echo "Cleaning up RST headers..."
	uv run python clean_rst.py
	@echo "Building HTML..."
	$(MAKE) html
	
html: 
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# Removed to sort circular make <- make dependency.
# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
# %: Makefile
# 	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
