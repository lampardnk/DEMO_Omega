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
import mimetypes
from app.data_loader import load_user_data, filter_data_by_timerange
from app.chart_utils import create_activity_chart, create_grades_chart

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

def load_submissions():
    if os.path.exists(app.config['SUBMISSIONS_FILE']):
        with open(app.config['SUBMISSIONS_FILE'], 'r') as f:
            return json.load(f)
    return []

def save_submissions(submissions):
    os.makedirs(os.path.dirname(app.config['SUBMISSIONS_FILE']), exist_ok=True)
    with open(app.config['SUBMISSIONS_FILE'], 'w') as f:
        json.dump(submissions, f, indent=4)

def load_quizzes():
    if os.path.exists(app.config['QUIZZES_FILE']):
        with open(app.config['QUIZZES_FILE'], 'r') as f:
            return json.load(f)
    return []

def save_quizzes(quizzes):
    os.makedirs(os.path.dirname(app.config['QUIZZES_FILE']), exist_ok=True)
    with open(app.config['QUIZZES_FILE'], 'w') as f:
        json.dump(quizzes, f, indent=4)

def load_tags():
    """Load tags from the tags file"""
    if os.path.exists(app.config['TAGS_FILE']):
        with open(app.config['TAGS_FILE'], 'r') as f:
            return json.load(f)
    return []

def save_tags(tags):
    """Save tags to the tags file"""
    os.makedirs(os.path.dirname(app.config['TAGS_FILE']), exist_ok=True)
    with open(app.config['TAGS_FILE'], 'w') as f:
        json.dump(tags, f, indent=4)

def load_quiz_tags():
    """Load quiz tags from the quiz tags file"""
    if os.path.exists(app.config['QUIZ_TAGS_FILE']):
        with open(app.config['QUIZ_TAGS_FILE'], 'r') as f:
            return json.load(f)
    return []

def save_quiz_tags(tags):
    """Save quiz tags to the quiz tags file"""
    os.makedirs(os.path.dirname(app.config['QUIZ_TAGS_FILE']), exist_ok=True)
    with open(app.config['QUIZ_TAGS_FILE'], 'w') as f:
        json.dump(tags, f, indent=4)

def get_all_tags():
    """Get all tags with their IDs and display names"""
    return load_tags()

def get_tag_by_id(tag_id):
    """Get a tag by its ID"""
    tags = load_tags()
    for tag in tags:
        if tag['id'] == tag_id:
            return tag
    return None

def get_all_quiz_tags():
    """Get all quiz tags with their IDs and display names"""
    return load_quiz_tags()

def get_quiz_tag_by_id(tag_id):
    """Get a quiz tag by its ID"""
    tags = load_quiz_tags()
    for tag in tags:
        if tag['id'] == tag_id:
            return tag
    return None

def get_tag_display_name(tag_id):
    """Get the display name for a tag ID"""
    tag = get_tag_by_id(tag_id)
    return tag['display_name'] if tag else tag_id

def get_quiz_tag_display_name(tag_id):
    """Get the display name for a quiz tag ID"""
    tag = get_quiz_tag_by_id(tag_id)
    return tag['display_name'] if tag else tag_id

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
    
    # Get file extension
    extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    # Determine file type category
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
    
    # Get mime type
    mime_type = file.content_type or mimetypes.guess_type(filename)[0] or 'application/octet-stream'
    
    # Create attachment info
    attachment = {
        'id': str(uuid.uuid4()),
        'filename': filename,
        'original_filename': file.filename,
        'path': os.path.join(question_id, filename),
        'type': mime_type,
        'file_type': extension,
        'category': file_category
    }
    
    return attachment

@app.route('/')
def index():
    # Redirect to question bank page instead of about page
    return redirect(url_for('questionbank'))

@app.route('/questionbank')
def questionbank():
    # Check if we should show deleted questions
    show_deleted = request.args.get('show_deleted', 'false').lower() == 'true'
    
    # Get filter tags from request (can be multiple)
    filter_tags = request.args.getlist('tags')
    sort_by = request.args.get('sort', 'newest')
    
    # Get search query if any
    search_query = request.args.get('search', '').strip().lower()
    
    # Load questions from the JSON file
    questions = load_questions(include_deleted=show_deleted)
    
    # Filter by multiple tags if specified
    if filter_tags:
        filtered_questions = []
        for question in questions:
            # Check if any of the question's tags match any of the filter tags
            if any(tag in question.get('tags', []) for tag in filter_tags):
                filtered_questions.append(question)
        questions = filtered_questions
    
    # Filter by search query if specified
    if search_query:
        search_results = []
        for question in questions:
            # Check if search query is in name or content
            name = question.get('name', '').lower()
            content = question.get('content', '').lower()
            
            if search_query in name or search_query in content:
                search_results.append(question)
        questions = search_results
    
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
            try:
                question['svg'] = latex_to_svg(ensure_complete_latex_document(question['content']))
                question['svg_generated'] = True
            except Exception as e:
                # If LaTeX compilation fails, use a placeholder image
                app.logger.error(f"Error generating SVG for question {question.get('id')}: {str(e)}")
                question['svg'] = '/static/img/latex-placeholder.svg'
                question['svg_generated'] = False
            updated = True
    
    # Save the updated questions if any SVGs were generated
    if updated:
        save_questions(load_questions(include_deleted=True))
    
    # Get all tags for the filter dropdown
    all_tags = get_all_tags()
    
    return render_template('index.html', questions=questions, filter_tags=filter_tags, 
                          sort_by=sort_by, all_tags=all_tags, show_deleted=show_deleted,
                          search_query=search_query)

