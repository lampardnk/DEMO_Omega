
import json
import os
from typing import List, Dict, Any, Optional
from app import app
from decimal import Decimal


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle Decimal objects"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


class DataManager:
    """Centralized data management for all JSON files"""
    
    @staticmethod
    def _ensure_directory(file_path: str) -> None:
        """Ensure the directory for a file exists"""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    @staticmethod
    def _load_json(file_path: str, default: Any = None) -> Any:
        """Generic JSON file loader with default fallback"""
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
        return default if default is not None else []
    
    @staticmethod
    def _save_json(file_path: str, data: Any) -> None:
        """Generic JSON file saver"""
        DataManager._ensure_directory(file_path)
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4, cls=DecimalEncoder)
    
    # Questions
    @staticmethod
    def load_questions(include_deleted: bool = False) -> List[Dict]:
        """Load questions from JSON file"""
        questions = DataManager._load_json(app.config['QUESTIONS_FILE'])
        if not include_deleted:
            questions = [q for q in questions if not q.get('deleted', False)]
        return questions
    
    @staticmethod
    def save_questions(questions: List[Dict]) -> None:
        """Save questions to JSON file"""
        DataManager._save_json(app.config['QUESTIONS_FILE'], questions)
    
    # Submissions
    @staticmethod
    def load_submissions() -> List[Dict]:
        """Load submissions from JSON file"""
        return DataManager._load_json(app.config['SUBMISSIONS_FILE'])
    
    @staticmethod
    def save_submissions(submissions: List[Dict]) -> None:
        """Save submissions to JSON file"""
        DataManager._save_json(app.config['SUBMISSIONS_FILE'], submissions)
    
    # Quizzes
    @staticmethod
    def load_quizzes() -> List[Dict]:
        """Load quizzes from JSON file"""
        return DataManager._load_json(app.config['QUIZZES_FILE'])
    
    @staticmethod
    def save_quizzes(quizzes: List[Dict]) -> None:
        """Save quizzes to JSON file"""
        DataManager._save_json(app.config['QUIZZES_FILE'], quizzes)
    
    # Tags
    @staticmethod
    def load_tags() -> List[Dict]:
        """Load tags from JSON file"""
        return DataManager._load_json(app.config['TAGS_FILE'])
    
    @staticmethod
    def save_tags(tags: List[Dict]) -> None:
        """Save tags to JSON file"""
        DataManager._save_json(app.config['TAGS_FILE'], tags)
    
    # Quiz Tags
    @staticmethod
    def load_quiz_tags() -> List[Dict]:
        """Load quiz tags from JSON file"""
        return DataManager._load_json(app.config['QUIZ_TAGS_FILE'])
    
    @staticmethod
    def save_quiz_tags(tags: List[Dict]) -> None:
        """Save quiz tags to JSON file"""
        DataManager._save_json(app.config['QUIZ_TAGS_FILE'], tags)


class TagManager:
    """Manager for tag-related operations"""
    
    @staticmethod
    def get_all_tags() -> List[Dict]:
        """Get all tags with their IDs and display names"""
        return DataManager.load_tags()
    
    @staticmethod
    def get_tag_by_id(tag_id: str) -> Optional[Dict]:
        """Get a tag by its ID"""
        tags = DataManager.load_tags()
        return next((tag for tag in tags if tag['id'] == tag_id), None)
    
    @staticmethod
    def get_all_quiz_tags() -> List[Dict]:
        """Get all quiz tags with their IDs and display names"""
        return DataManager.load_quiz_tags()
    
    @staticmethod
    def get_quiz_tag_by_id(tag_id: str) -> Optional[Dict]:
        """Get a quiz tag by its ID"""
        tags = DataManager.load_quiz_tags()
        return next((tag for tag in tags if tag['id'] == tag_id), None)
    
    @staticmethod
    def get_tag_display_name(tag_id: str) -> str:
        """Get the display name for a tag ID"""
        tag = TagManager.get_tag_by_id(tag_id)
        return tag['display_name'] if tag else tag_id
    
    @staticmethod
    def get_quiz_tag_display_name(tag_id: str) -> str:
        """Get the display name for a quiz tag ID"""
        tag = TagManager.get_quiz_tag_by_id(tag_id)
        return tag['display_name'] if tag else tag_id
