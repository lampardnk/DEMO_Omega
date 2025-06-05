import json
import os
import re
import tempfile
import subprocess
import shutil
import hashlib
from flask import render_template, request, redirect, url_for, jsonify, flash, session, send_from_directory
from werkzeug.utils import secure_filename
from app import app
from app.forms import QuestionForm, AttachmentForm
import uuid
from decimal import Decimal
import base64
import time

# Custom JSON encoder to handle Decimal objects
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

# LaTeX compilation cache
LATEX_CACHE = {}
CACHE_EXPIRY = 3600  # Cache expiry in seconds (1 hour)

def load_questions(include_deleted=False):
    if os.path.exists(app.config['QUESTIONS_FILE']):
        with open(app.config['QUESTIONS_FILE'], 'r') as f:
            questions = json.load(f)
            if not include_deleted:
                questions = [q for q in questions if not q.get('deleted', False)]
            return questions
    return []

def save_questions(questions):
    os.makedirs(os.path.dirname(app.config['QUESTIONS_FILE']), exist_ok=True)
    with open(app.config['QUESTIONS_FILE'], 'w') as f:
        json.dump(questions, f, indent=4, cls=DecimalEncoder)

def get_all_tags():
    """Get all unique tags from the questions"""
    all_tags = set()
    for question in load_questions():
        for tag in question.get('tags', []):
            all_tags.add(tag)
    return sorted(all_tags)

def get_latex_cache_key(latex_string):
    """Generate a cache key for LaTeX content"""
    return hashlib.md5(latex_string.encode('utf-8')).hexdigest()

def latex_to_svg(latex_string):
    """Convert LaTeX to SVG using command line tools with caching."""
    # Check cache first
    cache_key = get_latex_cache_key(latex_string)
    current_time = time.time()
    
    # Return from cache if available and not expired
    if cache_key in LATEX_CACHE:
        cached_item = LATEX_CACHE[cache_key]
        if current_time - cached_item['timestamp'] < CACHE_EXPIRY:
            return cached_item['svg']
    
    # Not in cache or expired, generate SVG
    svg_data = _generate_latex_svg(latex_string)
    
    # Store in cache
    LATEX_CACHE[cache_key] = {
        'svg': svg_data,
        'timestamp': current_time
    }
    
    # Clean old cache entries
    _clean_latex_cache()
    
    return svg_data

def _clean_latex_cache():
    """Remove expired items from the LaTeX cache"""
    current_time = time.time()
    expired_keys = [k for k, v in LATEX_CACHE.items() 
                   if current_time - v['timestamp'] > CACHE_EXPIRY]
    
    for key in expired_keys:
        del LATEX_CACHE[key]

