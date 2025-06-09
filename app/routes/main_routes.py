
from flask import render_template, redirect, url_for, request, flash, jsonify
from app import app
from app.data_loader import load_user_data, filter_data_by_timerange
from app.utils.data_manager import TagManager


@app.route('/')
def index():
    return redirect(url_for('questionbank'))


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
            app.logger.info(
                f"User data loaded. Name: {user_data.get('basic_info', {}).get('name')}"
            )

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


# Make tag helper functions available in templates
@app.context_processor
def inject_tag_helpers():
    return {
        'get_tag_by_id': TagManager.get_tag_by_id,
        'get_tag_display_name': TagManager.get_tag_display_name,
        'get_quiz_tag_by_id': TagManager.get_quiz_tag_by_id,
        'get_quiz_tag_display_name': TagManager.get_quiz_tag_display_name
    }
