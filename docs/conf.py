# -*- coding: utf-8 -*-
import os


def read_version():
    path = os.path.join('..', 'src', 'hexrec', '__init__.py')
    with open(path, 'rt') as file:
        for line in file:
            if line.startswith('__version__'):
                return eval(line.split('=')[1])
    raise ValueError(f'cannot find __version__ inside of {path}')


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
year = '2013-2022'
author = 'Andrea Zoppi'
copyright = f'{year}, {author}'
version = release = read_version()

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
html_short_title = f'{project}-{version}'
html_static_path = ['_static']
html_style = 'css/my_theme.css'

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

