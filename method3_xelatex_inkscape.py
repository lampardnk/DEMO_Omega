#!/usr/bin/env python3
"""
Method 3: xelatex → Inkscape
Use xelatex to generate PDF, then Inkscape to convert to SVG.
This method supports more fonts and Unicode characters.
"""

import shutil
from pathlib import Path
from test_utils import TEST_DIR, get_robust_latex_content, get_simple_latex_content, get_minimal_latex_content, run_command_with_timeout

def get_xelatex_content(method_name):
    """Get LaTeX content optimized for XeLaTeX with Unicode support."""
    return f"""\\documentclass{{article}}
\\usepackage{{fontspec}}
\\usepackage{{unicode-math}}
\\usepackage{{amsmath}}
\\usepackage{{tikz}}
\\usepackage{{circuitikz}}
\\usepackage{{exam}}
\\usepackage{{array}}
\\usepackage{{booktabs}}

\\begin{{document}}

\\title{{{method_name} Test Document}}
\\maketitle

\\section{{Mathematical Content with Unicode}}
Complex equation: $\\nabla \\times \\vec{{E}} = -\\frac{{\\partial \\vec{{B}}}}{{\\partial t}}$

Unicode math: $α + β = γ$ and $∮ \\vec{{E}} \\cdot d\\vec{{l}} = -\\frac{{d}}{{dt}}\\int_S \\vec{{B}} \\cdot \\vec{{n}} da$

\\begin{{align}}
E &= mc^2\\\\
F &= ma\\\\
∇ × E &= -∂B/∂t
\\end{{align}}

\\section{{TikZ Graphics}}
\\begin{{tikzpicture}}
\\draw[->] (-2,0) -- (2,0) node[right] {{$x$}};
\\draw[->] (0,-2) -- (0,2) node[above] {{$y$}};
\\draw[domain=-1.5:1.5,smooth,variable=\\x,blue] plot ({{\\x}},{{{{\\x}}^2-1}});
\\draw (0,0) circle (1cm);
\\end{{tikzpicture}}

\\section{{Circuit Diagrams}}
\\begin{{circuitikz}}
\\draw (0,0) to[V,v=$V_s$] (0,2) to[R,l=$R_1$] (2,2) to[R,l=$R_2$] (2,0) -- (0,0);
\\draw (2,2) to[C,l=$C$] (4,2) to[L,l=$L$] (4,0) -- (2,0);
\\end{{circuitikz}}

\\section{{Tabular Data}}
\\begin{{table}}[h]
\\centering
\\begin{{tabular}}{{|c|c|c|}}
\\hline
Method & Speed & Quality \\\\
\\hline
pdflatex & Fast & Good \\\\
xelatex & Medium & Excellent \\\\
lualatex & Medium & Very Good \\\\
\\hline
\\end{{tabular}}
\\caption{{Comparison of LaTeX engines}}
\\end{{table}}

\\section{{Exam Questions}}
\\begin{{questions}}
\\question What is the derivative of $x^2$?
\\begin{{parts}}
\\part $2x$
\\part $x$
\\part $2x^2$
\\end{{parts}}

\\question Solve for $x$: $2x + 5 = 11$
\\begin{{subparts}}
\\subpart Show your work
\\subpart Verify your answer
\\end{{subparts}}
\\end{{questions}}

\\end{{document}}
"""

def test_method3():
    """
    Test Method 3: xelatex → Inkscape
    
    Requirements:
    - xelatex (texlive with xetex)
    - inkscape
    """
    method_name = "Method 3: xelatex → Inkscape"
    print(f"\n--- Testing {method_name} ---")
    
    result = {
        'overall_success': False,
        'steps': {},
        'files_created': [],
        'method_name': method_name
    }
    
    # Try XeLaTeX content first, then fallback to simpler versions
    latex_content = get_xelatex_content("Method 3 - XeLaTeX")
    input_file = TEST_DIR / "input" / "method3_input.tex"
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
    
    # Create a temporary directory for xelatex auxiliary files
    temp_dir = TEST_DIR / "temp" / "method3"
    temp_dir.mkdir(exist_ok=True)
    
    # Step 1: Run xelatex to generate PDF
    print("Step 1: Generating PDF with xelatex...")
    pdf_result = run_command_with_timeout([
        "xelatex", 
        "-interaction=nonstopmode",
        "-output-directory", str(temp_dir),
        str(input_file)
    ])
    
    result['steps']['pdf_generation'] = pdf_result
    
    if pdf_result['success']:
        print(f"PDF generation successful ({pdf_result['duration']:.2f}s)")
        
        # Copy the resulting PDF to the pdf directory
        pdf_file = TEST_DIR / "pdf" / "method3_output.pdf"
        temp_pdf = temp_dir / "method3_input.pdf"
        
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
        
        # Step 2: Convert PDF to SVG using Inkscape
        print("Step 2: Converting PDF to SVG with Inkscape...")
        svg_file = TEST_DIR / "svg" / "method3_output.svg"
        
        # Try modern Inkscape syntax first (v1.0+)
        svg_result = run_command_with_timeout([
            "inkscape", 
            "--export-type=svg",
            "--export-filename=" + str(svg_file),
            str(pdf_file)
        ])
        
        # If that fails, try legacy syntax
        if not svg_result['success']:
            print("Trying legacy Inkscape syntax...")
            svg_result = run_command_with_timeout([
                "inkscape", 
                "--export-svg=" + str(svg_file),
                str(pdf_file)
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
            print(f"Error output: {pdf_result['stderr'][:200]}...")
    
    return result

if __name__ == "__main__":
    result = test_method3()
    print(f"\nMethod 3 result: {'SUCCESS' if result['overall_success'] else 'FAILED'}") 