@app.route('/quizzes')
def quizzes():
    search_query = request.args.get('search', '').strip().lower()
    filter_tags = request.args.getlist('tags')
    sort_by = request.args.get('sort', 'newest')
    show_deleted = request.args.get('show_deleted') == 'true'
    
    # Load all quizzes
    all_quizzes = load_quizzes()
    
    # Filter by search query if provided
    filtered_quizzes = all_quizzes
    if search_query:
        filtered_quizzes = [q for q in filtered_quizzes if search_query in q.get('name', '').lower()]
    
    # Filter by tags if selected
    if filter_tags:
        filtered_quizzes = [q for q in filtered_quizzes if set(filter_tags).intersection(set(q.get('tags', [])))]
    
    # Filter deleted quizzes
    if not show_deleted:
        filtered_quizzes = [q for q in filtered_quizzes if not q.get('deleted', False)]
    
    # Sort the quizzes
    if sort_by == 'name_asc':
        filtered_quizzes = sorted(filtered_quizzes, key=lambda q: q.get('name', '').lower())
    elif sort_by == 'name_desc':
        filtered_quizzes = sorted(filtered_quizzes, key=lambda q: q.get('name', '').lower(), reverse=True)
    elif sort_by == 'questions_asc':
        filtered_quizzes = sorted(filtered_quizzes, key=lambda q: len(q.get('question_ids', [])))
    elif sort_by == 'questions_desc':
        filtered_quizzes = sorted(filtered_quizzes, key=lambda q: len(q.get('question_ids', [])), reverse=True)
    else:  # Default is 'newest' which is the default order (no sorting needed)
        pass
    
    # Get all quiz tags for the filter dropdown
    all_quiz_tags = get_all_quiz_tags()
    
    return render_template('quizzes.html', 
                          quizzes=filtered_quizzes, 
                          search_query=search_query,
                          filter_tags=filter_tags,
                          all_quiz_tags=all_quiz_tags,
                          sort_by=sort_by,
                          show_deleted=show_deleted)

@app.route('/quizzes/new', methods=['GET', 'POST'])
def create_quiz():
    quiz_tags = get_all_quiz_tags()
    all_tags = get_all_tags()
    
    # Get filter parameters from request
    filter_tags = request.args.getlist('filter_tags') or []
    search_query = request.args.get('search_query', '')
    sort_by = request.args.get('sort_by', 'newest')
    quiz_name = request.args.get('quiz_name', '')
    selected_quiz_tags = request.args.getlist('selected_tags') or []
    
    # Load all questions, including deleted ones for admin viewing
    all_questions = load_questions(include_deleted=True)
    
    # Filter out deleted questions for display by default
    questions = [q for q in all_questions if not q.get('deleted', False)]
    
    # Ensure SVG is generated for all questions
    for question in questions:
        if not question.get('svg') or question.get('svg_generated') is False:
            try:
                question['svg'] = latex_to_svg(ensure_complete_latex_document(question['content']))
                question['svg_generated'] = True
            except Exception as e:
                # If LaTeX compilation fails, use a placeholder image
                app.logger.error(f"Error generating SVG for question {question.get('id')}: {str(e)}")
                question['svg'] = '/static/img/latex-placeholder.svg'
                question['svg_generated'] = False
    
    # Save questions with generated SVGs
    save_questions(all_questions)
    
    # Apply search and tag filters if provided
    if search_query or filter_tags:
        filtered_questions = []
        for question in questions:
            # Check for tag match if tag filter is applied
            tags_match = True
            if filter_tags:
                question_tags = question.get('tags', [])
                # Ensure at least one selected tag is in the question's tags
                tags_match = any(tag in question_tags for tag in filter_tags)
            
            # Check for text match if search query is provided
            text_match = True
            if search_query:
                search_lower = search_query.lower()
                name = question.get('name', '').lower()
                content = question.get('content', '').lower()
                
                text_match = search_lower in name or search_lower in content
            
            # Add question if it matches both tag and text criteria
            if tags_match and text_match:
                filtered_questions.append(question)
        
        questions = filtered_questions
    
    # Sort questions based on sort_by parameter
    if sort_by == 'rating_asc':
        questions.sort(key=lambda q: q.get('rating', 0))
    elif sort_by == 'rating_desc':
        questions.sort(key=lambda q: q.get('rating', 0), reverse=True)
    # For 'newest', no sorting needed as it's the default order
    
    if request.method == 'POST':
        name = request.form.get('quiz_name', '').strip()
        selected_tags = request.form.getlist('selected_tags')
        question_ids = request.form.getlist('question_ids')
        
        if not name:
            flash('Quiz name is required!', 'error')
            return render_template('create_quiz.html', 
                                  questions=questions, 
                                  all_quiz_tags=quiz_tags,
                                  all_tags=all_tags,
                                  filter_tags=filter_tags,
                                  search_query=search_query,
                                  sort_by=sort_by)
        
        if not question_ids:
            flash('Please select at least one question for the quiz!', 'error')
            return render_template('create_quiz.html', 
                                  questions=questions, 
                                  all_quiz_tags=quiz_tags,
                                  all_tags=all_tags,
                                  filter_tags=filter_tags,
                                  search_query=search_query,
                                  sort_by=sort_by)
        
        quizzes = load_quizzes()
        new_quiz = {
            'id': str(uuid.uuid4()),
            'name': name,
            'tags': selected_tags,
            'question_ids': question_ids,
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'deleted': False
        }
        quizzes.append(new_quiz)
        save_quizzes(quizzes)
        
        flash('Quiz created successfully!', 'success')
        return redirect(url_for('quizzes'))
    
    # For GET requests or if form validation fails
    return render_template('create_quiz.html', 
                          questions=questions, 
                          all_quiz_tags=quiz_tags,
                          all_tags=all_tags,
                          filter_tags=filter_tags,
                          search_query=search_query,
                          sort_by=sort_by)

