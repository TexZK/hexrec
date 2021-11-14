# -*- coding: utf-8 -*-
import os

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.coverage',
    'sphinx.ext.doctest',
    'sphinx.ext.extlinks',
    'sphinx.ext.ifconfig',
    'sphinx.ext.napoleon',
    'sphinx_autodoc_typehints',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
    'sphinx_click.ext',
]
if os.getenv('SPELLCHECK'):
    extensions += 'sphinxcontrib.spelling',
    spelling_show_suggestions = True
    spelling_lang = 'en_US'

source_suffix = '.rst'
master_doc = 'index'
project = 'hexrec'
year = '2021'
author = 'Andrea Zoppi'
copyright = '{0}, {1}'.format(year, author)
version = release = '0.2.3'

pygments_style = 'trac'
templates_path = ['_templates']
extlinks = {
    'issue': ('https://github.com/TexZK/hexrec/issues/%s', '#'),
    'pr': ('https://github.com/TexZK/hexrec/pull/%s', 'PR #'),
}
# on_rtd is whether we are on readthedocs.org
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

if not on_rtd:  # only set the theme if we're building docs locally
    html_theme = 'sphinx_rtd_theme'

html_use_smartypants = True
html_last_updated_fmt = '%Y-%m-%d'
html_split_index = False
html_sidebars = {
   '**': ['searchbox.html', 'globaltoc.html', 'sourcelink.html'],
}
html_short_title = '%s-%s' % (project, version)
html_static_path = ['_static']
html_style = 'css/my_theme.css'

autoclass_content = 'both'
autodoc_default_flags = [
    'members',
    'inherited-members',
    'private-members',
    'show-inheritance',
]
autodoc_inherit_docstrings = True
autodoc_member_order = 'bysource'
autosummary_generate = True
autosummary_generate_overwrite = True

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = False
napoleon_use_ivar = True
napoleon_use_rtype = False
napoleon_use_param = True
napoleon_include_private_with_doc = True
napoleon_include_special_with_doc = True

typehints_document_rtype = False
