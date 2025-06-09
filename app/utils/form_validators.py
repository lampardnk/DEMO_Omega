
from typing import List, Tuple
from flask import flash


def validate_question_form(selected_tag_ids: List[str]) -> bool:
    """Validate question form data"""
    if not selected_tag_ids:
        flash('Please select at least one tag for the question.', 'error')
        return False
    return True


def validate_required_field(value: str, field_name: str, flash_error: bool = True) -> bool:
    """Validate that a required field is not empty"""
    if not value or not value.strip():
        if flash_error:
            flash(f'{field_name} is required!', 'error')
        return False
    return True


def validate_list_not_empty(items: List, field_name: str, flash_error: bool = True) -> bool:
    """Validate that a list is not empty"""
    if not items:
        if flash_error:
            flash(f'Please select at least one {field_name}!', 'error')
        return False
    return True
