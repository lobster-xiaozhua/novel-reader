"""
Django apps package.
Monkey-patch for Python 3.14 compatibility with Django 4.2.
"""

import sys

# Fix Python 3.14 compatibility issue with Django 4.2 BaseContext.__copy__
# In Python 3.14, copy(super()) returns the super object itself, which cannot
# have new attributes assigned to it.
if sys.version_info >= (3, 14):
    from django.template.context import BaseContext
    import copy as _copy

    def _fixed_basecontext_copy(self):
        duplicate = object.__new__(self.__class__)
        BaseContext.__init__(duplicate)
        duplicate.dicts = self.dicts[:]
        return duplicate

    BaseContext.__copy__ = _fixed_basecontext_copy
