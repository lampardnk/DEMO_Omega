
import uuid
from typing import List, Dict, Any, Callable
from flask import jsonify, request
from app.utils.data_manager import DataManager


def handle_tag_management(load_func: Callable, save_func: Callable, 
                         load_items_func: Callable, save_items_func: Callable):
    """Generic tag management handler"""
    tags = load_func()

    if request.method == 'GET':
        return jsonify(tags)

    elif request.method == 'POST':
        data = request.get_json()
        if not data or 'display_name' not in data:
            return jsonify({
                'success': False,
                'error': 'No display name provided'
            }), 400

        tag_id = data.get('id', data['display_name'].lower().replace(' ', '_'))

        if any(tag['id'] == tag_id for tag in tags):
            return jsonify({
                'success': False,
                'error': 'Tag ID already exists'
            }), 400

        new_tag = {'id': tag_id, 'display_name': data['display_name']}
        tags.append(new_tag)
        save_func(tags)

        return jsonify({'success': True, 'tag': new_tag})

    elif request.method == 'PUT':
        data = request.get_json()
        if not data or 'id' not in data or 'display_name' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required fields'
            }), 400

        tag_to_update = next((tag for tag in tags if tag['id'] == data['id']),
                             None)
        if not tag_to_update:
            return jsonify({'success': False, 'error': 'Tag not found'}), 404

        tag_to_update['display_name'] = data['display_name']
        save_func(tags)

        return jsonify({'success': True, 'tag': tag_to_update})

    elif request.method == 'DELETE':
        data = request.get_json()
        if not data or 'id' not in data:
            return jsonify({
                'success': False,
                'error': 'No tag ID provided'
            }), 400

        tag_to_delete = next((tag for tag in tags if tag['id'] == data['id']),
                             None)
        if not tag_to_delete:
            return jsonify({'success': False, 'error': 'Tag not found'}), 404

        tags.remove(tag_to_delete)
        save_func(tags)

        # Remove tag from items
        items = load_items_func()
        updated = False
        for item in items:
            if 'tags' in item and data['id'] in item['tags']:
                item['tags'].remove(data['id'])
                updated = True

        if updated:
            save_items_func(items)

        return jsonify({'success': True})

    return jsonify({'success': False, 'error': 'Invalid request method'}), 405


def validate_hint_data(data: Dict) -> tuple[bool, str, Dict]:
    """Validate hint data and return validation result, error message, and processed data"""
    if not data or 'text' not in data or 'weight' not in data:
        return False, 'Missing required fields', {}

    hint_text = data['text'].strip()
    word_count = len(hint_text.split())
    if word_count > 50:
        return False, f'Hint text must be 50 words or less (currently {word_count} words)', {}

    try:
        weight = int(data['weight'])
        if weight < 1 or weight > 10:
            return False, 'Weight must be between 1 and 10', {}
    except ValueError:
        return False, 'Weight must be an integer', {}

    return True, '', {'text': hint_text, 'weight': weight}


def create_api_response(success: bool, data: Any = None, error: str = None, status_code: int = 200):
    """Create standardized API response"""
    response_data = {'success': success}
    
    if success and data is not None:
        response_data.update(data)
    elif not success and error:
        response_data['error'] = error
    
    return jsonify(response_data), status_code
