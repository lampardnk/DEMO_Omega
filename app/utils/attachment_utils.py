
import uuid
from typing import List, Dict, Any, Optional
from flask import flash
from app.utils.file_manager import FileManager


def process_file_uploads(files, question_id: str, existing_attachments: List[Dict] = None) -> Optional[List[Dict]]:
    """Process file uploads and return attachments or None on error"""
    valid_files = [f for f in files if f and f.filename]

    if not valid_files:
        return []

    # Validate files
    if existing_attachments:
        # Count existing files for validation
        all_files = valid_files + [
            type('obj',
                 (object, ), {'filename': a.get('original_filename', '')})
            for a in existing_attachments
        ]
        is_valid, error_message = FileManager.validate_uploads(all_files)
    else:
        is_valid, error_message = FileManager.validate_uploads(valid_files)

    if not is_valid:
        flash(error_message, 'error')
        return None

    file_attachments = []
    for file in valid_files:
        if FileManager.allowed_file(file.filename):
            attachment = FileManager.save_attachment(file, question_id)
            file_attachments.append(attachment)
        else:
            ext = file.filename.rsplit(
                '.', 1)[1].lower() if '.' in file.filename else 'unknown'
            flash(f'File type {ext} is not allowed', 'error')
            return None

    return file_attachments


def process_kept_attachments(form_data, question: Dict, new_question_id: str) -> List[Dict]:
    """Process attachments to keep from existing question"""
    kept_attachments = []
    for attachment_id in form_data.getlist('keep_attachment'):
        attachment = next((a for a in question.get('attachments', [])
                           if a.get('id') == attachment_id), None)
        if attachment:
            kept_attachments.append(attachment)
            FileManager.copy_attachment(attachment, question['id'],
                                        new_question_id)

    return kept_attachments


def process_url_attachments(urls: List[str]) -> List[Dict]:
    """Process URL attachments from form data"""
    return [{
        'id': str(uuid.uuid4()),
        'type': 'url',
        'url': url.strip(),
        'description': 'URL Link'
    } for url in urls if url.strip()]
