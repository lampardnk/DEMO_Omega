import json
import os
import re
import tempfile
import subprocess
import shutil
from flask import render_template, request, redirect, url_for, jsonify, flash, session, send_from_directory
from werkzeug.utils import secure_filename
from app import app
from app.forms import QuestionForm, AttachmentForm
import matplotlib.pyplot as plt
import numpy as np
import io
import base64
import uuid
from decimal import Decimal
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

# Custom JSON encoder to handle Decimal objects
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def load_questions(include_deleted=False):
    if os.path.exists(app.config['QUESTIONS_FILE']):
        with open(app.config['QUESTIONS_FILE'], 'r') as f:
            questions = json.load(f)
            if not include_deleted:
                # Filter out questions marked as deleted
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

def check_latex_packages(latex_content):
    """Check if the LaTeX content requires special packages"""
    needs_tikz = "\\begin{tikzpicture}" in latex_content or "\\tikz" in latex_content
    needs_circuitikz = "\\begin{circuitikz}" in latex_content
    needs_scope = "\\begin{scope}" in latex_content
    
    return needs_tikz, needs_circuitikz, needs_scope

def latex_to_svg(latex_string):
    """
    Convert LaTeX to SVG image
    Will use matplotlib for simple LaTeX and a full LaTeX compiler for complex environments like TikZ
    """
    # Check if we need special LaTeX packages
    needs_tikz, needs_circuitikz, needs_scope = check_latex_packages(latex_string)
    
    # If we need special packages, use a full LaTeX compiler
    if needs_tikz or needs_circuitikz or needs_scope:
        return compile_complex_latex(latex_string, needs_tikz, needs_circuitikz, needs_scope)
    
    # For simple LaTeX, use matplotlib
    fig = plt.figure(figsize=(5, 0.5))
    plt.axis('off')
    plt.text(0.5, 0.5, f"${latex_string}$", size=14, ha='center', va='center')
    
    # Convert the figure to a PNG and then encode to base64
    buf = io.BytesIO()
    FigureCanvas(fig).print_png(buf)
    plt.close(fig)
    
    # Return base64 encoded image
    data = base64.b64encode(buf.getbuffer()).decode("ascii")
    return f"data:image/png;base64,{data}"

def compile_complex_latex(latex_content, needs_tikz=False, needs_circuitikz=False, needs_scope=False):
    """Compile complex LaTeX with TikZ, CircuiTikZ, etc. using a full LaTeX compiler"""
    # Create a temporary directory for LaTeX compilation
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create the LaTeX document
        latex_document = []
        latex_document.append("\\documentclass[border=10pt]{standalone}")
        latex_document.append("\\usepackage{amsmath,amssymb}")
        
        # Add required packages based on content
        if needs_tikz or needs_scope:
            latex_document.append("\\usepackage{tikz}")
        if needs_circuitikz:
            latex_document.append("\\usepackage{circuitikz}")
        
        # Start the document
        latex_document.append("\\begin{document}")
        
        # Add the LaTeX content
        if needs_tikz or needs_circuitikz or needs_scope:
            # For TikZ or CircuiTikZ content, add directly
            latex_document.append(latex_content)
        else:
            # For regular math, wrap in equation environment
            latex_document.append("$" + latex_content + "$")
        
        # End the document
        latex_document.append("\\end{document}")
        
        # Write the LaTeX document to a file
        tex_file = os.path.join(temp_dir, "latex_content.tex")
        with open(tex_file, "w") as f:
            f.write("\n".join(latex_document))
        
        try:
            # Compile LaTeX to PDF using pdflatex
            subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-output-directory", temp_dir, tex_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            
            # Convert PDF to PNG using pdf2image or another tool
            pdf_file = os.path.join(temp_dir, "latex_content.pdf")
            png_file = os.path.join(temp_dir, "latex_content.png")
            
            # Use pdftoppm or similar to convert PDF to PNG
            subprocess.run(
                ["pdftoppm", "-png", "-singlefile", "-r", "300", pdf_file, os.path.join(temp_dir, "latex_content")],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            
            # Read the PNG file and convert to base64
            with open(png_file, "rb") as f:
                png_data = f.read()
            
            # Return base64 encoded image
            base64_data = base64.b64encode(png_data).decode("ascii")
            return f"data:image/png;base64,{base64_data}"
            
        except subprocess.CalledProcessError as e:
            # If compilation fails, return error message as image
            error_text = f"LaTeX compilation error: {e}"
            fig = plt.figure(figsize=(6, 1))
            plt.axis('off')
            plt.text(0.5, 0.5, error_text, color='red', ha='center', va='center')
            
            buf = io.BytesIO()
            FigureCanvas(fig).print_png(buf)
            plt.close(fig)
            
            data = base64.b64encode(buf.getbuffer()).decode("ascii")
            return f"data:image/png;base64,{data}"

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
        
        # Generate unique ID for the question
        question_id = str(uuid.uuid4())
        
        # Generate SVG from LaTeX
        latex_svg = latex_to_svg(form.content.data)
        
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
        
        # Generate unique ID for the new question
        new_question_id = str(uuid.uuid4())
        
        # Generate SVG from LaTeX
        latex_svg = latex_to_svg(form.content.data)
        
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
            'svg': latex_svg,
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