@app.route('/quizzes/<quiz_id>/edit', methods=['GET', 'POST'])
def edit_quiz(quiz_id):
    quizzes = load_quizzes()
    quiz = next((q for q in quizzes if q.get('id') == quiz_id), None)
    
    if not quiz:
        flash('Quiz not found!', 'error')
        return redirect(url_for('quizzes'))
    
    if quiz.get('deleted'):
        flash('Cannot edit a deleted quiz!', 'error')
        return redirect(url_for('quizzes'))
    
    all_tags = get_all_tags()
    all_quiz_tags = get_all_quiz_tags()
    all_questions = load_questions(include_deleted=True)
    
    # Filter out deleted questions for display
    questions = [q for q in all_questions if not q.get('deleted', False)]
    
    # Ensure SVG is generated for all questions
    for question in questions:
        if not question.get('svg') or question.get('svg_generated') is False:
            try:
                question['svg'] = latex_to_svg(ensure_complete_latex_document(question['content']))
                question['svg_generated'] = True
            except Exception as e:
                # If LaTeX compilation fails, use a placeholder image
                app.logger.error(f"Error generating SVG for question {question.get('id')}: {str(e)}")
                question['svg'] = '/static/img/latex-placeholder.svg'
                question['svg_generated'] = False
    
    # Save questions with generated SVGs
    save_questions(all_questions)
    
    if request.method == 'POST':
        name = request.form.get('quiz_name', '').strip()
        selected_tags = request.form.getlist('selected_tags')
        question_ids = request.form.getlist('question_ids')
        
        if not name:
            flash('Quiz name is required!', 'error')
            return render_template('create_quiz.html', 
                                  quiz=quiz,
                                  questions=questions, 
                                  all_quiz_tags=all_quiz_tags,
                                  all_tags=all_tags)
        
        if not question_ids:
            flash('Please select at least one question for the quiz!', 'error')
            return render_template('create_quiz.html', 
                                  quiz=quiz,
                                  questions=questions, 
                                  all_quiz_tags=all_quiz_tags,
                                  all_tags=all_tags)
        
        # Update the quiz
        quiz['name'] = name
        quiz['tags'] = selected_tags
        quiz['question_ids'] = question_ids
        
        save_quizzes(quizzes)
        flash('Quiz updated successfully!', 'success')
        return redirect(url_for('quizzes'))
    
    return render_template('create_quiz.html', 
                          quiz=quiz, 
                          questions=questions, 
                          all_quiz_tags=all_quiz_tags,
                          all_tags=all_tags)

@app.route('/quizzes/<quiz_id>/attempt')
def attempt_quiz(quiz_id):
    quizzes = load_quizzes()
    quiz = next((q for q in quizzes if q['id'] == quiz_id), None)

    if not quiz:
        flash('Quiz not found.', 'danger')
        return redirect(url_for('quizzes'))
        
    if quiz.get('deleted', False):
        flash('This quiz has been deleted and cannot be attempted.', 'danger')
        return redirect(url_for('quizzes'))

    all_questions = load_questions(include_deleted=True)
    quiz_questions = [q for q in all_questions if q['id'] in quiz['question_ids']]
    
    # Ensure svgs are generated
    for question in quiz_questions:
        if not question.get('svg') or question.get('svg_generated') is False:
            try:
                question['svg'] = latex_to_svg(ensure_complete_latex_document(question['content']))
                question['svg_generated'] = True
            except Exception as e:
                # If LaTeX compilation fails, use a placeholder image
                app.logger.error(f"Error generating SVG for question {question.get('id')}: {str(e)}")
                question['svg'] = '/static/img/latex-placeholder.svg'
                question['svg_generated'] = False
    save_questions(all_questions)
    
    # Calculate progress - only count questions completed in this specific quiz
    all_submissions = load_submissions()
    
    # Get all correct submissions for this quiz
    correct_submissions = [
        s for s in all_submissions 
        if s.get('outcome') == 'Correct' and s.get('quiz_id') == quiz_id
    ]
    
    # Get unique question IDs that have been correctly answered in this quiz
    completed_question_ids = set(s['question_id'] for s in correct_submissions)
    
    # Calculate progress percentage
    total_questions = len(quiz_questions)
    completed_count = sum(1 for q in quiz_questions if q['id'] in completed_question_ids)
    progress = int((completed_count / total_questions) * 100) if total_questions > 0 else 0

    return render_template('attempt_quiz.html', 
                          quiz=quiz, 
                          questions=quiz_questions,
                          progress=progress,
                          completed_questions=completed_question_ids)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/dashboard')
