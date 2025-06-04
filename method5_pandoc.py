#!/usr/bin/env python3
"""
Method 5: pandoc pipeline
Use pandoc to process LaTeX and convert to SVG via PDF.
This method leverages pandoc's flexibility with document formats.
"""

from pathlib import Path
from test_utils import TEST_DIR, get_robust_latex_content, get_simple_latex_content, get_minimal_latex_content, run_command_with_timeout

def test_method5():
    """
    Test Method 5: pandoc pipeline
    
    Requirements:
    - pandoc
    - pdflatex or xelatex (configured in pandoc)
    - pdf2svg
    """
    method_name = "Method 5: pandoc pipeline"
    print(f"\n--- Testing {method_name} ---")
    
    result = {
        'overall_success': False,
        'steps': {},
        'files_created': [],
        'method_name': method_name
    }
    
    # Use simple content for pandoc (more reliable)
    latex_content = get_simple_latex_content("Method 5 - Pandoc Pipeline")
    input_file = TEST_DIR / "input" / "method5_input.tex"
    
    try:
        with open(input_file, "w", encoding='utf-8') as f:
            f.write(latex_content)
        result['files_created'].append(str(input_file))
        print(f"Created input file: {input_file}")
    except Exception as e:
        result['steps']['create_input'] = {
            'success': False,
            'error': str(e),
            'duration': 0,
            'returncode': -3
        }
        return result
    
    # Create a temporary directory
    temp_dir = TEST_DIR / "temp" / "method5"
    temp_dir.mkdir(exist_ok=True)
    
    # Step 1: Use pandoc to convert LaTeX to PDF
    print("Step 1: Converting LaTeX to PDF with pandoc...")
    pdf_file = TEST_DIR / "pdf" / "method5_output.pdf"
    
    pdf_result = run_command_with_timeout([
        "pandoc",
        "-f", "latex",
        "-t", "pdf",
        "-o", str(pdf_file),
        str(input_file)
    ])
    
    result['steps']['pdf_generation'] = pdf_result
    
    if pdf_result['success']:
        print(f"PDF generation via pandoc successful ({pdf_result['duration']:.2f}s)")
        result['files_created'].append(str(pdf_file))
        
        # Step 2: Convert PDF to SVG using pdf2svg
        print("Step 2: Converting PDF to SVG with pdf2svg...")
        svg_file = TEST_DIR / "svg" / "method5_output.svg"
        svg_result = run_command_with_timeout([
            "pdf2svg", 
            str(pdf_file), 
            str(svg_file)
        ])
        
        result['steps']['svg_conversion'] = svg_result
        
        if svg_result['success']:
            print(f"SVG conversion successful ({svg_result['duration']:.2f}s)")
            result['files_created'].append(str(svg_file))
            result['overall_success'] = True
            
            print(f"Success! Files created:")
            for file_path in result['files_created']:
                print(f"  - {file_path}")
        else:
            print(f"SVG conversion failed: {svg_result['error']}")
            print(f"Return code: {svg_result['returncode']}")
            if svg_result['stderr']:
                print(f"Error output: {svg_result['stderr'][:200]}...")
    else:
        print(f"PDF generation via pandoc failed: {pdf_result['error']}")
        print(f"Return code: {pdf_result['returncode']}")
        if pdf_result['stderr']:
            print(f"Error output: {pdf_result['stderr'][:200]}...")
    
    return result

if __name__ == "__main__":
    result = test_method5()
    print(f"\nMethod 5 result: {'SUCCESS' if result['overall_success'] else 'FAILED'}") 