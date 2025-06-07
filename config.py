import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))
 
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    QUESTIONS_FILE = os.path.join(basedir, 'app/data/questions.json')
    SUBMISSIONS_FILE = os.path.join(basedir, 'app/data/submissions.json')
    TAGS_FILE = os.path.join(basedir, 'app/data/tags.json')
    UPLOAD_FOLDER = os.path.join(basedir, 'app/uploads')
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100 MB max upload size
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'webm', 'mp4', 'docx', 'xlsx', 'pptx'}
    # File type categories for validation
    VIEWABLE_EXTENSIONS = {'pdf', 'webm', 'mp4', 'png', 'jpg', 'jpeg'}
    DOWNLOADABLE_EXTENSIONS = {'docx', 'xlsx', 'pptx'}