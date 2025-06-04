#!/usr/bin/env python3
"""
Method 1: pdflatex → pdf2svg
Use pdflatex to generate PDF, then pdf2svg (poppler) to convert to SVG.
"""

import shutil
from pathlib import Path
from test_utils import TEST_DIR, get_robust_latex_content, get_simple_latex_content, get_minimal_latex_content, run_command_with_timeout

def test_method1():
    """
    Test Method 1: pdflatex → pdf2svg
    
    Requirements:
    - pdflatex (texlive)
    - pdf2svg (poppler-based)
    """
    method_name = "Method 1: pdflatex → pdf2svg"
    print(f"\n--- Testing {method_name} ---")
    
    result = {
        'overall_success': False,
        'steps': {},
        'files_created': [],
        'method_name': method_name
    }
    
    # Try robust content first, fallback to simple if needed
    latex_content = get_robust_latex_content("Method 1 - pdflatex")
    input_file = TEST_DIR / "input" / "method1_input.tex"
    fallback_used = False
    
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
    
    # Create a temporary directory for pdflatex auxiliary files
    temp_dir = TEST_DIR / "temp" / "method1"
    temp_dir.mkdir(exist_ok=True)
    
    # Step 1: Run pdflatex to generate PDF
    print("Step 1: Generating PDF with pdflatex...")
    pdf_result = run_command_with_timeout([
        "pdflatex", 
        "-interaction=nonstopmode",
        "-output-directory", str(temp_dir),
        str(input_file)
    ])
    
    # Check if PDF was actually created (pdflatex may return non-zero even on success)
    temp_pdf = temp_dir / "method1_input.pdf"
    if temp_pdf.exists():
        pdf_result['success'] = True
        print(f"PDF generation successful - robust content worked! ({pdf_result['duration']:.2f}s)")
    
    result['steps']['pdf_generation'] = pdf_result
    
    # If PDF generation failed and we haven't tried fallback yet, try simple content
    if not pdf_result['success'] and not fallback_used:
        print("PDF generation failed with robust content. Trying simple fallback...")
        print(f"Error details: {pdf_result['stderr'][:200]}..." if pdf_result['stderr'] else "No error details")
        
        # Try simple content
        latex_content = get_simple_latex_content("Method 1 - pdflatex (Simple)")
        fallback_file = TEST_DIR / "input" / "method1_input_simple.tex"
        
        try:
            with open(fallback_file, "w", encoding='utf-8') as f:
                f.write(latex_content)
            result['files_created'].append(str(fallback_file))
            print(f"Created fallback input file: {fallback_file}")
            
            # Try PDF generation again with simple content
            pdf_result = run_command_with_timeout([
                "pdflatex", 
                "-interaction=nonstopmode",
                "-output-directory", str(temp_dir),
                str(fallback_file)
            ])
            
            result['steps']['pdf_generation_fallback'] = pdf_result
            fallback_used = True
            
            if pdf_result['success']:
                print(f"PDF generation with simple content successful ({pdf_result['duration']:.2f}s)")
                # Update the PDF file path for the simple version
                temp_pdf = temp_dir / "method1_input_simple.pdf"
            else:
                print(f"PDF generation failed even with simple content: {pdf_result['stderr'][:200]}..." if pdf_result['stderr'] else "No error details")
                
                # Try minimal content as last resort
                print("Trying minimal content as last resort...")
                minimal_content = get_minimal_latex_content("Method 1 - pdflatex (Minimal)")
                minimal_file = TEST_DIR / "input" / "method1_input_minimal.tex"
                
                try:
                    with open(minimal_file, "w", encoding='utf-8') as f:
                        f.write(minimal_content)
                    result['files_created'].append(str(minimal_file))
                    print(f"Created minimal input file: {minimal_file}")
                    
                    # Try PDF generation with minimal content
                    pdf_result = run_command_with_timeout([
                        "pdflatex", 
                        "-interaction=nonstopmode",
                        "-output-directory", str(temp_dir),
                        str(minimal_file)
                    ])
                    
                    result['steps']['pdf_generation_minimal'] = pdf_result
                    
                    if pdf_result['success']:
                        print(f"PDF generation with minimal content successful ({pdf_result['duration']:.2f}s)")
                        temp_pdf = temp_dir / "method1_input_minimal.pdf"
                        fallback_used = True
                    else:
                        print(f"PDF generation failed even with minimal content: {pdf_result['stderr'][:300]}..." if pdf_result['stderr'] else "No error details")
                        
                except Exception as e:
                    print(f"Failed to create minimal content: {e}")
                    
        except Exception as e:
            print(f"Failed to create fallback content: {e}")
    
    if pdf_result['success']:
        print(f"PDF generation successful ({pdf_result['duration']:.2f}s)")
        
        # Copy the resulting PDF to the pdf directory
        pdf_file = TEST_DIR / "pdf" / "method1_output.pdf"
        if fallback_used:
            if (temp_dir / "method1_input_minimal.pdf").exists():
                temp_pdf = temp_dir / "method1_input_minimal.pdf"
            else:
                temp_pdf = temp_dir / "method1_input_simple.pdf"
        else:
            temp_pdf = temp_dir / "method1_input.pdf"
        
        if temp_pdf.exists():
            try:
                shutil.copy(temp_pdf, pdf_file)
                result['files_created'].append(str(pdf_file))
                print(f"PDF copied to: {pdf_file}")
            except Exception as e:
                result['steps']['pdf_copy'] = {
                    'success': False,
                    'error': str(e),
                    'duration': 0,
                    'returncode': -4
                }
                return result
        else:
            result['steps']['pdf_copy'] = {
                'success': False,
                'error': 'PDF file not generated',
                'duration': 0,
                'returncode': -5
            }
            return result
        
        # Step 2: Convert PDF to SVG using pdf2svg
        print("Step 2: Converting PDF to SVG with pdf2svg...")
        svg_file = TEST_DIR / "svg" / "method1_output.svg"
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
        print(f"PDF generation failed: {pdf_result['error']}")
        print(f"Return code: {pdf_result['returncode']}")
        if pdf_result['stderr']:
            print(f"Error output: {pdf_result['stderr'][:500]}...")
        if pdf_result['stdout']:
            print(f"LaTeX output: {pdf_result['stdout'][:500]}...")
    
    return result

if __name__ == "__main__":
    result = test_method1()
    print(f"\nMethod 1 result: {'SUCCESS' if result['overall_success'] else 'FAILED'}") 