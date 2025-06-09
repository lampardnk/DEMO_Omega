
from flask import render_template, request, redirect, url_for, flash
from app import app
from app.utils.data_manager import DataManager, TagManager
from app.utils.quiz_utils import get_filtered_quizzes, create_new_quiz, get_quiz_progress, validate_quiz_form
from app.utils.question_utils import get_filtered_questions, ensure_question_svgs


@app.route('/quizzes')
def quizzes():
    search_query = request.args.get('search', '').strip().lower()
    filter_tags = request.args.getlist('tags')
    sort_by = request.args.get('sort', 'newest')
    show_deleted = request.args.get('show_deleted') == 'true'

    filtered_quizzes = get_filtered_quizzes(search_query, filter_tags, sort_by, show_deleted)
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

    questions = get_filtered_questions(filter_tags, search_query, sort_by)

    if request.method == 'POST':
        name = request.form.get('quiz_name', '').strip()
        selected_tags = request.form.getlist('selected_tags')
        question_ids = request.form.getlist('question_ids')

        if not validate_quiz_form(name, question_ids):
            return render_template('create_quiz.html',
                                   questions=questions,
                                   all_quiz_tags=quiz_tags,
                                   all_tags=all_tags,
                                   filter_tags=filter_tags,
                                   search_query=search_query,
                                   sort_by=sort_by)

        new_quiz = create_new_quiz(name, selected_tags, question_ids)
        quizzes = DataManager.load_quizzes()
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
    questions = get_filtered_questions()

    if request.method == 'POST':
        name = request.form.get('quiz_name', '').strip()
        selected_tags = request.form.getlist('selected_tags')
        question_ids = request.form.getlist('question_ids')

        if not validate_quiz_form(name, question_ids):
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
    quiz_questions = [
        q for q in all_questions if q['id'] in quiz['question_ids']
    ]

    # Generate SVGs
    ensure_question_svgs(quiz_questions, all_questions)

    # Calculate progress
    progress_data = get_quiz_progress(quiz_id, quiz_questions)

    return render_template('attempt_quiz.html',
                           quiz=quiz,
                           questions=quiz_questions,
                           progress=progress_data['progress'],
                           completed_questions=progress_data['completed_question_ids'])


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