def dashboard():
    # Import data_loader here to avoid circular imports
    from app.data_loader import load_user_data, filter_data_by_timerange
    from app.chart_utils import create_activity_chart, create_grades_chart
    
    # Get time range from query parameters, default to 7 days
    days = request.args.get('days', 7, type=int)
    
    # Print debug info about current directory and parameters
    import os
    app.logger.info(f"Current working directory: {os.getcwd()}")
    app.logger.info(f"Selected time range: {days} days")
    
    # Load user data
    try:
        # Load and filter the user data
        app.logger.info("Attempting to load user data...")
        user_data = load_user_data()
        
        if user_data:
            # Print debug information
            app.logger.info(f"User data loaded. Name: {user_data.get('basic_info', {}).get('name')}")
            app.logger.info(f"Gradebook entries: {len(user_data.get('gradebook', []))}")
            app.logger.info(f"Activity entries: {len(user_data.get('activity', {}).get('daily_submissions', []))}")
            app.logger.info(f"Class progress entries: {len(user_data.get('class_progress', []))}")
            
            # Prepare data for the template
            import copy
            filtered_data = copy.deepcopy(user_data)
            
            # Apply time filtering 
            filtered_data = filter_data_by_timerange(filtered_data, days)
            
            # Print filtered data information
            app.logger.info(f"After filtering (days={days}):")
            app.logger.info(f"Gradebook entries: {len(filtered_data.get('gradebook', []))}")
            app.logger.info(f"Activity entries: {len(filtered_data.get('activity', {}).get('daily_submissions', []))}")
            
            # Make sure we have the activity structure even if empty
            if 'activity' not in filtered_data:
                filtered_data['activity'] = {'daily_submissions': []}
            elif 'daily_submissions' not in filtered_data['activity']:
                filtered_data['activity']['daily_submissions'] = []
                
            # Make sure we have the gradebook structure even if empty
            if 'gradebook' not in filtered_data:
                filtered_data['gradebook'] = []
                
            # Make sure we have the teacher_comments structure even if empty
            if 'teacher_comments' not in filtered_data:
                filtered_data['teacher_comments'] = []
            
            # Generate charts
            activity_chart_html = create_activity_chart(filtered_data['activity']['daily_submissions'])
            grades_chart_html = create_grades_chart(filtered_data['gradebook'])
            
            return render_template(
                'dashboard.html', 
                user=filtered_data,
                activity_chart=activity_chart_html,
                grades_chart=grades_chart_html
            )
        else:
            app.logger.error("User data could not be loaded (returned None)")
            flash("User data could not be loaded", "error")
            return render_template('dashboard.html')
    except Exception as e:
        app.logger.error(f"Error loading user data: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        flash("Could not load user data", "error")
        return render_template('dashboard.html')

@app.route('/courses')
def courses():
    return render_template('courses.html')

@app.route('/add_question', methods=['GET', 'POST'])
def add_question():
    form = QuestionForm()
    attachment_form = AttachmentForm()
    
    # Get all existing tags for the dropdown
    all_tags = get_all_tags()
    
    if form.validate_on_submit():
        questions = load_questions(include_deleted=True)
        
        # Get selected tag IDs from the form
        selected_tag_ids = request.form.getlist('selected_tags')
        
        # Ensure at least one tag is provided
        if not selected_tag_ids:
            flash('Please select at least one tag for the question.', 'error')
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
        
        # Process hints from the form
        hints = []
        hint_index = 0
        while f'hint_text_{hint_index}' in request.form:
            hint_text = request.form.get(f'hint_text_{hint_index}', '').strip()
            hint_weight = request.form.get(f'hint_weight_{hint_index}', '5')
            
            # Validate hint text - must be 50 words or less
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
                    # Skip invalid weights
                    pass
            
            hint_index += 1
        
        # Create the new question
        new_question = {
            'id': question_id,
            'name': form.name.data,
            'content': form.content.data,
            'answer': form.answer.data,
            'svg': latex_svg,
            'svg_generated': False,  # Flag to indicate SVG needs to be generated
            'rating': float(form.rating.data),  # Convert Decimal to float
            'tags': selected_tag_ids,
            'deleted': False,
            'attachments': url_attachments,
            'hints': hints  # Add hints to the question model
        }
        
        # Process file uploads if any
        if 'attachment_file' in request.files:
            files = request.files.getlist('attachment_file')
            # Debug info
            file_names = [f.filename for f in files if f and f.filename]
            flash(f"Files detected: {len(file_names)} - {', '.join(file_names)}", 'info')
            
            valid_files = [f for f in files if f and f.filename]
            
            # Validate files against limits
            is_valid, error_message = validate_file_uploads(valid_files)
            if not is_valid:
                flash(error_message, 'error')
                return render_template('add_question.html', form=form, attachment_form=attachment_form, all_tags=all_tags)
            
            file_attachments = []
            for file in valid_files:
                if allowed_file(file.filename):
                    attachment = save_attachment(file, question_id)
                    file_attachments.append(attachment)
                else:
                    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'unknown'
                    flash(f'File type {ext} is not allowed', 'error')
                    return render_template('add_question.html', form=form, attachment_form=attachment_form, all_tags=all_tags)
            
            # Add file attachments to question
            new_question['attachments'].extend(file_attachments)
        
        questions.append(new_question)
        save_questions(questions)
        flash('Question added successfully!', 'success')
        return redirect(url_for('questionbank'))
    
    return render_template('add_question.html', form=form, attachment_form=attachment_form, all_tags=all_tags)

@app.route('/question/<question_id>')
def view_question(question_id):
    questions = load_questions(include_deleted=True)
    question = next((q for q in questions if q.get('id') == question_id), None)
    
    # Check if we're in quiz creation/editing context
    creating_quiz = request.args.get('creating_quiz') == 'true'
    quiz_name = request.args.get('quiz_name', '')
    selected_quiz_tags = request.args.getlist('selected_quiz_tags')
    filter_tags = request.args.getlist('filter_tags')
    search_query = request.args.get('search_query', '')
    sort_by = request.args.get('sort_by', 'newest')
    
    if not question:
        flash('Question not found!', 'error')
        return redirect(url_for('index'))
    
    # Generate SVG if it hasn't been generated yet or if it's flagged for regeneration
    if not question.get('svg') or question.get('svg_generated') is False:
        try:
            question['svg'] = latex_to_svg(ensure_complete_latex_document(question['content']))
            question['svg_generated'] = True
        except Exception as e:
            # If LaTeX compilation fails, use a placeholder image
            app.logger.error(f"Error generating SVG for question {question.get('id')}: {str(e)}")
            question['svg'] = '/static/img/latex-placeholder.svg'
            question['svg_generated'] = False
        
        # Save the updated questions
        save_questions(questions)
    
    # Get all tags for accessing the tag display names
    all_tags = get_all_tags()
    
    # Function to get tag by ID for use in the template
    def get_tag_by_id(tag_id):
        return next((tag for tag in all_tags if tag['id'] == tag_id), None)
    
    return render_template('view_question.html', 
                          question=question,
                          creating_quiz=creating_quiz,
                          quiz_name=quiz_name,
                          selected_quiz_tags=selected_quiz_tags,
                          filter_tags=filter_tags,
                          search_query=search_query,
                          sort_by=sort_by,
                          get_tag_by_id=get_tag_by_id)

@app.route('/attempt_question/<question_id>', methods=['GET', 'POST'])
def attempt_question(question_id):
    questions = load_questions(include_deleted=True)
    question = next((q for q in questions if q.get('id') == question_id), None)
    
    # Get quiz context if provided (for attempt quiz feature)
    quiz_id = request.args.get('quiz_id')
    quiz = None
    if quiz_id:
        quizzes = load_quizzes()
        quiz = next((q for q in quizzes if q.get('id') == quiz_id), None)
    
    # Check if we're in quiz creation/editing context
    creating_quiz = request.args.get('creating_quiz') == 'true'
    quiz_name = request.args.get('quiz_name', '')
    selected_quiz_tags = request.args.getlist('selected_quiz_tags')
    filter_tags = request.args.getlist('filter_tags')
    search_query = request.args.get('search_query', '')
    sort_by = request.args.get('sort_by', 'newest')
    
    if not question:
        flash('Question not found!', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        user_answer = request.form.get('answer', '').strip()
        correct_answer = question.get('answer', '').strip()
        
        # Get the quiz ID from form if available
        submission_quiz_id = request.form.get('quiz_id')
        
        # Get the hints that were used from the form
        used_hints = request.form.getlist('used_hints')
        
        # Map hint IDs to their positions for proper tracking
        hint_positions = {}
        for i, hint in enumerate(question.get('hints', []), 1):
            hint_positions[hint['id']] = i
        
        # Create a structure to track both hint IDs and their positions
        hint_data = []
        for hint_id in used_hints:
            if hint_id in hint_positions:
                hint_data.append({
                    'id': hint_id,
                    'position': hint_positions[hint_id]
                })
            else:
                # Handle unknown hints
                hint_data.append({
                    'id': hint_id,
                    'position': 0  # unknown position
                })
        
        # Simple string comparison
        is_correct = user_answer.lower() == correct_answer.lower()
        
        submissions = load_submissions()
        new_submission = {
            'id': str(uuid.uuid4()),
            'question_id': question_id,
            'user_answer': user_answer,
            'outcome': 'Correct' if is_correct else 'Incorrect',
            'verdict': 'Your answer is correct.' if is_correct else 'Your answer is incorrect. Please try again.',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'used_hints': used_hints,  # Keep the raw hint IDs
            'hint_data': hint_data,    # Add the enhanced hint data with positions
            'quiz_id': submission_quiz_id  # Track which quiz this submission is from
        }
        submissions.append(new_submission)
        save_submissions(submissions)
        
        flash(new_submission['verdict'], 'success' if is_correct else 'error')
        
        # If correct and from a quiz, redirect back to the quiz
        if is_correct and submission_quiz_id:
            return redirect(url_for('attempt_quiz', quiz_id=submission_quiz_id))
        
        # Pass all the creation context parameters back when redirecting
        if creating_quiz:
            return redirect(url_for('attempt_question', 
                                   question_id=question_id, 
                                   quiz_id=quiz_id,
                                   creating_quiz=creating_quiz,
                                   quiz_name=quiz_name,
                                   selected_quiz_tags=selected_quiz_tags,
                                   filter_tags=filter_tags,
                                   search_query=search_query,
                                   sort_by=sort_by))
        else:
            return redirect(url_for('attempt_question', question_id=question_id, quiz_id=quiz_id))

    # Generate SVG if it hasn't been generated yet or if it's flagged for regeneration
    if not question.get('svg') or question.get('svg_generated') is False:
        try:
            question['svg'] = latex_to_svg(ensure_complete_latex_document(question['content']))
            question['svg_generated'] = True
        except Exception as e:
            # If LaTeX compilation fails, use a placeholder image
            app.logger.error(f"Error generating SVG for question {question.get('id')}: {str(e)}")
            question['svg'] = '/static/img/latex-placeholder.svg'
            question['svg_generated'] = False
            
        # Save the updated questions
        save_questions(questions)
    
    # Get submissions for this question
    all_submissions = load_submissions()
    question_submissions = [s for s in all_submissions if s['question_id'] == question_id]
    question_submissions.sort(key=lambda x: x['timestamp'], reverse=True)

    # Get all tags for accessing the tag display names
    all_tags = get_all_tags()
    
    # Function to get tag by ID for use in the template
    def get_tag_by_id(tag_id):
        return next((tag for tag in all_tags if tag['id'] == tag_id), None)
    
    return render_template('attempt_question.html', 
                           question=question, 
                           get_tag_by_id=get_tag_by_id, 
                           submissions=question_submissions,
                           quiz_id=quiz_id,
                           creating_quiz=creating_quiz,
                           quiz_name=quiz_name,
                           selected_quiz_tags=selected_quiz_tags,
                           filter_tags=filter_tags,
                           search_query=search_query,
                           sort_by=sort_by)

@app.route('/edit_question/<question_id>', methods=['GET', 'POST'])
def edit_question(question_id):
    questions = load_questions(include_deleted=True)
    question = next((q for q in questions if q.get('id') == question_id), None)
    
    if not question:
        flash('Question not found!', 'error')
        return redirect(url_for('questionbank'))
    
    form = QuestionForm()
    attachment_form = AttachmentForm()
    all_tags = get_all_tags()
    
    if request.method == 'GET':
        # Pre-populate the form with existing question data
        if 'name' in question:
            form.name.data = question['name']
        form.content.data = question['content']
        form.answer.data = question.get('answer', '')
        form.rating.data = question['rating']
        # Tags are now selected from dropdown, not text input
    
    if form.validate_on_submit():
        # Mark the old question as deleted
        question['deleted'] = True
        
        # Get selected tag IDs from the form
        selected_tag_ids = request.form.getlist('selected_tags')
        
        # Ensure at least one tag is provided
        if not selected_tag_ids:
            flash('Please select at least one tag for the question.', 'error')
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
            'name': form.name.data,
            'content': form.content.data,
            'answer': form.answer.data,
            'svg': latex_svg,  # Use existing SVG initially
            'svg_generated': False,  # Flag to indicate SVG needs to be generated
            'rating': float(form.rating.data),
            'tags': selected_tag_ids,
            'deleted': False,
            'edited_from': question_id,  # Reference to the original question
            'attachments': kept_attachments,
            'hints': question.get('hints', [])  # Preserve hints from the original question
        }
        
        # Process new file uploads if any
        if 'attachment_file' in request.files:
            files = request.files.getlist('attachment_file')
            valid_files = [f for f in files if f and f.filename]
            
            # Validate files against limits
            # First, count existing files that are being kept
            existing_pdfs = sum(1 for a in kept_attachments if a.get('category', '') == 'pdf')
            existing_videos = sum(1 for a in kept_attachments if a.get('category', '') == 'video')
            existing_images = sum(1 for a in kept_attachments if a.get('category', '') == 'image')
            
            # Create a combined list for validation
            all_files = valid_files + [
                type('obj', (object,), {
                    'filename': a.get('original_filename', ''),
                })
                for a in kept_attachments
            ]
            
            # Validate all files together
            is_valid, error_message = validate_file_uploads(all_files)
            if not is_valid:
                flash(error_message, 'error')
                return render_template('edit_question.html', form=form, attachment_form=attachment_form, 
                                      question=question, all_tags=all_tags)
            
            # Process new uploads
            for file in valid_files:
                if allowed_file(file.filename):
                    attachment = save_attachment(file, new_question_id)
                    new_question['attachments'].append(attachment)
                else:
                    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'unknown'
                    flash(f'File type {ext} is not allowed', 'error')
                    return render_template('edit_question.html', form=form, attachment_form=attachment_form, 
                                          question=question, all_tags=all_tags)
        
        questions.append(new_question)
        save_questions(questions)
        flash('Question updated successfully!', 'success')
        return redirect(url_for('view_question', question_id=new_question_id))
    
    return render_template('edit_question.html', form=form, attachment_form=attachment_form, question=question, all_tags=all_tags)

@app.route('/delete_question/<question_id>', methods=['GET', 'POST'])
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
    
    return redirect(url_for('questionbank'))

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
        
        # Check if the file is a PDF to display it inline
        is_pdf = attachment.get('file_type') == 'pdf' or filename.lower().endswith('.pdf')
        
        return send_from_directory(attachment_dir, filename, as_attachment=not is_pdf, 
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

@app.route('/api/tags', methods=['GET', 'POST', 'PUT', 'DELETE'])
def manage_tags():
    """API endpoint to manage tags"""
    tags = load_tags()
    
    if request.method == 'GET':
        # Return all tags
        return jsonify(tags)
        
    elif request.method == 'POST':
        # Add a new tag
        data = request.get_json()
        if not data or 'display_name' not in data:
            return jsonify({'success': False, 'error': 'No display name provided'}), 400
            
        # Create a safe ID from the display name
        tag_id = data.get('id', data['display_name'].lower().replace(' ', '_'))
        
        # Check if the tag already exists
        if any(tag['id'] == tag_id for tag in tags):
            return jsonify({'success': False, 'error': 'Tag ID already exists'}), 400
            
        # Add the new tag
        new_tag = {
            'id': tag_id,
            'display_name': data['display_name']
        }
        tags.append(new_tag)
        save_tags(tags)
        
        return jsonify({'success': True, 'tag': new_tag})
        
    elif request.method == 'PUT':
        # Update a tag's display name
        data = request.get_json()
        if not data or 'id' not in data or 'display_name' not in data:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
            
        # Find the tag to update
        tag_to_update = next((tag for tag in tags if tag['id'] == data['id']), None)
        if not tag_to_update:
            return jsonify({'success': False, 'error': 'Tag not found'}), 404
            
        # Update the display name
        tag_to_update['display_name'] = data['display_name']
        save_tags(tags)
        
        return jsonify({'success': True, 'tag': tag_to_update})
        
    elif request.method == 'DELETE':
        # Delete a tag
        data = request.get_json()
        if not data or 'id' not in data:
            return jsonify({'success': False, 'error': 'No tag ID provided'}), 400
            
        # Check if the tag exists
        tag_to_delete = next((tag for tag in tags if tag['id'] == data['id']), None)
        if not tag_to_delete:
            return jsonify({'success': False, 'error': 'Tag not found'}), 404
            
        # Remove the tag
        tags.remove(tag_to_delete)
        save_tags(tags)
        
        # Also need to remove this tag from all questions
        questions = load_questions(include_deleted=True)
        updated = False
        for question in questions:
            if data['id'] in question.get('tags', []):
                question['tags'].remove(data['id'])
                updated = True
        
        if updated:
            save_questions(questions)
            
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Invalid request method'}), 405

# Make tag helper functions available in templates
@app.context_processor
def inject_tag_helpers():
    return {
        'get_tag_by_id': get_tag_by_id,
        'get_tag_display_name': get_tag_display_name,
        'get_quiz_tag_by_id': get_quiz_tag_by_id,
        'get_quiz_tag_display_name': get_quiz_tag_display_name
    }

def allowed_file(filename):
    """Check if the file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def validate_file_uploads(files):
    """
    Validate file uploads against the defined limits:
    - at most 1 pdf
    - at most 1 webm OR mp4 
    - at most 1 png, jpg, or jpeg
    - at most 4 files in total
    
    Returns a tuple of (is_valid, error_message)
    """
    if len(files) > 4:
        return False, "Maximum 4 files can be uploaded"
    
    # Count file types
    pdf_count = 0
    video_count = 0
    image_count = 0
    
    # Total file size
    total_size = 0
    
    for file in files:
        if not file or not file.filename:
            continue
        
        # Get file extension
        extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        
        if not extension or extension not in app.config['ALLOWED_EXTENSIONS']:
            return False, f"File type {extension} is not allowed"
        
        # Check file size (in bytes)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # Reset file pointer
        
        total_size += file_size
        
        # Count by file type
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
    
    # Max total size (100MB)
    if total_size > app.config['MAX_CONTENT_LENGTH']:
        return False, f"Total file size must be less than {app.config['MAX_CONTENT_LENGTH'] // (1024 * 1024)}MB"
    
    return True, ""

@app.route('/api/questions/<question_id>/hints', methods=['POST'])
def add_hint(question_id):
    """API endpoint to add a hint to a question"""
    try:
        data = request.get_json()
        if not data or 'text' not in data or 'weight' not in data:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400

        # Validate hint text - maximum 50 words
        hint_text = data['text'].strip()
        word_count = len(hint_text.split())
        if word_count > 50:
            return jsonify({'success': False, 'error': f'Hint text must be 50 words or less (currently {word_count} words)'}), 400

        # Validate weight - must be integer between 1 and 10
        try:
            weight = int(data['weight'])
            if weight < 1 or weight > 10:
                return jsonify({'success': False, 'error': 'Weight must be between 1 and 10'}), 400
        except ValueError:
            return jsonify({'success': False, 'error': 'Weight must be an integer'}), 400

        # Load questions and find the target question
        questions = load_questions(include_deleted=True)
        question = next((q for q in questions if q.get('id') == question_id), None)
        
        if not question:
            return jsonify({'success': False, 'error': 'Question not found'}), 404

        # Create the new hint object
        new_hint = {
            'id': str(uuid.uuid4()),
            'text': hint_text,
            'weight': weight
        }

        # Add the hint to the question
        if 'hints' not in question:
            question['hints'] = []
        question['hints'].append(new_hint)
        save_questions(questions)

        return jsonify({
            'success': True,
            'hint': new_hint
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/questions/<question_id>/hints/<hint_id>', methods=['PUT'])
def update_hint(question_id, hint_id):
    """API endpoint to update a hint"""
    try:
        data = request.get_json()
        if not data or ('text' not in data and 'weight' not in data):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400

        # Validate hint text if provided - maximum 50 words
        if 'text' in data:
            hint_text = data['text'].strip()
            word_count = len(hint_text.split())
            if word_count > 50:
                return jsonify({'success': False, 'error': f'Hint text must be 50 words or less (currently {word_count} words)'}), 400

        # Validate weight if provided - must be integer between 1 and 10
        if 'weight' in data:
            try:
                weight = int(data['weight'])
                if weight < 1 or weight > 10:
                    return jsonify({'success': False, 'error': 'Weight must be between 1 and 10'}), 400
            except ValueError:
                return jsonify({'success': False, 'error': 'Weight must be an integer'}), 400

        # Load questions and find the target question
        questions = load_questions(include_deleted=True)
        question = next((q for q in questions if q.get('id') == question_id), None)
        
        if not question:
            return jsonify({'success': False, 'error': 'Question not found'}), 404

        # Find the hint to update
        hint = next((h for h in question.get('hints', []) if h.get('id') == hint_id), None)
        if not hint:
            return jsonify({'success': False, 'error': 'Hint not found'}), 404

        # Update the hint
        if 'text' in data:
            hint['text'] = hint_text
        if 'weight' in data:
            hint['weight'] = weight

        save_questions(questions)

        return jsonify({
            'success': True,
            'hint': hint
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/questions/<question_id>/hints/<hint_id>', methods=['DELETE'])
def delete_hint(question_id, hint_id):
    """API endpoint to delete a hint"""
    try:
        # Load questions and find the target question
        questions = load_questions(include_deleted=True)
        question = next((q for q in questions if q.get('id') == question_id), None)
        
        if not question:
            return jsonify({'success': False, 'error': 'Question not found'}), 404

        # Find the hint to delete
        hint = next((h for h in question.get('hints', []) if h.get('id') == hint_id), None)
        if not hint:
            return jsonify({'success': False, 'error': 'Hint not found'}), 404

        # Remove the hint
        question['hints'].remove(hint)
        save_questions(questions)

        return jsonify({
            'success': True
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/quiz_tags', methods=['GET', 'POST', 'PUT', 'DELETE'])
def manage_quiz_tags():
    """API endpoint to manage quiz tags"""
    tags = load_quiz_tags()
    
    if request.method == 'GET':
        # Return all tags
        return jsonify(tags)
        
    elif request.method == 'POST':
        # Add a new tag
        data = request.get_json()
        if not data or 'display_name' not in data:
            return jsonify({'success': False, 'error': 'No display name provided'}), 400
            
        # Create a safe ID from the display name
        tag_id = data.get('id', data['display_name'].lower().replace(' ', '_'))
        
        # Check if the tag already exists
        if any(tag['id'] == tag_id for tag in tags):
            return jsonify({'success': False, 'error': 'Tag ID already exists'}), 400
            
        # Add the new tag
        new_tag = {
            'id': tag_id,
            'display_name': data['display_name']
        }
        tags.append(new_tag)
        save_quiz_tags(tags)
        
        return jsonify({'success': True, 'tag': new_tag})
        
    elif request.method == 'PUT':
        # Update a tag's display name
        data = request.get_json()
        if not data or 'id' not in data or 'display_name' not in data:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
            
        # Find the tag to update
        tag_to_update = next((tag for tag in tags if tag['id'] == data['id']), None)
        if not tag_to_update:
            return jsonify({'success': False, 'error': 'Tag not found'}), 404
            
        # Update the display name
        tag_to_update['display_name'] = data['display_name']
        save_quiz_tags(tags)
        
        return jsonify({'success': True, 'tag': tag_to_update})
        
    elif request.method == 'DELETE':
        # Delete a tag
        data = request.get_json()
        if not data or 'id' not in data:
            return jsonify({'success': False, 'error': 'No tag ID provided'}), 400
            
        # Check if the tag exists
        tag_to_delete = next((tag for tag in tags if tag['id'] == data['id']), None)
        if not tag_to_delete:
            return jsonify({'success': False, 'error': 'Tag not found'}), 404
            
        # Remove the tag
        tags.remove(tag_to_delete)
        save_quiz_tags(tags)
        
        # Also need to remove this tag from all quizzes
        quizzes = load_quizzes()
        updated = False
        for quiz in quizzes:
            if 'tags' in quiz and data['id'] in quiz['tags']:
                quiz['tags'].remove(data['id'])
                updated = True
        
        if updated:
            save_quizzes(quizzes)
            
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Invalid request method'}), 405 

@app.route('/quizzes/<quiz_id>/delete', methods=['GET', 'POST'])
def delete_quiz(quiz_id):
    quizzes = load_quizzes()
    quiz = next((q for q in quizzes if q['id'] == quiz_id), None)
    
    if not quiz:
        flash('Quiz not found.', 'danger')
    else:
        quiz['deleted'] = True
        save_quizzes(quizzes)
        flash('Quiz deleted successfully.', 'success')
    
    return redirect(url_for('quizzes'))

@app.route('/quizzes/<quiz_id>/restore', methods=['GET', 'POST'])
def restore_quiz(quiz_id):
    quizzes = load_quizzes()
    quiz = next((q for q in quizzes if q['id'] == quiz_id), None)
    
    if not quiz:
        flash('Quiz not found.', 'danger')
    else:
        quiz['deleted'] = False
        save_quizzes(quizzes)
        flash('Quiz restored successfully.', 'success')
    
    return redirect(url_for('quizzes')) 

@app.route('/debug/user_data')
def debug_user_data():
    """Debug route to directly view the user data as JSON"""
    from app.data_loader import load_user_data
    
    try:
        user_data = load_user_data()
        if user_data:
            # Return the user data as JSON
            return jsonify(user_data)
        else:
            return jsonify({"error": "User data could not be loaded"}), 500
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500 