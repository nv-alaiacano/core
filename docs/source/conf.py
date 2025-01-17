# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import re
import subprocess
import sys

from natsort import natsorted

sys.path.insert(0, os.path.abspath("../../"))

repodir = os.path.abspath(os.path.join(__file__, r"../../.."))
gitdir = os.path.join(repodir, r".git")

# -- Project information -----------------------------------------------------

project = "Merlin Core"
copyright = "2023, NVIDIA"  # pylint: disable=redefined-builtin
author = "NVIDIA"


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "myst_nb",
    "sphinx_design",
    "sphinx_multiversion",
    "sphinx_external_toc",
    "sphinx.ext.autodoc",
    "sphinx.ext.coverage",
    "sphinx.ext.githubpages",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinxcontrib.copydirs",
]

# MyST configuration settings
external_toc_path = "toc.yaml"
myst_enable_extensions = [
    "deflist",
    "html_image",
    "linkify",
    "replacements",
    "tasklist",
]
myst_linkify_fuzzy_links = False
myst_heading_anchors = 3
jupyter_execute_notebooks = "off"

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [
    "generated",
]

# The API documents are RST and include `.. toctree::` directives.
suppress_warnings = ["etoc.toctree"]

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_book_theme"
html_title = "Merlin Core"
html_theme_options = {
    "repository_url": "https://github.com/NVIDIA-Merlin/core",
    "use_repository_button": True,
    "footer_content_items": ["copyright.html", "last-updated.html"],
    "extra_footer": "",
    "logo": {"text": "NVIDIA Merlin Core", "alt_text": "NVIDIA Merlin Core"},
}
html_sidebars = {
    "**": [
        "navbar-logo.html",
        "search-field.html",
        "icon-links.html",
        "sbt-sidebar-nav.html",
        "merlin-ecosystem.html",
        "versions.html",
    ]
}
html_favicon = "_static/favicon.png"
html_copy_source = True
html_show_sourcelink = False

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
html_css_files = ["css/custom.css", "css/versions.css"]
html_js_files = ["js/rtd-version-switcher.js"]
html_context = {"analytics_id": "G-NVJ1Y1YJHK"}

if os.path.exists(gitdir):
    tag_refs = subprocess.check_output(["git", "tag", "-l", "v*"]).decode("utf-8").split()
    tag_refs = [tag for tag in tag_refs if re.match(r"^v[0-9]+.[0-9]+.[0-9]+$", tag)]
    tag_refs = natsorted(tag_refs)[-6:]
    smv_tag_whitelist = r"^(" + r"|".join(tag_refs) + r")$"
else:
    smv_tag_whitelist = r"^v.*$"

smv_branch_whitelist = r"^(main|stable)$"

smv_refs_override_suffix = "-docs"

html_baseurl = "https://nvidia-merlin.github.io/models/stable"

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "cudf": ("https://docs.rapids.ai/api/cudf/stable/", None),
    "distributed": ("https://distributed.dask.org/en/latest/", None),
}

autodoc_inherit_docstrings = False
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": False,
    "member-order": "bysource",
}

autosummary_generate = True

copydirs_additional_dirs = [
    "../../README.md",
    "../../LICENSE",
]
copydirs_file_rename = {
    "README.md": "index.md",
}
