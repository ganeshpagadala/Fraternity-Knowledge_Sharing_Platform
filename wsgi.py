import sys
import os

# Add your project directory to the sys.path
project_home = os.path.dirname(os.path.abspath(__file__))
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Import and initialize
from database.tables import create_tables
import app as application_module

# Create tables and upload dirs on startup
with application_module.app.app_context():
    create_tables()
    for sub in ('media', 'avatars', 'covers'):
        os.makedirs(os.path.join(application_module.app.config['UPLOAD_FOLDER'], sub), exist_ok=True)

# This is what PythonAnywhere's WSGI server looks for
application = application_module.app
