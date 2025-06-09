import json
import os
from datetime import datetime, timedelta

def load_user_data():
    """
    Load user data from user.json
    In a real application, this would pull data from various sources
    and combine them into a single user data structure
    """
    try:
        # Try multiple paths to find the user.json file
        possible_paths = [
            # Direct path in current directory
            'user.json',
            # Path relative to the app directory
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'user.json'),
            # Absolute path based on module location
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'user.json')
        ]
        
        user_json_path = None
        for path in possible_paths:
            if os.path.exists(path):
                user_json_path = path
                break
                
        if not user_json_path:
            print("Error: Could not find user.json file")
            return None
            
        print(f"Loading user data from: {user_json_path}")
        
        with open(user_json_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Remove any unwanted characters at the end
            if content.strip().endswith('%'):
                content = content.strip()[:-1]
            user_data = json.loads(content)
            
        # Check if the loaded data has the expected structure
        if 'user' in user_data:
            print(f"User data loaded successfully. Found: {len(user_data['user'].get('gradebook', []))} grade entries, "
                  f"{len(user_data['user'].get('class_progress', []))} class progress entries, "
                  f"{len(user_data['user'].get('teacher_comments', []))} teacher comments, "
                  f"{len(user_data['user'].get('activity', {}).get('daily_submissions', []))} activity entries")
            return user_data['user']
        else:
            print("Error: User data does not have the expected structure")
            return None
    except Exception as e:
        print(f"Error loading user data: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return None

def filter_data_by_timerange(user_data, days=7):
    """
    Filter user data based on a time range
    This would be used to implement the time range selector
    """
    if not user_data:
        return user_data
    
    # Create a deep copy of the user data to avoid modifying the original
    import copy
    filtered_data = copy.deepcopy(user_data)
    
    # Calculate the cutoff date - use proper filtering
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    print(f"Filtering data with cutoff date: {cutoff_date}")
    
    # Filter gradebook
    if 'gradebook' in filtered_data:
        original_count = len(filtered_data['gradebook'])
        filtered_data['gradebook'] = [
            grade for grade in filtered_data['gradebook']
            if grade['date'] >= cutoff_date
        ]
        print(f"Filtered gradebook: {original_count} -> {len(filtered_data['gradebook'])} entries")
    
    # Filter teacher comments
    if 'teacher_comments' in filtered_data:
        original_count = len(filtered_data['teacher_comments'])
        filtered_data['teacher_comments'] = [
            comment for comment in filtered_data['teacher_comments']
            if comment['date'] >= cutoff_date
        ]
        print(f"Filtered teacher comments: {original_count} -> {len(filtered_data['teacher_comments'])} entries")
    
    # Filter activity data
    if 'activity' in filtered_data and 'daily_submissions' in filtered_data['activity']:
        original_count = len(filtered_data['activity']['daily_submissions'])
        filtered_data['activity']['daily_submissions'] = [
            submission for submission in filtered_data['activity']['daily_submissions']
            if submission['date'] >= cutoff_date
        ]
        print(f"Filtered activity submissions: {original_count} -> {len(filtered_data['activity']['daily_submissions'])} entries")
    
    # Note: We don't filter class_progress as it represents current state
    
    return filtered_data

def update_user_data():
    """
    In a real application, this function would:
    1. Pull the latest data from various sources
    2. Process and combine the data
    3. Save the updated data to user.json
    """
    # This is just a placeholder for demonstration
    # In a real application, you would fetch data from various APIs or databases
    
    # Example of how you might update the user.json file
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        user_json_path = os.path.join(base_dir, 'user.json')
        
        with open(user_json_path, 'r') as f:
            user_data = json.load(f)
        
        # Update data here...
        # For example, add a new activity record:
        # user_data['user']['activity']['daily_submissions'].append({
        #     "date": datetime.now().strftime('%Y-%m-%d'),
        #     "unique_successful": 10,
        #     "avg_rating": 4.3,
        #     "correct_percentage": 88
        # })
        
        with open(user_json_path, 'w') as f:
            json.dump(user_data, f, indent=2)
            
        return True
    except Exception as e:
        print(f"Error updating user data: {str(e)}")
        return False 