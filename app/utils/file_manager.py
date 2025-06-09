
import os
import shutil
import uuid
import mimetypes
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from typing import List, Tuple, Dict, Any
from app import app


class FileManager:
    """Handle file uploads and attachments"""
    
    @staticmethod
    def allowed_file(filename: str) -> bool:
        """Check if the file extension is allowed"""
        return ('.' in filename and 
                filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS'])
    
    @staticmethod
    def validate_uploads(files: List[FileStorage]) -> Tuple[bool, str]:
        """Validate file uploads against limits"""
        if len(files) > 4:
            return False, "Maximum 4 files can be uploaded"
        
        pdf_count = video_count = image_count = total_size = 0
        
        for file in files:
            if not file or not file.filename:
                continue
            
            extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
            
            if not extension or extension not in app.config['ALLOWED_EXTENSIONS']:
                return False, f"File type {extension} is not allowed"
            
            # Check file size
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            total_size += file_size
            
            # Count by type
            if extension == 'pdf':
                pdf_count += 1
            elif extension in ['webm', 'mp4']:
                video_count += 1
            elif extension in ['png', 'jpg', 'jpeg']:
                image_count += 1
        
        # Validate counts
        if pdf_count > 1:
            return False, "Only 1 PDF file is allowed"
        if video_count > 1:
            return False, "Only 1 video file (webm or mp4) is allowed"
        if image_count > 1:
            return False, "Only 1 image file (png, jpg, or jpeg) is allowed"
        if total_size > app.config['MAX_CONTENT_LENGTH']:
            return False, f"Total file size must be less than {app.config['MAX_CONTENT_LENGTH'] // (1024 * 1024)}MB"
        
        return True, ""
    
    @staticmethod
    def save_attachment(file: FileStorage, question_id: str) -> Dict[str, Any]:
        """Save an uploaded attachment file"""
        attachment_dir = os.path.join(app.config['UPLOAD_FOLDER'], question_id)
        os.makedirs(attachment_dir, exist_ok=True)
        
        filename = secure_filename(file.filename)
        file_path = os.path.join(attachment_dir, filename)
        file.save(file_path)
        
        extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        # Determine file category
        file_category = 'other'
        if extension in app.config['VIEWABLE_EXTENSIONS']:
            if extension == 'pdf':
                file_category = 'pdf'
            elif extension in ['webm', 'mp4']:
                file_category = 'video'
            elif extension in ['png', 'jpg', 'jpeg']:
                file_category = 'image'
        elif extension in app.config['DOWNLOADABLE_EXTENSIONS']:
            file_category = 'document'
        
        mime_type = file.content_type or mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        
        return {
            'id': str(uuid.uuid4()),
            'filename': filename,
            'original_filename': file.filename,
            'path': os.path.join(question_id, filename),
            'type': mime_type,
            'file_type': extension,
            'category': file_category
        }
    
    @staticmethod
    def copy_attachment(attachment: Dict[str, Any], old_question_id: str, new_question_id: str) -> None:
        """Copy attachment from old question to new question"""
        if 'path' in attachment:
            old_path = os.path.join(app.config['UPLOAD_FOLDER'], attachment['path'])
            new_dir = os.path.join(app.config['UPLOAD_FOLDER'], new_question_id)
            os.makedirs(new_dir, exist_ok=True)
            new_path = os.path.join(new_dir, attachment['filename'])
            shutil.copy2(old_path, new_path)
            attachment['path'] = os.path.join(new_question_id, attachment['filename'])
    
    @staticmethod
    def remove_attachment_file(attachment: Dict[str, Any]) -> None:
        """Remove attachment file from filesystem"""
        if 'path' in attachment:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], attachment['path'])
            if os.path.exists(file_path):
                os.remove(file_path)