def _generate_latex_svg(latex_string):
    """Internal function to generate SVG from LaTeX without caching."""
    # Create a temporary directory for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Write the LaTeX content to a temporary file, adding extra newlines for safety
        tex_file = os.path.join(temp_dir, "content.tex")
        with open(tex_file, "w") as f:
            f.write(latex_string + "\n\n")
        
        try:
            # Run pdflatex to create PDF
            result = subprocess.run(
                ["pdflatex", "-shell-escape", "-interaction=nonstopmode", "-output-directory", temp_dir, tex_file],
                check=False,  # Don't raise exception on non-zero exit
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Check if pdflatex succeeded
            if result.returncode != 0:
                # Try to extract the error message from the log
                log_file = os.path.join(temp_dir, "content.log")
                error_message = "LaTeX compilation failed"
                
                if os.path.exists(log_file):
                    with open(log_file, 'r') as f:
                        log_content = f.read()
                        # Extract error message from the log
                        error_patterns = [
                            r'! (.+?)\n',  # Common error pattern
                            r'! LaTeX Error: (.+?)\n',  # LaTeX specific error
                            r'! Package (.+?) Error: (.+?)\n'  # Package error
                        ]
                        
                        for pattern in error_patterns:
                            matches = re.findall(pattern, log_content)
                            if matches:
                                if isinstance(matches[0], tuple):
                                    error_message = ': '.join(matches[0])
                                else:
                                    error_message = matches[0]
                                break
                
                raise subprocess.CalledProcessError(
                    result.returncode, 
                    result.args, 
                    output=result.stdout, 
                    stderr=error_message
                )
            
            # Convert PDF to SVG using pdf2svg
            pdf_file = os.path.join(temp_dir, "content.pdf")
            svg_file = os.path.join(temp_dir, "content.svg")
            
            if os.path.exists(pdf_file):
                svg_result = subprocess.run(
                    ["pdf2svg", pdf_file, svg_file],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                # Read the SVG file
                with open(svg_file, "r") as f:
                    svg_content = f.read()
                
                # Return base64 encoded SVG
                base64_data = base64.b64encode(svg_content.encode()).decode("ascii")
                return f"data:image/svg+xml;base64,{base64_data}"
            else:
                raise FileNotFoundError("PDF file was not created")
            
        except subprocess.CalledProcessError as e:
            # If compilation fails, provide an error message with the actual error
            error_message = f"LaTeX error: {e.stderr}"
            error_svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="500" height="100" viewBox="0 0 500 100">
    <rect width="500" height="100" fill="#f8d7da" stroke="#f5c6cb" stroke-width="1" rx="5" ry="5"/>
    <text x="50%" y="50%" text-anchor="middle" dominant-baseline="middle" font-family="Arial" font-size="14" fill="#721c24">
        {error_message}
    </text>
</svg>'''
            base64_data = base64.b64encode(error_svg.encode()).decode("ascii")
            return f"data:image/svg+xml;base64,{base64_data}"
        except (FileNotFoundError, OSError) as e:
            # If tools are missing or other system errors
            error_message = f"System error: {str(e)}"
            error_svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="500" height="100" viewBox="0 0 500 100">
    <rect width="500" height="100" fill="#f8d7da" stroke="#f5c6cb" stroke-width="1" rx="5" ry="5"/>
    <text x="50%" y="50%" text-anchor="middle" dominant-baseline="middle" font-family="Arial" font-size="14" fill="#721c24">
        {error_message}
    </text>
</svg>'''
            base64_data = base64.b64encode(error_svg.encode()).decode("ascii")
            return f"data:image/svg+xml;base64,{base64_data}"

# New function to ensure a complete LaTeX document
def ensure_complete_latex_document(latex_content):
    """Makes sure the LaTeX content is a complete document by adding preamble and document environment if needed."""
    # Check if it's already a complete document
    if "\\documentclass" in latex_content:
        return latex_content
    
    # Detect what environments are present to add appropriate packages
    packages = ["\\usepackage{amsmath}", "\\usepackage{amssymb}"]
    
    # Add tikz package if needed
    if "\\begin{tikzpicture}" in latex_content:
        packages.append("\\usepackage{tikz}")
    
    # Add circuitikz package if needed
    if "\\begin{circuitikz}" in latex_content:
        packages.append("\\usepackage{circuitikz}")
    
    # Add enumitem if enumerate is used with custom labels
    if "\\begin{enumerate}" in latex_content:
        packages.append("\\usepackage{enumitem}")
        
    # Add geometry package for better margins
    packages.append("\\usepackage{geometry}")
    packages.append("\\geometry{margin=1in}")
    
    # Add preview package for cropping white space
    packages.append("\\usepackage[active,tightpage]{preview}")
    
    # Create a complete document using exam document class
    complete_document = "\\documentclass{exam}\n"
    complete_document += "\n".join(packages) + "\n\n"
    
    # Add preview environment based on what's in the content
    preview_env = "document"  # Default to previewing the whole document
    
    # Check for specific environments to preview
    if "\\begin{questions}" in latex_content:
        preview_env = "questions"
    elif "\\begin{tikzpicture}" in latex_content:
        preview_env = "tikzpicture"
    elif "\\begin{circuitikz}" in latex_content:
        preview_env = "circuitikz"
        
    complete_document += f"\\PreviewEnvironment{{{preview_env}}}\n\n"
    complete_document += "\\begin{document}\n\n"
    
    # For plain math expressions, wrap in questions environment to benefit from preview
    if not any(env in latex_content for env in ["\\begin{questions}", "\\begin{tikzpicture}", "\\begin{circuitikz}"]):
        complete_document += "\\begin{questions}\n\\question\n"
        complete_document += latex_content + "\n"
        complete_document += "\\end{questions}\n"
    else:
        complete_document += latex_content + "\n\n"
        
    complete_document += "\\end{document}"
    
    return complete_document

@app.route('/api/compile-latex', methods=['POST'])
def compile_latex():
    """API endpoint to compile LaTeX to SVG and return the result."""
    try:
        data = request.get_json()
        if not data or 'latex' not in data:
            return jsonify({'success': False, 'error': 'No LaTeX content provided'}), 400
        
        latex_content = data['latex']
        
        # Ensure it's a complete document
        complete_latex = ensure_complete_latex_document(latex_content)
        
        # Compile to SVG (will use cache if available)
        svg_data = latex_to_svg(complete_latex)
        
        return jsonify({
            'success': True,
            'svg': svg_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def save_attachment(file, question_id):
    """Save an uploaded attachment file"""
    attachment_dir = os.path.join(app.config['UPLOAD_FOLDER'], question_id)
    os.makedirs(attachment_dir, exist_ok=True)
    
    # Secure the filename and save the file
    filename = secure_filename(file.filename)
    file_path = os.path.join(attachment_dir, filename)
    file.save(file_path)
    
    # Create attachment info
    attachment = {
        'id': str(uuid.uuid4()),
        'filename': filename,
        'original_filename': file.filename,
        'path': os.path.join(question_id, filename),
        'type': file.content_type
    }
    
    return attachment

@app.route('/')
def index():
    # Check if we should show deleted questions
    show_deleted = request.args.get('show_deleted', 'false').lower() == 'true'
    
    questions = load_questions(include_deleted=show_deleted)
    
    # Get filter tags from request (can be multiple)
    filter_tags = request.args.getlist('tags')
    sort_by = request.args.get('sort', 'newest')
    
    # Filter by multiple tags if specified
    if filter_tags:
        filtered_questions = []
        for question in questions:
            # Check if any of the question's tags match any of the filter tags
            if any(tag in question.get('tags', []) for tag in filter_tags):
                filtered_questions.append(question)
        questions = filtered_questions
    
    # Sort questions
    if sort_by == 'rating_asc':
        questions.sort(key=lambda x: float(x.get('rating', 0)))
    elif sort_by == 'rating_desc':
        questions.sort(key=lambda x: float(x.get('rating', 0)), reverse=True)
    elif sort_by == 'newest':
        questions.sort(key=lambda x: x.get('id', 0), reverse=True)
    
    # Check for any questions that need SVG generation
    updated = False
    for question in questions:
        if not question.get('svg') or question.get('svg_generated') is False:
            question['svg'] = latex_to_svg(ensure_complete_latex_document(question['content']))
            question['svg_generated'] = True
            updated = True
    
    # Save the updated questions if any SVGs were generated
    if updated:
        save_questions(load_questions(include_deleted=True))
    
    # Get all unique tags for the filter dropdown
    all_tags = get_all_tags()
    
    return render_template('index.html', questions=questions, filter_tags=filter_tags, 
                          sort_by=sort_by, all_tags=all_tags, show_deleted=show_deleted)

@app.route('/add_question', methods=['GET', 'POST'])
def add_question():
    form = QuestionForm()
    attachment_form = AttachmentForm()
    
    # Get all existing tags for the dropdown
    all_tags = get_all_tags()
    
    if form.validate_on_submit():
        questions = load_questions(include_deleted=True)
        
        # Parse tags from comma-separated string to list and add selected tags
        input_tags = [tag.strip() for tag in form.tags.data.split(',') if tag.strip()]
        selected_tags = request.form.getlist('selected_tags')
        
        # Combine both sets of tags and remove duplicates
        combined_tags = list(set(input_tags + selected_tags))
        
        # Ensure at least one tag is provided
        if not combined_tags:
            flash('Please provide at least one tag for the question.', 'error')
            return render_template('add_question.html', form=form, attachment_form=attachment_form, all_tags=all_tags)
        
        # Generate unique ID for the question
        question_id = str(uuid.uuid4())
        
        # We'll generate the SVG later when viewing the question
        latex_svg = ''
        
        # Process and save any URL attachments
        urls = request.form.getlist('attachment_url')
        url_attachments = []
        for url in urls:
            if url.strip():
                url_attachments.append({
                    'id': str(uuid.uuid4()),
                    'type': 'url',
                    'url': url.strip(),
                    'description': 'URL Link'
                })
        
        # Create the new question
        new_question = {
            'id': question_id,
            'content': form.content.data,
            'svg': latex_svg,
            'svg_generated': False,  # Flag to indicate SVG needs to be generated
            'rating': float(form.rating.data),  # Convert Decimal to float
            'tags': combined_tags,
            'deleted': False,
            'attachments': url_attachments
        }
        
        # Process file uploads if any
        if 'attachment_file' in request.files:
            files = request.files.getlist('attachment_file')
            file_attachments = []
            
            for file in files:
                if file and file.filename:
                    attachment = save_attachment(file, question_id)
                    file_attachments.append(attachment)
            
            # Add file attachments to question
            new_question['attachments'].extend(file_attachments)
        
        questions.append(new_question)
        save_questions(questions)
        flash('Question added successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('add_question.html', form=form, attachment_form=attachment_form, all_tags=all_tags)

@app.route('/question/<question_id>')
def view_question(question_id):
    questions = load_questions(include_deleted=True)
    question = next((q for q in questions if q.get('id') == question_id), None)
    
    if not question:
        flash('Question not found!', 'error')
        return redirect(url_for('index'))
    
    # Generate SVG if it hasn't been generated yet or if it's flagged for regeneration
    if not question.get('svg') or question.get('svg_generated') is False:
        question['svg'] = latex_to_svg(ensure_complete_latex_document(question['content']))
        question['svg_generated'] = True
        save_questions(questions)
    
    return render_template('view_question.html', question=question)

@app.route('/edit_question/<question_id>', methods=['GET', 'POST'])
def edit_question(question_id):
    questions = load_questions(include_deleted=True)
    question = next((q for q in questions if q.get('id') == question_id), None)
    
    if not question:
        flash('Question not found!', 'error')
        return redirect(url_for('index'))
    
    form = QuestionForm()
    attachment_form = AttachmentForm()
    all_tags = get_all_tags()
    
    if request.method == 'GET':
        # Pre-populate the form with existing question data
        form.content.data = question['content']
        form.rating.data = question['rating']
        form.tags.data = ', '.join(question['tags'])
    
    if form.validate_on_submit():
        # Mark the old question as deleted
        question['deleted'] = True
        
        # Parse tags from comma-separated string to list and add selected tags
        input_tags = [tag.strip() for tag in form.tags.data.split(',') if tag.strip()]
        selected_tags = request.form.getlist('selected_tags')
        
        # Combine both sets of tags and remove duplicates
        combined_tags = list(set(input_tags + selected_tags))
        
        # Ensure at least one tag is provided
        if not combined_tags:
            flash('Please provide at least one tag for the question.', 'error')
            return render_template('edit_question.html', form=form, attachment_form=attachment_form, question=question, all_tags=all_tags)
        
        # Generate unique ID for the new question
        new_question_id = str(uuid.uuid4())
        
        # We'll generate the SVG later when viewing the question to speed up the edit page
        # Initially use the old SVG if available
        latex_svg = question.get('svg', '')
        
        # Get existing attachments to keep
        kept_attachments = []
        for attachment_id in request.form.getlist('keep_attachment'):
            attachment = next((a for a in question.get('attachments', []) if a.get('id') == attachment_id), None)
            if attachment:
                kept_attachments.append(attachment)
                
                # For file attachments, copy to the new question's directory
                if 'path' in attachment:
                    old_path = os.path.join(app.config['UPLOAD_FOLDER'], attachment['path'])
                    new_dir = os.path.join(app.config['UPLOAD_FOLDER'], new_question_id)
                    os.makedirs(new_dir, exist_ok=True)
                    new_path = os.path.join(new_dir, attachment['filename'])
                    shutil.copy2(old_path, new_path)
                    attachment['path'] = os.path.join(new_question_id, attachment['filename'])
        
        # Process and add new URL attachments
        urls = request.form.getlist('attachment_url')
        for url in urls:
            if url.strip():
                kept_attachments.append({
                    'id': str(uuid.uuid4()),
                    'type': 'url',
                    'url': url.strip(),
                    'description': 'URL Link'
                })
        
        # Create a new question with the edited data
        new_question = {
            'id': new_question_id,
            'content': form.content.data,
            'svg': latex_svg,  # Use existing SVG initially
            'svg_generated': False,  # Flag to indicate SVG needs to be generated
            'rating': float(form.rating.data),
            'tags': combined_tags,
            'deleted': False,
            'edited_from': question_id,  # Reference to the original question
            'attachments': kept_attachments
        }
        
        # Process new file uploads if any
        if 'attachment_file' in request.files:
            files = request.files.getlist('attachment_file')
            for file in files:
                if file and file.filename:
                    attachment = save_attachment(file, new_question_id)
                    new_question['attachments'].append(attachment)
        
        questions.append(new_question)
        save_questions(questions)
        flash('Question updated successfully!', 'success')
        return redirect(url_for('view_question', question_id=new_question_id))
    
    return render_template('edit_question.html', form=form, attachment_form=attachment_form, question=question, all_tags=all_tags)

@app.route('/delete_question/<question_id>', methods=['POST'])
def delete_question(question_id):
    questions = load_questions(include_deleted=True)
    question = next((q for q in questions if q.get('id') == question_id), None)
    
    if not question:
        flash('Question not found!', 'error')
    else:
        # Mark the question as deleted instead of removing it
        question['deleted'] = True
        save_questions(questions)
        flash('Question deleted successfully!', 'success')
    
    return redirect(url_for('index'))

@app.route('/download/<question_id>/<attachment_id>')
def download_attachment(question_id, attachment_id):
    questions = load_questions(include_deleted=True)
    question = next((q for q in questions if q.get('id') == question_id), None)
    
    if not question:
        flash('Question not found!', 'error')
        return redirect(url_for('index'))
    
    attachment = next((a for a in question.get('attachments', []) if a.get('id') == attachment_id), None)
    
    if not attachment:
        flash('Attachment not found!', 'error')
        return redirect(url_for('view_question', question_id=question_id))
    
    if attachment.get('type') == 'url':
        # For URL attachments, redirect to the URL
        return redirect(attachment['url'])
    else:
        # For file attachments, serve the file
        attachment_dir = os.path.dirname(os.path.join(app.config['UPLOAD_FOLDER'], attachment['path']))
        filename = os.path.basename(attachment['path'])
        return send_from_directory(attachment_dir, filename, as_attachment=True, 
                                  download_name=attachment['original_filename'])

@app.route('/remove_attachment/<question_id>/<attachment_id>', methods=['POST'])
def remove_attachment(question_id, attachment_id):
    questions = load_questions(include_deleted=True)
    question = next((q for q in questions if q.get('id') == question_id), None)
    
    if not question:
        flash('Question not found!', 'error')
        return redirect(url_for('index'))
    
    # Remove the attachment from the question
    attachments = question.get('attachments', [])
    attachment = next((a for a in attachments if a.get('id') == attachment_id), None)
    
    if attachment:
        attachments.remove(attachment)
        
        # If it's a file attachment, remove the file
        if 'path' in attachment:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], attachment['path'])
            if os.path.exists(file_path):
                os.remove(file_path)
        
        save_questions(questions)
        flash('Attachment removed successfully!', 'success')
    else:
        flash('Attachment not found!', 'error')
    
    return redirect(url_for('view_question', question_id=question_id)) 