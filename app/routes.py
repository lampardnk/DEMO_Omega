import json
import uuid
import time
from flask import render_template, request, redirect, url_for, jsonify, flash, send_from_directory
from app import app
from app.forms import QuestionForm, AttachmentForm
from app.utils.data_manager import DataManager, TagManager
from app.utils.latex_processor import LaTeXProcessor
from app.utils.file_manager import FileManager
from app.data_loader import load_user_data, filter_data_by_timerange


@app.route('/api/compile-latex', methods=['POST'])
def compile_latex():
    """API endpoint to compile LaTeX to SVG and return the result"""
    try:
        data = request.get_json()
        if not data or 'latex' not in data:
            return jsonify({'success': False, 'error': 'No LaTeX content provided'}), 400

        latex_content = data['latex']
        complete_latex = LaTeXProcessor.ensure_complete_document(latex_content)
        svg_data = LaTeXProcessor.latex_to_svg(complete_latex)

        return jsonify({'success': True, 'svg': svg_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/')
def index():
    return redirect(url_for('questionbank'))


@app.route('/questionbank')
def questionbank():
    show_deleted = request.args.get('show_deleted', 'false').lower() == 'true'
    filter_tags = request.args.getlist('tags')
    sort_by = request.args.get('sort', 'newest')
    search_query = request.args.get('search', '').strip().lower()

    questions = DataManager.load_questions(include_deleted=show_deleted)

    # Apply filters
    if filter_tags:
        questions = [q for q in questions if any(tag in q.get('tags', []) for tag in filter_tags)]

    if search_query:
        questions = [q for q in questions if 
                    search_query in q.get('name', '').lower() or 
                    search_query in q.get('content', '').lower()]

    # Sort questions
    if sort_by == 'rating_asc':
        questions.sort(key=lambda x: float(x.get('rating', 0)))
    elif sort_by == 'rating_desc':
        questions.sort(key=lambda x: float(x.get('rating', 0)), reverse=True)
    elif sort_by == 'newest':
        questions.sort(key=lambda x: x.get('id', 0), reverse=True)

    # Generate SVGs if needed
    updated = False
    for question in questions:
        if not question.get('svg') or question.get('svg_generated') is False:
            try:
                question['svg'] = LaTeXProcessor.latex_to_svg(
                    LaTeXProcessor.ensure_complete_document(question['content'])
                )
                question['svg_generated'] = True
            except Exception as e:
                app.logger.error(f"Error generating SVG for question {question.get('id')}: {str(e)}")
                question['svg'] = '/static/img/latex-placeholder.svg'
                question['svg_generated'] = False
            updated = True

    if updated:
        DataManager.save_questions(DataManager.load_questions(include_deleted=True))

    all_tags = TagManager.get_all_tags()

    return render_template('index.html', 
                          questions=questions, 
                          filter_tags=filter_tags,
                          sort_by=sort_by, 
                          all_tags=all_tags, 
                          show_deleted=show_deleted,
                          search_query=search_query)


@app.route('/quizzes')
def quizzes():
    search_query = request.args.get('search', '').strip().lower()
    filter_tags = request.args.getlist('tags')
    sort_by = request.args.get('sort', 'newest')
    show_deleted = request.args.get('show_deleted') == 'true'

    all_quizzes = DataManager.load_quizzes()

    # Apply filters
    filtered_quizzes = all_quizzes
    if search_query:
        filtered_quizzes = [q for q in filtered_quizzes if search_query in q.get('name', '').lower()]

    if filter_tags:
        filtered_quizzes = [q for q in filtered_quizzes if set(filter_tags).intersection(set(q.get('tags', [])))]

    if not show_deleted:
        filtered_quizzes = [q for q in filtered_quizzes if not q.get('deleted', False)]

    # Sort quizzes
    if sort_by == 'name_asc':
        filtered_quizzes = sorted(filtered_quizzes, key=lambda q: q.get('name', '').lower())
    elif sort_by == 'name_desc':
        filtered_quizzes = sorted(filtered_quizzes, key=lambda q: q.get('name', '').lower(), reverse=True)
    elif sort_by == 'questions_asc':
        filtered_quizzes = sorted(filtered_quizzes, key=lambda q: len(q.get('question_ids', [])))
    elif sort_by == 'questions_desc':
        filtered_quizzes = sorted(filtered_quizzes, key=lambda q: len(q.get('question_ids', [])), reverse=True)

    all_quiz_tags = TagManager.get_all_quiz_tags()

    return render_template('quizzes.html',
                          quizzes=filtered_quizzes,
                          search_query=search_query,
                          filter_tags=filter_tags,
                          all_quiz_tags=all_quiz_tags,
                          sort_by=sort_by,
                          show_deleted=show_deleted)


@app.route('/quizzes/new', methods=['GET', 'POST'])
def create_quiz():
    quiz_tags = TagManager.get_all_quiz_tags()
    all_tags = TagManager.get_all_tags()

    # Get filter parameters
    filter_tags = request.args.getlist('filter_tags') or []
    search_query = request.args.get('search_query', '')
    sort_by = request.args.get('sort_by', 'newest')

    questions = _get_filtered_questions(filter_tags, search_query, sort_by)

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

        quizzes = DataManager.load_quizzes()
        new_quiz = {
            'id': str(uuid.uuid4()),
            'name': name,
            'tags': selected_tags,
            'question_ids': question_ids,
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'deleted': False
        }
        quizzes.append(new_quiz)
        DataManager.save_quizzes(quizzes)

        flash('Quiz created successfully!', 'success')
        return redirect(url_for('quizzes'))

    return render_template('create_quiz.html',
                          questions=questions,
                          all_quiz_tags=quiz_tags,
                          all_tags=all_tags,
                          filter_tags=filter_tags,
                          search_query=search_query,
                          sort_by=sort_by)


@app.route('/quizzes/<quiz_id>/edit', methods=['GET', 'POST'])
def edit_quiz(quiz_id):
    quizzes = DataManager.load_quizzes()
    quiz = next((q for q in quizzes if q.get('id') == quiz_id), None)

    if not quiz:
        flash('Quiz not found!', 'error')
        return redirect(url_for('quizzes'))

    if quiz.get('deleted'):
        flash('Cannot edit a deleted quiz!', 'error')
        return redirect(url_for('quizzes'))

    all_tags = TagManager.get_all_tags()
    all_quiz_tags = TagManager.get_all_quiz_tags()
    questions = _get_filtered_questions()

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

        quiz['name'] = name
        quiz['tags'] = selected_tags
        quiz['question_ids'] = question_ids

        DataManager.save_quizzes(quizzes)
        flash('Quiz updated successfully!', 'success')
        return redirect(url_for('quizzes'))

    return render_template('create_quiz.html',
                          quiz=quiz,
                          questions=questions,
                          all_quiz_tags=all_quiz_tags,
                          all_tags=all_tags)


@app.route('/quizzes/<quiz_id>/attempt')
def attempt_quiz(quiz_id):
    quizzes = DataManager.load_quizzes()
    quiz = next((q for q in quizzes if q['id'] == quiz_id), None)

    if not quiz:
        flash('Quiz not found.', 'danger')
        return redirect(url_for('quizzes'))

    if quiz.get('deleted', False):
        flash('This quiz has been deleted and cannot be attempted.', 'danger')
        return redirect(url_for('quizzes'))

    all_questions = DataManager.load_questions(include_deleted=True)
    quiz_questions = [q for q in all_questions if q['id'] in quiz['question_ids']]

    # Generate SVGs
    _ensure_question_svgs(quiz_questions, all_questions)

    # Calculate progress
    all_submissions = DataManager.load_submissions()
    correct_submissions = [s for s in all_submissions 
                          if s.get('outcome') == 'Correct' and s.get('quiz_id') == quiz_id]
    completed_question_ids = set(s['question_id'] for s in correct_submissions)

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
    days = request.args.get('days', 7, type=int)

    try:
        app.logger.info(f"Selected time range: {days} days")
        user_data = load_user_data()

        if user_data:
            app.logger.info(f"User data loaded. Name: {user_data.get('basic_info', {}).get('name')}")

            import copy
            filtered_data = copy.deepcopy(user_data)
            filtered_data = filter_data_by_timerange(filtered_data, days)

            # Ensure data structures exist
            if 'activity' not in filtered_data:
                filtered_data['activity'] = {'daily_submissions': []}
            elif 'daily_submissions' not in filtered_data['activity']:
                filtered_data['activity']['daily_submissions'] = []

            if 'gradebook' not in filtered_data:
                filtered_data['gradebook'] = []

            if 'teacher_comments' not in filtered_data:
                filtered_data['teacher_comments'] = []

            return render_template('dashboard.html', user=filtered_data)
        else:
            app.logger.error("User data could not be loaded")
            flash("User data could not be loaded", "error")
            return render_template('dashboard.html')
    except Exception as e:
        app.logger.error(f"Error loading user data: {str(e)}")
        flash("Could not load user data", "error")
        return render_template('dashboard.html')


@app.route('/courses')
def courses():
    return render_template('courses.html')


@app.route('/add_question', methods=['GET', 'POST'])
def add_question():
    form = QuestionForm()
    attachment_form = AttachmentForm()
    all_tags = TagManager.get_all_tags()

    if form.validate_on_submit():
        selected_tag_ids = request.form.getlist('selected_tags')

        if not selected_tag_ids:
            flash('Please select at least one tag for the question.', 'error')
            return render_template('add_question.html', 
                                  form=form, 
                                  attachment_form=attachment_form, 
                                  all_tags=all_tags)

        question_id = str(uuid.uuid4())

        # Process URL attachments
        urls = request.form.getlist('attachment_url')
        url_attachments = [
            {
                'id': str(uuid.uuid4()),
                'type': 'url',
                'url': url.strip(),
                'description': 'URL Link'
            }
            for url in urls if url.strip()
        ]

        # Process hints
        hints = _process_hints_from_form(request.form)

        new_question = {
            'id': question_id,
            'name': form.name.data,
            'content': form.content.data,
            'answer': form.answer.data,
            'svg': '',
            'svg_generated': False,
            'rating': float(form.rating.data),
            'tags': selected_tag_ids,
            'deleted': False,
            'attachments': url_attachments,
            'hints': hints
        }

        # Process file uploads
        if 'attachment_file' in request.files:
            file_attachments = _process_file_uploads(request.files.getlist('attachment_file'), question_id)
            if file_attachments is None:  # Error occurred
                return render_template('add_question.html', 
                                      form=form, 
                                      attachment_form=attachment_form, 
                                      all_tags=all_tags)
            new_question['attachments'].extend(file_attachments)

        questions = DataManager.load_questions(include_deleted=True)
        questions.append(new_question)
        DataManager.save_questions(questions)
        flash('Question added successfully!', 'success')
        return redirect(url_for('questionbank'))

    return render_template('add_question.html', 
                          form=form, 
                          attachment_form=attachment_form, 
                          all_tags=all_tags)


@app.route('/question/<question_id>')
def view_question(question_id):
    questions = DataManager.load_questions(include_deleted=True)
    question = next((q for q in questions if q.get('id') == question_id), None)

    # Get context parameters
    creating_quiz = request.args.get('creating_quiz') == 'true'
    quiz_name = request.args.get('quiz_name', '')
    selected_quiz_tags = request.args.getlist('selected_quiz_tags')
    filter_tags = request.args.getlist('filter_tags')
    search_query = request.args.get('search_query', '')
    sort_by = request.args.get('sort_by', 'newest')

    if not question:
        flash('Question not found!', 'error')
        return redirect(url_for('index'))

    # Generate SVG if needed
    if not question.get('svg') or question.get('svg_generated') is False:
        try:
            question['svg'] = LaTeXProcessor.latex_to_svg(
                LaTeXProcessor.ensure_complete_document(question['content'])
            )
            question['svg_generated'] = True
        except Exception as e:
            app.logger.error(f"Error generating SVG for question {question.get('id')}: {str(e)}")
            question['svg'] = '/static/img/latex-placeholder.svg'
            question['svg_generated'] = False

        DataManager.save_questions(questions)

    all_tags = TagManager.get_all_tags()

    return render_template('view_question.html',
                          question=question,
                          creating_quiz=creating_quiz,
                          quiz_name=quiz_name,
                          selected_quiz_tags=selected_quiz_tags,
                          filter_tags=filter_tags,
                          search_query=search_query,
                          sort_by=sort_by,
                          get_tag_by_id=TagManager.get_tag_by_id)


@app.route('/attempt_question/<question_id>', methods=['GET', 'POST'])
def attempt_question(question_id):
    questions = DataManager.load_questions(include_deleted=True)
    question = next((q for q in questions if q.get('id') == question_id), None)

    quiz_id = request.args.get('quiz_id')
    quiz = None
    if quiz_id:
        quizzes = DataManager.load_quizzes()
        quiz = next((q for q in quizzes if q.get('id') == quiz_id), None)

    # Get context parameters
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
        submission_quiz_id = request.form.get('quiz_id')
        used_hints = request.form.getlist('used_hints')

        # Process hint data
        hint_data = _process_hint_data(used_hints, question.get('hints', []))

        is_correct = user_answer.lower() == correct_answer.lower()

        new_submission = {
            'id': str(uuid.uuid4()),
            'question_id': question_id,
            'user_answer': user_answer,
            'outcome': 'Correct' if is_correct else 'Incorrect',
            'verdict': 'Your answer is correct.' if is_correct else 'Your answer is incorrect. Please try again.',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'used_hints': used_hints,
            'hint_data': hint_data,
            'quiz_id': submission_quiz_id
        }

        submissions = DataManager.load_submissions()
        submissions.append(new_submission)
        DataManager.save_submissions(submissions)

        flash(new_submission['verdict'], 'success' if is_correct else 'error')

        if is_correct and submission_quiz_id:
            return redirect(url_for('attempt_quiz', quiz_id=submission_quiz_id))

        # Return with context parameters
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

    # Generate SVG if needed
    if not question.get('svg') or question.get('svg_generated') is False:
        try:
            question['svg'] = LaTeXProcessor.latex_to_svg(
                LaTeXProcessor.ensure_complete_document(question['content'])
            )
            question['svg_generated'] = True
        except Exception as e:
            app.logger.error(f"Error generating SVG for question {question.get('id')}: {str(e)}")
            question['svg'] = '/static/img/latex-placeholder.svg'
            question['svg_generated'] = False

        DataManager.save_questions(questions)

    # Get submissions for this question
    all_submissions = DataManager.load_submissions()
    question_submissions = [s for s in all_submissions if s['question_id'] == question_id]
    question_submissions.sort(key=lambda x: x['timestamp'], reverse=True)

    return render_template('attempt_question.html',
                           question=question,
                           get_tag_by_id=TagManager.get_tag_by_id,
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
    questions = DataManager.load_questions(include_deleted=True)
    question = next((q for q in questions if q.get('id') == question_id), None)

    if not question:
        flash('Question not found!', 'error')
        return redirect(url_for('questionbank'))

    form = QuestionForm()
    attachment_form = AttachmentForm()
    all_tags = TagManager.get_all_tags()

    if request.method == 'GET':
        if 'name' in question:
            form.name.data = question['name']
        form.content.data = question['content']
        form.answer.data = question.get('answer', '')
        form.rating.data = question['rating']

    if form.validate_on_submit():
        question['deleted'] = True

        selected_tag_ids = request.form.getlist('selected_tags')

        if not selected_tag_ids:
            flash('Please select at least one tag for the question.', 'error')
            return render_template('edit_question.html', 
                                  form=form, 
                                  attachment_form=attachment_form, 
                                  question=question, 
                                  all_tags=all_tags)

        new_question_id = str(uuid.uuid4())

        # Handle existing attachments
        kept_attachments = _process_kept_attachments(request.form, question, new_question_id)

        # Add new URL attachments
        urls = request.form.getlist('attachment_url')
        for url in urls:
            if url.strip():
                kept_attachments.append({
                    'id': str(uuid.uuid4()),
                    'type': 'url',
                    'url': url.strip(),
                    'description': 'URL Link'
                })

        new_question = {
            'id': new_question_id,
            'name': form.name.data,
            'content': form.content.data,
            'answer': form.answer.data,
            'svg': question.get('svg', ''),
            'svg_generated': False,
            'rating': float(form.rating.data),
            'tags': selected_tag_ids,
            'deleted': False,
            'edited_from': question_id,
            'attachments': kept_attachments,
            'hints': question.get('hints', [])
        }

        # Process new file uploads
        if 'attachment_file' in request.files:
            file_attachments = _process_file_uploads(request.files.getlist('attachment_file'), 
                                                    new_question_id, kept_attachments)
            if file_attachments is None:  # Error occurred
                return render_template('edit_question.html', 
                                      form=form, 
                                      attachment_form=attachment_form,
                                      question=question, 
                                      all_tags=all_tags)
            new_question['attachments'].extend(file_attachments)

        questions.append(new_question)
        DataManager.save_questions(questions)
        flash('Question updated successfully!', 'success')
        return redirect(url_for('view_question', question_id=new_question_id))

    return render_template('edit_question.html', 
                          form=form, 
                          attachment_form=attachment_form, 
                          question=question, 
                          all_tags=all_tags)


@app.route('/delete_question/<question_id>', methods=['GET', 'POST'])
def delete_question(question_id):
    questions = DataManager.load_questions(include_deleted=True)
    question = next((q for q in questions if q.get('id') == question_id), None)

    if not question:
        flash('Question not found!', 'error')
    else:
        question['deleted'] = True
        DataManager.save_questions(questions)
        flash('Question deleted successfully!', 'success')

    return redirect(url_for('questionbank'))


@app.route('/download/<question_id>/<attachment_id>')
def download_attachment(question_id, attachment_id):
    questions = DataManager.load_questions(include_deleted=True)
    question = next((q for q in questions if q.get('id') == question_id), None)

    if not question:
        flash('Question not found!', 'error')
        return redirect(url_for('index'))

    attachment = next((a for a in question.get('attachments', []) if a.get('id') == attachment_id), None)

    if not attachment:
        flash('Attachment not found!', 'error')
        return redirect(url_for('view_question', question_id=question_id))

    if attachment.get('type') == 'url':
        return redirect(attachment['url'])
    else:
        attachment_dir = os.path.dirname(os.path.join(app.config['UPLOAD_FOLDER'], attachment['path']))
        filename = os.path.basename(attachment['path'])
        is_pdf = attachment.get('file_type') == 'pdf' or filename.lower().endswith('.pdf')

        return send_from_directory(attachment_dir, filename, as_attachment=not is_pdf,
                                  download_name=attachment['original_filename'])


@app.route('/remove_attachment/<question_id>/<attachment_id>', methods=['POST'])
def remove_attachment(question_id, attachment_id):
    questions = DataManager.load_questions(include_deleted=True)
    question = next((q for q in questions if q.get('id') == question_id), None)

    if not question:
        flash('Question not found!', 'error')
        return redirect(url_for('index'))

    attachments = question.get('attachments', [])
    attachment = next((a for a in attachments if a.get('id') == attachment_id), None)

    if attachment:
        attachments.remove(attachment)
        FileManager.remove_attachment_file(attachment)
        DataManager.save_questions(questions)
        flash('Attachment removed successfully!', 'success')
    else:
        flash('Attachment not found!', 'error')

    return redirect(url_for('view_question', question_id=question_id))


# API Routes
@app.route('/api/tags', methods=['GET', 'POST', 'PUT', 'DELETE'])
def manage_tags():
    """API endpoint to manage tags"""
    return _handle_tag_management(DataManager.load_tags, DataManager.save_tags, 
                                 DataManager.load_questions, DataManager.save_questions)


@app.route('/api/quiz_tags', methods=['GET', 'POST', 'PUT', 'DELETE'])
def manage_quiz_tags():
    """API endpoint to manage quiz tags"""
    return _handle_tag_management(DataManager.load_quiz_tags, DataManager.save_quiz_tags,
                                 DataManager.load_quizzes, DataManager.save_quizzes)


@app.route('/api/questions/<question_id>/hints', methods=['POST'])
def add_hint(question_id):
    """API endpoint to add a hint to a question"""
    try:
        data = request.get_json()
        if not data or 'text' not in data or 'weight' not in data:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400

        hint_text = data['text'].strip()
        word_count = len(hint_text.split())
        if word_count > 50:
            return jsonify({'success': False, 'error': f'Hint text must be 50 words or less (currently {word_count} words)'}), 400

        try:
            weight = int(data['weight'])
            if weight < 1 or weight > 10:
                return jsonify({'success': False, 'error': 'Weight must be between 1 and 10'}), 400
        except ValueError:
            return jsonify({'success': False, 'error': 'Weight must be an integer'}), 400

        questions = DataManager.load_questions(include_deleted=True)
        question = next((q for q in questions if q.get('id') == question_id), None)

        if not question:
            return jsonify({'success': False, 'error': 'Question not found'}), 404

        new_hint = {
            'id': str(uuid.uuid4()),
            'text': hint_text,
            'weight': weight
        }

        if 'hints' not in question:
            question['hints'] = []
        question['hints'].append(new_hint)
        DataManager.save_questions(questions)

        return jsonify({'success': True, 'hint': new_hint})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/questions/<question_id>/hints/<hint_id>', methods=['PUT'])
def update_hint(question_id, hint_id):
    """API endpoint to update a hint"""
    try:
        data = request.get_json()
        if not data or ('text' not in data and 'weight' not in data):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400

        if 'text' in data:
            hint_text = data['text'].strip()
            word_count = len(hint_text.split())
            if word_count > 50:
                return jsonify({'success': False, 'error': f'Hint text must be 50 words or less (currently {word_count} words)'}), 400

        if 'weight' in data:
            try:
                weight = int(data['weight'])
                if weight < 1 or weight > 10:
                    return jsonify({'success': False, 'error': 'Weight must be between 1 and 10'}), 400
            except ValueError:
                return jsonify({'success': False, 'error': 'Weight must be an integer'}), 400

        questions = DataManager.load_questions(include_deleted=True)
        question = next((q for q in questions if q.get('id') == question_id), None)

        if not question:
            return jsonify({'success': False, 'error': 'Question not found'}), 404

        hint = next((h for h in question.get('hints', []) if h.get('id') == hint_id), None)
        if not hint:
            return jsonify({'success': False, 'error': 'Hint not found'}), 404

        if 'text' in data:
            hint['text'] = hint_text
        if 'weight' in data:
hint['weight'] = weight

        DataManager.save_questions(questions)
        return jsonify({'success': True, 'hint': hint})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/questions/<question_id>/hints/<hint_id>', methods=['DELETE'])
def delete_hint(question_id, hint_id):
    """API endpoint to delete a hint"""
    try:
        questions = DataManager.load_questions(include_deleted=True)
        question = next((q for q in questions if q.get('id') == question_id), None)

        if not question:
            return jsonify({'success': False, 'error': 'Question not found'}), 404

        hint = next((h for h in question.get('hints', []) if h.get('id') == hint_id), None)
        if not hint:
            return jsonify({'success': False, 'error': 'Hint not found'}), 404

        question['hints'].remove(hint)
        DataManager.save_questions(questions)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/quizzes/<quiz_id>/delete', methods=['GET', 'POST'])
def delete_quiz(quiz_id):
    quizzes = DataManager.load_quizzes()
    quiz = next((q for q in quizzes if q['id'] == quiz_id), None)

    if not quiz:
        flash('Quiz not found.', 'danger')
    else:
        quiz['deleted'] = True
        DataManager.save_quizzes(quizzes)
        flash('Quiz deleted successfully.', 'success')

    return redirect(url_for('quizzes'))


@app.route('/quizzes/<quiz_id>/restore', methods=['GET', 'POST'])
def restore_quiz(quiz_id):
    quizzes = DataManager.load_quizzes()
    quiz = next((q for q in quizzes if q['id'] == quiz_id), None)

    if not quiz:
        flash('Quiz not found.', 'danger')
    else:
        quiz['deleted'] = False
        DataManager.save_quizzes(quizzes)
        flash('Quiz restored successfully.', 'success')

    return redirect(url_for('quizzes'))


@app.route('/debug/user_data')
def debug_user_data():
    """Debug route to view user data as JSON"""
    try:
        user_data = load_user_data()
        if user_data:
            return jsonify(user_data)
        else:
            return jsonify({"error": "User data could not be loaded"}), 500
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# Helper functions
def _get_filtered_questions(filter_tags=None, search_query='', sort_by='newest'):
    """Get filtered and sorted questions with SVGs generated"""
    all_questions = DataManager.load_questions(include_deleted=True)
    questions = [q for q in all_questions if not q.get('deleted', False)]

    _ensure_question_svgs(questions, all_questions)

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


def _ensure_question_svgs(questions, all_questions):
    """Ensure SVGs are generated for questions"""
    updated = False
    for question in questions:
        if not question.get('svg') or question.get('svg_generated') is False:
            try:
                question['svg'] = LaTeXProcessor.latex_to_svg(
                    LaTeXProcessor.ensure_complete_document(question['content'])
                )
                question['svg_generated'] = True
            except Exception as e:
                app.logger.error(f"Error generating SVG for question {question.get('id')}: {str(e)}")
                question['svg'] = '/static/img/latex-placeholder.svg'
                question['svg_generated'] = False
            updated = True

    if updated:
        DataManager.save_questions(all_questions)


def _process_hints_from_form(form_data):
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


def _process_file_uploads(files, question_id, existing_attachments=None):
    """Process file uploads and return attachments or None on error"""
    valid_files = [f for f in files if f and f.filename]

    if not valid_files:
        return []

    # Validate files
    if existing_attachments:
        # Count existing files for validation
        all_files = valid_files + [
            type('obj', (object,), {'filename': a.get('original_filename', '')})
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
            ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'unknown'
            flash(f'File type {ext} is not allowed', 'error')
            return None

    return file_attachments


def _process_kept_attachments(form_data, question, new_question_id):
    """Process attachments to keep from existing question"""
    kept_attachments = []
    for attachment_id in form_data.getlist('keep_attachment'):
        attachment = next((a for a in question.get('attachments', []) if a.get('id') == attachment_id), None)
        if attachment:
            kept_attachments.append(attachment)
            FileManager.copy_attachment(attachment, question['id'], new_question_id)

    return kept_attachments


def _process_hint_data(used_hints, hints):
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
            hint_data.append({
                'id': hint_id,
                'position': 0
            })

    return hint_data


def _handle_tag_management(load_func, save_func, load_items_func, save_items_func):
    """Generic tag management handler"""
    tags = load_func()

    if request.method == 'GET':
        return jsonify(tags)

    elif request.method == 'POST':
        data = request.get_json()
        if not data or 'display_name' not in data:
            return jsonify({'success': False, 'error': 'No display name provided'}), 400

        tag_id = data.get('id', data['display_name'].lower().replace(' ', '_'))

        if any(tag['id'] == tag_id for tag in tags):
            return jsonify({'success': False, 'error': 'Tag ID already exists'}), 400

        new_tag = {
            'id': tag_id,
            'display_name': data['display_name']
        }
        tags.append(new_tag)
        save_func(tags)

        return jsonify({'success': True, 'tag': new_tag})

    elif request.method == 'PUT':
        data = request.get_json()
        if not data or 'id' not in data or 'display_name' not in data:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400

        tag_to_update = next((tag for tag in tags if tag['id'] == data['id']), None)
        if not tag_to_update:
            return jsonify({'success': False, 'error': 'Tag not found'}), 404

        tag_to_update['display_name'] = data['display_name']
        save_func(tags)

        return jsonify({'success': True, 'tag': tag_to_update})

    elif request.method == 'DELETE':
        data = request.get_json()
        if not data or 'id' not in data:
            return jsonify({'success': False, 'error': 'No tag ID provided'}), 400

        tag_to_delete = next((tag for tag in tags if tag['id'] == data['id']), None)
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


# Make tag helper functions available in templates
@app.context_processor
def inject_tag_helpers():
    return {
        'get_tag_by_id': TagManager.get_tag_by_id,
        'get_tag_display_name': TagManager.get_tag_display_name,
        'get_quiz_tag_by_id': TagManager.get_quiz_tag_by_id,
        'get_quiz_tag_display_name': TagManager.get_quiz_tag_display_name
    }