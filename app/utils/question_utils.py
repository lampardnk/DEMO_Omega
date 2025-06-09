
import uuid
import time
from typing import List, Dict, Any, Optional
from flask import flash, request
from app import app
from app.utils.data_manager import DataManager, TagManager
from app.utils.latex_processor import LaTeXProcessor
from app.utils.file_manager import FileManager


def ensure_question_svgs(questions: List[Dict], all_questions: List[Dict]) -> None:
    """Ensure SVGs are generated for questions"""
    updated = False
    for question in questions:
        if not question.get('svg') or question.get('svg_generated') is False:
            try:
                question['svg'] = LaTeXProcessor.latex_to_svg(
                    LaTeXProcessor.ensure_complete_document(
                        question['content']))
                question['svg_generated'] = True
            except Exception as e:
                app.logger.error(
                    f"Error generating SVG for question {question.get('id')}: {str(e)}"
                )
                question['svg'] = '/static/img/latex-placeholder.svg'
                question['svg_generated'] = False
            updated = True

    if updated:
        DataManager.save_questions(all_questions)


def get_filtered_questions(filter_tags: List[str] = None,
                          search_query: str = '',
                          sort_by: str = 'newest') -> List[Dict]:
    """Get filtered and sorted questions with SVGs generated"""
    all_questions = DataManager.load_questions(include_deleted=True)
    questions = [q for q in all_questions if not q.get('deleted', False)]

    ensure_question_svgs(questions, all_questions)

    # Apply filters
    if filter_tags or search_query:
        filtered_questions = []
        for question in questions:
            tags_match = True
            if filter_tags:
                question_tags = question.get('tags', [])
                tags_match = any(tag in question_tags for tag in filter_tags)

            text_match = True
            if search_query:
                search_lower = search_query.lower()
                name = question.get('name', '').lower()
                content = question.get('content', '').lower()
                text_match = search_lower in name or search_lower in content

            if tags_match and text_match:
                filtered_questions.append(question)

        questions = filtered_questions

    # Sort questions
    if sort_by == 'rating_asc':
        questions.sort(key=lambda q: q.get('rating', 0))
    elif sort_by == 'rating_desc':
        questions.sort(key=lambda q: q.get('rating', 0), reverse=True)

    return questions


def generate_question_svg(question: Dict) -> None:
    """Generate SVG for a single question"""
    if not question.get('svg') or question.get('svg_generated') is False:
        try:
            question['svg'] = LaTeXProcessor.latex_to_svg(
                LaTeXProcessor.ensure_complete_document(question['content']))
            question['svg_generated'] = True
        except Exception as e:
            app.logger.error(
                f"Error generating SVG for question {question.get('id')}: {str(e)}"
            )
            question['svg'] = '/static/img/latex-placeholder.svg'
            question['svg_generated'] = False


def create_new_question(form_data: Dict, selected_tag_ids: List[str]) -> Dict:
    """Create a new question from form data"""
    question_id = str(uuid.uuid4())

    # Process URL attachments
    urls = form_data.getlist('attachment_url')
    url_attachments = [{
        'id': str(uuid.uuid4()),
        'type': 'url',
        'url': url.strip(),
        'description': 'URL Link'
    } for url in urls if url.strip()]

    # Process hints
    hints = process_hints_from_form(form_data)

    new_question = {
        'id': question_id,
        'name': form_data.get('name'),
        'content': form_data.get('content'),
        'answer': form_data.get('answer'),
        'svg': '',
        'svg_generated': False,
        'rating': float(form_data.get('rating', 0)),
        'tags': selected_tag_ids,
        'deleted': False,
        'attachments': url_attachments,
        'hints': hints
    }

    return new_question


def process_hints_from_form(form_data) -> List[Dict]:
    """Process hints from form data"""
    hints = []
    hint_index = 0
    while f'hint_text_{hint_index}' in form_data:
        hint_text = form_data.get(f'hint_text_{hint_index}', '').strip()
        hint_weight = form_data.get(f'hint_weight_{hint_index}', '5')

        word_count = len(hint_text.split())
        if hint_text and word_count <= 50:
            try:
                weight = int(hint_weight)
                if 1 <= weight <= 10:
                    hints.append({
                        'id': str(uuid.uuid4()),
                        'text': hint_text,
                        'weight': weight
                    })
            except ValueError:
                pass

        hint_index += 1

    return hints


def process_hint_data(used_hints: List[str], hints: List[Dict]) -> List[Dict]:
    """Process hint data for submissions"""
    hint_positions = {}
    for i, hint in enumerate(hints, 1):
        hint_positions[hint['id']] = i

    hint_data = []
    for hint_id in used_hints:
        if hint_id in hint_positions:
            hint_data.append({
                'id': hint_id,
                'position': hint_positions[hint_id]
            })
        else:
            hint_data.append({'id': hint_id, 'position': 0})

    return hint_data


def create_submission(question_id: str, user_answer: str, correct_answer: str, 
                     quiz_id: str = None, used_hints: List[str] = None) -> Dict:
    """Create a new submission"""
    used_hints = used_hints or []
    questions = DataManager.load_questions(include_deleted=True)
    question = next((q for q in questions if q.get('id') == question_id), None)
    
    hint_data = process_hint_data(used_hints, question.get('hints', []))
    is_correct = user_answer.lower() == correct_answer.lower()

    return {
        'id': str(uuid.uuid4()),
        'question_id': question_id,
        'user_answer': user_answer,
        'outcome': 'Correct' if is_correct else 'Incorrect',
        'verdict': 'Your answer is correct.' if is_correct else 'Your answer is incorrect. Please try again.',
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'used_hints': used_hints,
        'hint_data': hint_data,
        'quiz_id': quiz_id
    }
