import json
import os

print("Starting JSON fix script...")

try:
    # Read the file content
    with open('user.json', 'r') as f:
        content = f.read().strip()
    
    # Remove any trailing characters after the closing brace
    content = content.rstrip()
    if content.endswith('%'):
        content = content[:-1].rstrip()
    
    # Make sure the content ends with a proper closing brace
    if not content.endswith('}'):
        last_brace = content.rfind('}')
        if last_brace > 0:
            content = content[:last_brace+1]
    
    print(f"Cleaned content: {content[-20:]}")
    
    # Parse the JSON to verify it's valid
    json_data = json.loads(content)
    
    # Write the cleaned content back to file
    with open('user.json', 'w') as f:
        json.dump(json_data, f, indent=2)
    
    print("JSON file fixed successfully!")
    
except Exception as e:
    print(f"Error fixing JSON: {str(e)}") 