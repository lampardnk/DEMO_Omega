
import os
from flask import render_template, request, redirect, url_for, flash, send_from_directory
from app import app
from app.forms import QuestionForm, AttachmentForm
from app.utils.data_manager import DataManager, TagManager
from app.utils.question_utils import (
    get_filtered_questions, generate_question_svg, create_new_question,
    create_submission
)
from app.utils.attachment_utils import (
    process_file_uploads, process_kept_attachments, process_url_attachments
)
from app.utils.file_manager import FileManager
from app.utils.form_validators import validate_question_form


@app.route('/questionbank')
def questionbank():
    show_deleted = request.args.get('show_deleted', 'false').lower() == 'true'
    filter_tags = request.args.getlist('tags')
    sort_by = request.args.get('sort', 'newest')
    search_query = request.args.get('search', '').strip().lower()

    questions = DataManager.load_questions(include_deleted=show_deleted)

    # Apply filters
    if filter_tags:
        questions = [
            q for q in questions
            if any(tag in q.get('tags', []) for tag in filter_tags)
        ]

    if search_query:
        questions = [
            q for q in questions if search_query in q.get('name', '').lower()
            or search_query in q.get('content', '').lower()
        ]

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
            generate_question_svg(question)
            updated = True

    if updated:
        DataManager.save_questions(
            DataManager.load_questions(include_deleted=True))

    all_tags = TagManager.get_all_tags()

    return render_template('index.html',
                           questions=questions,
                           filter_tags=filter_tags,
                           sort_by=sort_by,
                           all_tags=all_tags,
                           show_deleted=show_deleted,
                           search_query=search_query)


@app.route('/add_question', methods=['GET', 'POST'])
def add_question():
    form = QuestionForm()
    attachment_form = AttachmentForm()
    all_tags = TagManager.get_all_tags()

    if form.validate_on_submit():
        selected_tag_ids = request.form.getlist('selected_tags')

        if not validate_question_form(selected_tag_ids):
            return render_template('add_question.html',
                                   form=form,
                                   attachment_form=attachment_form,
                                   all_tags=all_tags)

        new_question = create_new_question(request.form, selected_tag_ids)

        # Process file uploads
        if 'attachment_file' in request.files:
            file_attachments = process_file_uploads(
                request.files.getlist('attachment_file'), new_question['id'])
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

    generate_question_svg(question)
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

        new_submission = create_submission(
            question_id, user_answer, correct_answer, 
            submission_quiz_id, used_hints
        )

        submissions = DataManager.load_submissions()
        submissions.append(new_submission)
        DataManager.save_submissions(submissions)

        is_correct = new_submission['outcome'] == 'Correct'
        flash(new_submission['verdict'], 'success' if is_correct else 'error')

        if is_correct and submission_quiz_id:
            return redirect(url_for('attempt_quiz', quiz_id=submission_quiz_id))

        # Return with context parameters
        if creating_quiz:
            return redirect(
                url_for('attempt_question',
                        question_id=question_id,
                        quiz_id=quiz_id,
                        creating_quiz=creating_quiz,
                        quiz_name=quiz_name,
                        selected_quiz_tags=selected_quiz_tags,
                        filter_tags=filter_tags,
                        search_query=search_query,
                        sort_by=sort_by))
        else:
            return redirect(
                url_for('attempt_question',
                        question_id=question_id,
                        quiz_id=quiz_id))

    generate_question_svg(question)
    DataManager.save_questions(questions)

    # Get submissions for this question
    all_submissions = DataManager.load_submissions()
    question_submissions = [
        s for s in all_submissions if s['question_id'] == question_id
    ]
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

        if not validate_question_form(selected_tag_ids):
            return render_template('edit_question.html',
                                   form=form,
                                   attachment_form=attachment_form,
                                   question=question,
                                   all_tags=all_tags)

        new_question = create_new_question(request.form, selected_tag_ids)
        new_question['edited_from'] = question_id
        new_question['svg'] = question.get('svg', '')
        new_question['hints'] = question.get('hints', [])

        # Handle existing attachments
        kept_attachments = process_kept_attachments(request.form, question, new_question['id'])
        new_question['attachments'] = kept_attachments

        # Add new URL attachments
        urls = request.form.getlist('attachment_url')
        new_question['attachments'].extend(process_url_attachments(urls))

        # Process new file uploads
        if 'attachment_file' in request.files:
            file_attachments = process_file_uploads(
                request.files.getlist('attachment_file'), new_question['id'],
                kept_attachments)
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
        return redirect(url_for('view_question', question_id=new_question['id']))

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

    attachment = next((a for a in question.get('attachments', [])
                       if a.get('id') == attachment_id), None)

    if not attachment:
        flash('Attachment not found!', 'error')
        return redirect(url_for('view_question', question_id=question_id))

    if attachment.get('type') == 'url':
        return redirect(attachment['url'])
    else:
        attachment_dir = os.path.dirname(
            os.path.join(app.config['UPLOAD_FOLDER'], attachment['path']))
        filename = os.path.basename(attachment['path'])
        is_pdf = attachment.get(
            'file_type') == 'pdf' or filename.lower().endswith('.pdf')

        return send_from_directory(
            attachment_dir,
            filename,
            as_attachment=not is_pdf,
            download_name=attachment['original_filename'])


@app.route('/remove_attachment/<question_id>/<attachment_id>', methods=['POST'])
def remove_attachment(question_id, attachment_id):
    questions = DataManager.load_questions(include_deleted=True)
    question = next((q for q in questions if q.get('id') == question_id), None)

    if not question:
        flash('Question not found!', 'error')
        return redirect(url_for('index'))

    attachments = question.get('attachments', [])
    attachment = next((a for a in attachments if a.get('id') == attachment_id),
                      None)

    if attachment:
        attachments.remove(attachment)
        FileManager.remove_attachment_file(attachment)
        DataManager.save_questions(questions)
        flash('Attachment removed successfully!', 'success')
    else:
        flash('Attachment not found!', 'error')

    return redirect(url_for('view_question', question_id=question_id))
