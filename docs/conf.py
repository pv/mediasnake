needs_sphinx = '1.0'
extensions = ['sphinxcontrib.fulltoc']
templates_path = []
source_suffix = '.rst'
master_doc = 'index'

project = u'Mediasnake'
copyright = u'2013, Pauli Virtanen'
version = '0.1'
release = '0.1'
exclude_patterns = ['_build', 'examples']
pygments_style = 'sphinx'

html_theme = 'mediasnake'
html_static_path = []
html_theme_path = ['_theme']
html_use_index = False
html_show_sourcelink = False
html_sidebars = {
   '**': ['localtoc.html'],
}

man_pages = [
    ('index', 'mediasnake', u'mediasnake Documentation',
     [u'Pauli Virtanen'], 1)
]

texinfo_documents = [
  ('index', 'mediasnake', u'mediasnake Documentation',
   u'Pauli Virtanen', 'mediasnake', 'One line description of project.',
   'Miscellaneous'),
]
