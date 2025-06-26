"""
WSGI config for mspr2_cofrap project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mspr2_cofrap.settings')

application = get_wsgi_application() 