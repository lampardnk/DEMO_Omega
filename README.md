# QuestionBank and Quiz Web App Demo

A simple demo of a question bank and quiz web application built with Flask.

## Setup Instructions for Ubuntu

### 1. Install Python and pip

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv -y
```

### 2. Clone the repository (if you haven't already)

```bash
git clone <repository-url>
cd DEMO_Omega
```

### 3. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Create .env file (for configuration)

```bash
echo "SECRET_KEY=your-secret-key-here" > .env
```

### 6. Create necessary directories (if they don't exist)

```bash
mkdir -p app/data
mkdir -p app/uploads
```

### 7. Run the application

```bash
python run.py
```

The application will be available at http://127.0.0.1:5000/

## Setup Instructions for Windows using WSL (Windows Subsystem for Linux)

If you're experiencing issues with installing Flask on Windows, you can use WSL:

### 1. Install WSL if you haven't already

Open PowerShell as Administrator and run:
```powershell
wsl --install
```

### 2. Open Ubuntu terminal from WSL

### 3. Navigate to your project directory

```bash
cd /mnt/c/Users/your-username/path-to/DEMO_Omega
```

### 4. Create a virtual environment in your home directory

```bash
cd ~
python3 -m venv myvenv
```

### 5. Use the provided activation script

```bash
cd /mnt/c/Users/your-username/path-to/DEMO_Omega
bash ./activate_venv.sh
```

### 6. Run the application

```bash
python run.py
```

The application will be available at http://127.0.0.1:5000/

## Features

- Question bank management
- Quiz creation and management
- File upload capabilities
- Interactive quiz taking

## Notes

This is a demo version with simplified data storage using JSON files. For production use, a proper database implementation would be required. 