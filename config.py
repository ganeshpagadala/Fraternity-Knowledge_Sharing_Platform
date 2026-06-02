import os

BASE_DIR           = os.path.dirname(__file__)
DATABASE_PATH      = os.path.join(BASE_DIR, 'fraternity.db')

APP_NAME           = 'Fraternity'
SECRET_KEY         = os.environ.get('SECRET_KEY', 'Fr@t3rn!ty_S3cr3t_2024')
UPLOAD_FOLDER      = os.path.join(BASE_DIR, 'static', 'uploads')
MAX_CONTENT_LENGTH = 100 * 1024 * 1024   # 100 MB
MAX_MEDIA_FILES    = 4

ALLOWED_IMAGE_EXTENSIONS = {'png','jpg','jpeg','gif','webp'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4','webm','mov','avi'}
ALLOWED_FILE_EXTENSIONS  = {'pdf','doc','docx','txt','zip'}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS | ALLOWED_FILE_EXTENSIONS

SENDER_EMAIL  = os.environ.get('SENDER_EMAIL',  'dantavaidya@gmail.com')
EMAIL_PASSKEY = os.environ.get('EMAIL_PASSKEY', 'fpng oeai qyqo jlcd')

FIELD_CATEGORIES = [
    'Chartered Accountant','Lawyer','Doctor','Engineer',
    'Architect','Company Secretary','Cost Accountant',
    'Technology','Finance','Education','General'
]
