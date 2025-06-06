# QuestionBank and Quiz Web App

A Flask-based web application for creating, managing, and taking quizzes with support for LaTeX math expressions.

## Prerequisites

### Required System Dependencies

- Python 3.10 or higher
- LaTeX (texlive)
- pdf2svg

### Installation on Ubuntu/Debian

```bash
# Install Python and system dependencies
sudo apt update
sudo apt install python3 python3-pip python3-venv texlive pdf2svg -y

# Clone the repository and navigate to it
cd DEMO_Omega

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### Installation on macOS

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python3 mactex pdf2svg

# Clone the repository and navigate to it
cd DEMO_Omega

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

## Running the Application

```bash
# Activate the virtual environment (if not already activated)
source .venv/bin/activate

# Run the application
python run.py
```

The application will be available at http://127.0.0.1:8081/

## Project Structure

```
DEMO_Omega/
├── app/                      # Main application package
│   ├── data/                 # Data storage (JSON files)
│   │   ├── questions.json    # Question data
│   │   └── tags.json         # Tag definitions
│   ├── static/               # Static files (CSS, JS, images)
│   ├── templates/            # HTML templates
│   ├── uploads/              # Uploaded files storage
│   ├── __init__.py           # Flask application initialization
│   ├── forms.py              # Form definitions
│   └── routes.py             # Route handlers and business logic
├── config.py                 # Application configuration
├── requirements.txt          # Python dependencies
└── run.py                    # Application entry point
```

## Implemented Features

- **Question Bank Management**
  - Create, edit, and delete questions
  - LaTeX support for mathematical expressions
  - TikZ and CircuiTikZ support for diagrams
  - Tag-based question organization
  - Rating system for difficulty levels

- **File Attachments**
  - Support for multiple file types (PDF, images, videos, documents)
  - File upload validation with size and type limits
  - File downloads for question resources

- **LaTeX Rendering**
  - Server-side LaTeX to SVG conversion
  - Support for various LaTeX environments (document, tikz, circuitikz, align)
  - LaTeX preview in the question editor

- **User Interface**
  - Responsive design with Bootstrap
  - Tag filtering and search functionality
  - Collapsible example templates for question creation

## TODO Features

- **Question Attempt System**
  - Interactive question answering interface
  - Response recording and validation
  - Progress tracking

- **Hint System**
  - Multi-level hints for progressive help
  - Hint usage tracking

- **AI Marking Engine**
  - Automated assessment of student responses
  - Feedback generation for answers
  - Partial credit scoring

- **Media Viewers**
  - In-app PDF viewer
  - Integrated video player
  - Image gallery with zoom/pan

- **Submission Management**
  - View submission history
  - Detailed submission analytics
  - Performance reporting

## Notes

This application uses simple JSON files for data storage. For production use, a proper database implementation would be recommended. 