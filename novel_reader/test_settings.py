from novel_reader.settings import *

DEBUG = False
INSTALLED_APPS = [a for a in INSTALLED_APPS if a != 'debug_toolbar']
MIDDLEWARE = [m for m in MIDDLEWARE if 'debug_toolbar' not in m]
