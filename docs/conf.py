# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

from napari_metadata._version import version as napari_metadata_version

release = napari_metadata_version
if 'dev' in release:  # noqa: SIM108
    version = 'dev'
else:
    version = release

# -- Project information -----------------------------------------------------

project = 'napari-metadata'
copyright = '2025, The napari team'  # noqa: A001
author = 'The napari team'

# -- General configuration ---------------------------------------------------

extensions = [
    'sphinx.ext.intersphinx',
    'sphinx_external_toc',
    'myst_nb',
    'sphinx.ext.viewcode',
    'sphinx_favicon',
    'sphinx_copybutton',
]

external_toc_path = '_toc.yml'

# -- Options for HTML output -------------------------------------------------

html_theme = 'napari_sphinx_theme'

html_theme_options = {
    'external_links': [{'name': 'napari', 'url': 'https://napari.org'}],
    'github_url': 'https://github.com/napari/napari-metadata',
    'navbar_start': ['navbar-logo', 'navbar-project'],
    'navbar_end': ['navbar-icon-links', 'theme-switcher'],
    'navbar_persistent': [],
    'header_links_before_dropdown': 6,
    'secondary_sidebar_items': ['page-toc'],
    'pygments_light_style': 'napari',
    'pygments_dark_style': 'napari',
}

html_static_path = ['_static']
html_logo = 'images/logo.png'
html_sourcelink_suffix = ''
html_title = 'napari-metadata'

favicons = [
    {
        # the SVG is the "best" and contains code to detect OS light/dark mode
        'static-file': 'favicon/logo-silhouette-dark-light.svg',
        'type': 'image/svg+xml',
    },
    {
        # Safari in Oct. 2022 does not support SVG
        # an ICO would work as well, but PNG should be just as good
        # setting sizes="any" is needed for Chrome to prefer the SVG
        'sizes': 'any',
        'static-file': 'favicon/logo-silhouette-192.png',
    },
    {
        # this is used on iPad/iPhone for "Save to Home Screen"
        # apparently some other apps use it as well
        'rel': 'apple-touch-icon',
        'sizes': '180x180',
        'static-file': 'favicon/logo-noborder-180.png',
    },
]

intersphinx_mapping = {
    'python': ['https://docs.python.org/3', None],
    'numpy': ['https://numpy.org/doc/stable/', None],
    'napari': [
        'https://napari.org/dev',
        'https://napari.org/dev/objects.inv',
    ],
}

myst_enable_extensions = [
    'colon_fence',
    'dollarmath',
    'substitution',
    'tasklist',
]

myst_heading_anchors = 4
suppress_warnings = ['etoc.toctree']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [
    '_build',
    'Thumbs.db',
    '.DS_Store',
    '.jupyter_cache',
    'jupyter_execute',
]
