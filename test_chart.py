import os
import sys
import json

def check_activity_data():
    """
    Test function to check if the activity chart data can be properly loaded and displayed
    """
    try:
        print("Testing activity chart data loading...")
        
        # Get the absolute path to user.json in the root directory
        user_json_path = 'user.json'
        
        # Read the file content
        with open(user_json_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Remove any unwanted characters at the end
            if content.strip().endswith('%'):
                content = content.strip()[:-1]
            user_data = json.loads(content)
            
        # Check if the loaded data has the expected structure
        if 'user' in user_data and 'activity' in user_data['user']:
            activity = user_data['user']['activity']
            if 'daily_submissions' in activity:
                submissions = activity['daily_submissions']
                print(f"Found {len(submissions)} daily submissions")
                
                # Print details of each submission
                for i, submission in enumerate(submissions):
                    print(f"Submission {i+1}:")
                    print(f"  Date: {submission.get('date')}")
                    print(f"  Unique Successful: {submission.get('unique_successful')}")
                    print(f"  Avg Rating: {submission.get('avg_rating')}")
                    print(f"  Correct Percentage: {submission.get('correct_percentage')}")
                
                # Test the rendering calculations for each submission
                print("\nRendering calculations:")
                for i, submission in enumerate(submissions):
                    position = i * 14 + 2
                    height = submission.get('unique_successful', 0) * 10
                    percentage_left = position + 7
                    
                    print(f"Submission {i+1}:")
                    print(f"  Left position: {position}%")
                    print(f"  Height: {height}px")
                    print(f"  Percentage dot left: {percentage_left}%")
                    
                return True
            else:
                print("Error: No daily_submissions found in activity data")
        else:
            print("Error: User data does not have the expected structure")
            
        return False
    except Exception as e:
        print(f"Error testing activity chart data: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    check_activity_data() 