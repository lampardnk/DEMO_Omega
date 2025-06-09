
import uuid
import time
from typing import List, Dict, Any, Optional
from flask import flash
from app.utils.data_manager import DataManager, TagManager


def get_filtered_quizzes(search_query: str = '', filter_tags: List[str] = None, 
                        sort_by: str = 'newest', show_deleted: bool = False) -> List[Dict]:
    """Get filtered and sorted quizzes"""
    all_quizzes = DataManager.load_quizzes()
    filtered_quizzes = all_quizzes

    # Apply filters
    if search_query:
        filtered_quizzes = [
            q for q in filtered_quizzes
            if search_query.lower() in q.get('name', '').lower()
        ]

    if filter_tags:
        filtered_quizzes = [
            q for q in filtered_quizzes
            if set(filter_tags).intersection(set(q.get('tags', [])))
        ]

    if not show_deleted:
        filtered_quizzes = [
            q for q in filtered_quizzes if not q.get('deleted', False)
        ]

    # Sort quizzes
    if sort_by == 'name_asc':
        filtered_quizzes = sorted(filtered_quizzes,
                                  key=lambda q: q.get('name', '').lower())
    elif sort_by == 'name_desc':
        filtered_quizzes = sorted(filtered_quizzes,
                                  key=lambda q: q.get('name', '').lower(),
                                  reverse=True)
    elif sort_by == 'questions_asc':
        filtered_quizzes = sorted(filtered_quizzes,
                                  key=lambda q: len(q.get('question_ids', [])))
    elif sort_by == 'questions_desc':
        filtered_quizzes = sorted(filtered_quizzes,
                                  key=lambda q: len(q.get('question_ids', [])),
                                  reverse=True)

    return filtered_quizzes


def create_new_quiz(name: str, selected_tags: List[str], question_ids: List[str]) -> Dict:
    """Create a new quiz"""
    return {
        'id': str(uuid.uuid4()),
        'name': name,
        'tags': selected_tags,
        'question_ids': question_ids,
        'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'deleted': False
    }


def get_quiz_progress(quiz_id: str, quiz_questions: List[Dict]) -> Dict:
    """Calculate quiz progress for a user"""
    all_submissions = DataManager.load_submissions()
    correct_submissions = [
        s for s in all_submissions
        if s.get('outcome') == 'Correct' and s.get('quiz_id') == quiz_id
    ]
    completed_question_ids = set(s['question_id'] for s in correct_submissions)

    total_questions = len(quiz_questions)
    completed_count = sum(1 for q in quiz_questions
                          if q['id'] in completed_question_ids)
    progress = int((completed_count / total_questions) *
                   100) if total_questions > 0 else 0

    return {
        'total_questions': total_questions,
        'completed_count': completed_count,
        'progress': progress,
        'completed_question_ids': completed_question_ids
    }


def validate_quiz_form(name: str, question_ids: List[str]) -> bool:
    """Validate quiz form data"""
    if not name.strip():
        flash('Quiz name is required!', 'error')
        return False

    if not question_ids:
        flash('Please select at least one question for the quiz!', 'error')
        return False

    return True
