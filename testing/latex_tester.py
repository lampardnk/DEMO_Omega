#!/usr/bin/env python3
"""
LaTeX to SVG Renderer - Testing Script

This script renders LaTeX files to SVG using command-line tools.
It processes files from two directories:
- basic: Contains simple LaTeX environments
- mixed: Contains LaTeX files with mixed environments
"""

import os
import sys
import argparse
import subprocess
import tempfile
import base64
import glob
from pathlib import Path


def check_requirements():
    """Check if required command-line tools are installed."""
    requirements = ['pdflatex', 'pdf2svg']
    missing = []
    
    for cmd in requirements:
        try:
            subprocess.run(['which', cmd], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError:
            missing.append(cmd)
    
    if missing:
        print(f"ERROR: Missing required tools: {', '.join(missing)}")
        print("Please install them with:")
        print("  brew install texlive pdf2svg")
        sys.exit(1)


def detect_environments(tex_content):
    """Detect LaTeX environments in the content."""
    environments = []
    
    # Common LaTeX environments to check for
    env_patterns = [
        'document', 'tikzpicture', 'circuitikz', 'scope',
        'align', 'question', 'part', 'subpart', 'tabular'
    ]
    
    for env in env_patterns:
        if f'\\begin{{{env}}}' in tex_content:
            environments.append(env)
    
    return environments


def latex_to_svg(input_file, output_file):
    """Convert a LaTeX file to SVG using command-line tools."""
    # Read the LaTeX content
    with open(input_file, 'r') as f:
        latex_content = f.read()
    
    # Detect environments
    environments = detect_environments(latex_content)
    print(f"Detected environments: {', '.join(environments)}")
    
    # Create a full LaTeX document if the content doesn't have a document environment
    if 'document' not in environments:
        # Build the preamble
        preamble = ["\\documentclass[border=10pt]{standalone}", "\\usepackage{amsmath,amssymb}"]
        
        # Add required packages based on environments
        if 'tikzpicture' in environments or 'scope' in environments:
            preamble.append("\\usepackage{tikz}")
        if 'circuitikz' in environments:
            preamble.append("\\usepackage{circuitikz}")
        if 'align' in environments:
            preamble.append("\\usepackage{amsmath}")
        
        # Handle exam-specific environments
        if any(env in environments for env in ['question', 'part', 'subpart']):
            # For exam environments, we need to use the article class and exam package
            preamble = ["\\documentclass{article}", "\\usepackage{amsmath,amssymb}", "\\usepackage{exam}"]
            # Wrap the content in a proper exam structure
            latex_content = f"""\\begin{{questions}}
{latex_content}
\\end{{questions}}"""
        
        # Build the complete document
        full_latex = preamble + ["\\begin{document}", latex_content, "\\end{document}"]
        latex_content = '\n'.join(full_latex)
    
    # Special handling for align environment without document
    if 'align' in environments and 'document' not in environments:
        # For standalone align, use article class instead of standalone
        latex_content = latex_content.replace("\\documentclass[border=10pt]{standalone}", "\\documentclass{article}")
    
    # Create a temporary directory for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Write the LaTeX content to a temporary file
        tex_file = os.path.join(temp_dir, "content.tex")
        with open(tex_file, "w") as f:
            f.write(latex_content)
        
        try:
            # Run pdflatex to create PDF
            print(f"Running pdflatex on {input_file}...")
            subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-output-directory", temp_dir, tex_file],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Convert PDF to SVG using pdf2svg
            pdf_file = os.path.join(temp_dir, "content.pdf")
            
            print(f"Converting to SVG: {output_file}")
            subprocess.run(
                ["pdf2svg", pdf_file, output_file],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            print(f"Successfully created SVG: {output_file}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Error processing {input_file}: {e}")
            # Create an error SVG
            with open(output_file, 'w') as f:
                f.write(f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="500" height="100">
    <text x="10" y="30" fill="red">LaTeX Error processing {os.path.basename(input_file)}</text>
    <text x="10" y="60" fill="red">{str(e)}</text>
</svg>''')
            return False


def process_directory(input_dir, output_dir=None):
    """Process all .tex files in a directory and convert them to SVG."""
    if output_dir is None:
        output_dir = input_dir
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Get all .tex files in the directory
    tex_files = glob.glob(os.path.join(input_dir, "*.tex"))
    
    if not tex_files:
        print(f"No .tex files found in {input_dir}")
        return
    
    success_count = 0
    total_count = len(tex_files)
    
    for tex_file in tex_files:
        base_name = os.path.basename(tex_file)
        name_without_ext = os.path.splitext(base_name)[0]
        svg_file = os.path.join(output_dir, f"{name_without_ext}.svg")
        
        print(f"\nProcessing: {tex_file}")
        if latex_to_svg(tex_file, svg_file):
            success_count += 1
    
    print(f"\nCompleted: {success_count}/{total_count} files successfully converted to SVG.")


def create_sample_files():
    """Create sample LaTeX files for testing."""
    samples = {
        'basic/document.tex': '''\\documentclass{article}
\\begin{document}
This is a basic document with text only.
\\end{document}''',
        
        'basic/tikzpicture.tex': '''\\begin{tikzpicture}
\\draw (0,0) circle (1cm);
\\draw (0,0) -- (1,1);
\\end{tikzpicture}''',
        
        'basic/circuitikz.tex': '''\\begin{circuitikz}
\\draw (0,0) to[R=$R_1$] (3,0) to[V=$V_1$] (3,3) to[R=$R_2$] (0,3) to[I=$I_1$] (0,0);
\\end{circuitikz}''',
        
        'basic/scope.tex': '''\\begin{tikzpicture}
\\begin{scope}[xshift=2cm]
\\draw (0,0) rectangle (1,1);
\\end{scope}
\\end{tikzpicture}''',
        
        'basic/align.tex': '''\\begin{align}
E &= mc^2 \\\\
F &= ma
\\end{align}''',
        
        'basic/question.tex': '''\\documentclass{exam}
\\begin{document}
\\begin{questions}
\\question What is the value of $\\pi$ to 2 decimal places?
\\end{questions}
\\end{document}''',
        
        'basic/part.tex': '''\\documentclass{exam}
\\begin{document}
\\begin{questions}
\\question
\\begin{parts}
\\part Calculate the derivative of $f(x) = x^2 + 3x + 2$.
\\end{parts}
\\end{questions}
\\end{document}''',
        
        'basic/subpart.tex': '''\\documentclass{exam}
\\begin{document}
\\begin{questions}
\\question
\\begin{parts}
\\part
\\begin{subparts}
\\subpart Find the value of $x$ when $y = 0$.
\\end{subparts}
\\end{parts}
\\end{questions}
\\end{document}''',
        
        'basic/tabular.tex': '''\\begin{tabular}{|c|c|c|}
\\hline
A & B & C \\\\
\\hline
1 & 2 & 3 \\\\
4 & 5 & 6 \\\\
\\hline
\\end{tabular}''',
        
        'mixed/complex1.tex': '''\\documentclass{article}
\\usepackage{tikz}
\\usepackage{amsmath}
\\begin{document}
\\begin{align}
E &= mc^2 \\\\
F &= ma
\\end{align}

\\begin{tikzpicture}
\\draw (0,0) circle (1cm);
\\draw (0,0) -- (1,1);
\\end{tikzpicture}
\\end{document}''',
        
        'mixed/complex2.tex': '''\\documentclass{article}
\\usepackage{tikz}
\\usepackage{circuitikz}
\\usepackage{amsmath}
\\usepackage{exam}
\\begin{document}
\\begin{circuitikz}
\\draw (0,0) to[R=$R_1$] (3,0) to[V=$V_1$] (3,3);
\\end{circuitikz}

\\begin{align}
I &= \\frac{V}{R} \\\\
P &= VI
\\end{align}

\\begin{questions}
\\question What is Ohm's Law?
\\begin{parts}
\\part Express it mathematically.
\\begin{subparts}
\\subpart Using the variable $I$, $V$, and $R$.
\\end{subparts}
\\end{parts}
\\end{questions}
\\end{document}''',
    }
    
    for file_path, content in samples.items():
        full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'w') as f:
            f.write(content)
        
        print(f"Created sample file: {full_path}")


def main():
    parser = argparse.ArgumentParser(description='Convert LaTeX files to SVG images.')
    parser.add_argument('--create-samples', action='store_true', help='Create sample LaTeX files for testing')
    parser.add_argument('--process-basic', action='store_true', help='Process files in the basic directory')
    parser.add_argument('--process-mixed', action='store_true', help='Process files in the mixed directory')
    parser.add_argument('--process-all', action='store_true', help='Process all directories')
    parser.add_argument('--file', type=str, help='Process a specific .tex file')
    
    args = parser.parse_args()
    
    # Check requirements
    check_requirements()
    
    # Get the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create sample files if requested
    if args.create_samples:
        create_sample_files()
    
    # Process specific file if provided
    if args.file:
        file_path = args.file
        if not os.path.isabs(file_path):
            file_path = os.path.join(script_dir, file_path)
        
        if os.path.exists(file_path):
            output_file = os.path.splitext(file_path)[0] + '.svg'
            latex_to_svg(file_path, output_file)
        else:
            print(f"File not found: {file_path}")
    
    # Process directories
    if args.process_basic or args.process_all:
        basic_dir = os.path.join(script_dir, 'basic')
        process_directory(basic_dir)
    
    if args.process_mixed or args.process_all:
        mixed_dir = os.path.join(script_dir, 'mixed')
        process_directory(mixed_dir)
    
    # If no action specified, show help
    if not (args.create_samples or args.process_basic or args.process_mixed or 
            args.process_all or args.file):
        parser.print_help()


if __name__ == '__main__':
    main() 