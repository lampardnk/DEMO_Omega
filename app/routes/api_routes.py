
import uuid
from flask import jsonify, request
from app import app
from app.utils.data_manager import DataManager
from app.utils.latex_processor import LaTeXProcessor
from app.utils.api_utils import handle_tag_management, validate_hint_data, create_api_response


@app.route('/api/compile-latex', methods=['POST'])
def compile_latex():
    """API endpoint to compile LaTeX to SVG and return the result"""
    try:
        data = request.get_json()
        if not data or 'latex' not in data:
            return create_api_response(False, error='No LaTeX content provided', status_code=400)

        latex_content = data['latex']
        complete_latex = LaTeXProcessor.ensure_complete_document(latex_content)
        svg_data = LaTeXProcessor.latex_to_svg(complete_latex)

        return create_api_response(True, {'svg': svg_data})
    except Exception as e:
        return create_api_response(False, error=str(e), status_code=500)


@app.route('/api/tags', methods=['GET', 'POST', 'PUT', 'DELETE'])
def manage_tags():
    """API endpoint to manage tags"""
    return handle_tag_management(DataManager.load_tags, DataManager.save_tags,
                                  DataManager.load_questions, DataManager.save_questions)


@app.route('/api/quiz_tags', methods=['GET', 'POST', 'PUT', 'DELETE'])
def manage_quiz_tags():
    """API endpoint to manage quiz tags"""
    return handle_tag_management(DataManager.load_quiz_tags,
                                  DataManager.save_quiz_tags,
                                  DataManager.load_quizzes,
                                  DataManager.save_quizzes)


@app.route('/api/questions/<question_id>/hints', methods=['POST'])
def add_hint(question_id):
    """API endpoint to add a hint to a question"""
    try:
        data = request.get_json()
        is_valid, error_msg, processed_data = validate_hint_data(data)
        
        if not is_valid:
            return create_api_response(False, error=error_msg, status_code=400)

        questions = DataManager.load_questions(include_deleted=True)
        question = next((q for q in questions if q.get('id') == question_id), None)

        if not question:
            return create_api_response(False, error='Question not found', status_code=404)

        new_hint = {
            'id': str(uuid.uuid4()),
            'text': processed_data['text'],
            'weight': processed_data['weight']
        }

        if 'hints' not in question:
            question['hints'] = []
        question['hints'].append(new_hint)
        DataManager.save_questions(questions)

        return create_api_response(True, {'hint': new_hint})
    except Exception as e:
        return create_api_response(False, error=str(e), status_code=500)


@app.route('/api/questions/<question_id>/hints/<hint_id>', methods=['PUT'])
def update_hint(question_id, hint_id):
    """API endpoint to update a hint"""
    try:
        data = request.get_json()
        if not data or ('text' not in data and 'weight' not in data):
            return create_api_response(False, error='Missing required fields', status_code=400)

        questions = DataManager.load_questions(include_deleted=True)
        question = next((q for q in questions if q.get('id') == question_id), None)

        if not question:
            return create_api_response(False, error='Question not found', status_code=404)

        hint = next((h for h in question.get('hints', []) if h.get('id') == hint_id), None)
        if not hint:
            return create_api_response(False, error='Hint not found', status_code=404)

        # Validate and update text if provided
        if 'text' in data:
            hint_text = data['text'].strip()
            word_count = len(hint_text.split())
            if word_count > 50:
                return create_api_response(
                    False, 
                    error=f'Hint text must be 50 words or less (currently {word_count} words)',
                    status_code=400
                )
            hint['text'] = hint_text

        # Validate and update weight if provided
        if 'weight' in data:
            try:
                weight = int(data['weight'])
                if weight < 1 or weight > 10:
                    return create_api_response(False, error='Weight must be between 1 and 10', status_code=400)
                hint['weight'] = weight
            except ValueError:
                return create_api_response(False, error='Weight must be an integer', status_code=400)

        DataManager.save_questions(questions)
        return create_api_response(True, {'hint': hint})
    except Exception as e:
        return create_api_response(False, error=str(e), status_code=500)


@app.route('/api/questions/<question_id>/hints/<hint_id>', methods=['DELETE'])
def delete_hint(question_id, hint_id):
    """API endpoint to delete a hint"""
    try:
        questions = DataManager.load_questions(include_deleted=True)
        question = next((q for q in questions if q.get('id') == question_id), None)

        if not question:
            return create_api_response(False, error='Question not found', status_code=404)

        hint = next((h for h in question.get('hints', []) if h.get('id') == hint_id), None)
        if not hint:
            return create_api_response(False, error='Hint not found', status_code=404)

        question['hints'].remove(hint)
        DataManager.save_questions(questions)
        return create_api_response(True)
    except Exception as e:
        return create_api_response(False, error=str(e), status_code=500)
