#!/usr/bin/env python3
"""
Method 4: lualatex → pdf2svg
Use LuaLaTeX to generate PDF, then pdf2svg to convert to SVG.
LuaLaTeX has good support for complex typography and OpenType fonts.
"""

import shutil
from pathlib import Path
from test_utils import TEST_DIR, get_robust_latex_content, get_simple_latex_content, get_minimal_latex_content, run_command_with_timeout

def get_lualatex_content(method_name):
    """Get LaTeX content optimized for LuaLaTeX with Lua code."""
    return f"""\\documentclass{{article}}
\\usepackage{{fontspec}}
\\usepackage{{luacode}}
\\usepackage{{tikz}}
\\usepackage{{circuitikz}}
\\usepackage{{amsmath}}
\\usepackage{{exam}}
\\usepackage{{array}}
\\usepackage{{booktabs}}

\\begin{{document}}

\\title{{{method_name} Test Document}}
\\maketitle

\\section{{LuaLaTeX Special Features}}

\\begin{{luacode}}
function factorial(n)
  if n == 0 then
    return 1
  else
    return n * factorial(n - 1)
  end
end
tex.print("Factorial of 5 is " .. factorial(5))
\\end{{luacode}}

\\section{{Mathematical Content}}
Complex math: $\\int_{{0}}^{{\\infty}} e^{{-x^2}} dx = \\frac{{\\sqrt{{\\pi}}}}{{2}}$

\\begin{{align}}
E &= mc^2\\\\
F &= ma\\\\
\\nabla \\times \\vec{{E}} &= -\\frac{{\\partial \\vec{{B}}}}{{\\partial t}}
\\end{{align}}

\\section{{TikZ Graphics}}
\\begin{{tikzpicture}}
\\draw[thick,rounded corners=8pt] (0,0) -- (0,2) -- (1,3.25) -- (2,2) -- (2,0) -- (0,0);
\\draw[thick,dashed] (0,0) -- (2,2);
\\draw[thick,dashed] (0,2) -- (2,0);
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

def test_method4():
    """
    Test Method 4: lualatex → pdf2svg
    
    Requirements:
    - lualatex (texlive with luatex)
    - pdf2svg
    """
    method_name = "Method 4: lualatex → pdf2svg"
    print(f"\n--- Testing {method_name} ---")
    
    result = {
        'overall_success': False,
        'steps': {},
        'files_created': [],
        'method_name': method_name
    }
    
    # Try Lua content first, then fallback to simpler versions
    latex_content = get_lualatex_content("Method 4 - LuaLaTeX")
    input_file = TEST_DIR / "input" / "method4_input.tex"
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
    
    # Create a temporary directory for lualatex auxiliary files
    temp_dir = TEST_DIR / "temp" / "method4"
    temp_dir.mkdir(exist_ok=True)
    
    # Step 1: Run lualatex to generate PDF
    print("Step 1: Generating PDF with lualatex...")
    pdf_result = run_command_with_timeout([
        "lualatex", 
        "-interaction=nonstopmode",
        "-output-directory", str(temp_dir),
        str(input_file)
    ])
    
    result['steps']['pdf_generation'] = pdf_result
    
    # If PDF generation failed, try fallback content
    if not pdf_result['success'] and not fallback_used:
        print("PDF generation failed with Lua content. Trying simple fallback...")
        print(f"Error details: {pdf_result['stderr'][:200]}..." if pdf_result['stderr'] else "No error details")
        
        # Try simple content
        latex_content = get_simple_latex_content("Method 4 - LuaLaTeX (Simple)")
        fallback_file = TEST_DIR / "input" / "method4_input_simple.tex"
        
        try:
            with open(fallback_file, "w", encoding='utf-8') as f:
                f.write(latex_content)
            result['files_created'].append(str(fallback_file))
            print(f"Created fallback input file: {fallback_file}")
            
            # Try PDF generation again with simple content
            pdf_result = run_command_with_timeout([
                "lualatex", 
                "-interaction=nonstopmode",
                "-output-directory", str(temp_dir),
                str(fallback_file)
            ])
            
            result['steps']['pdf_generation_fallback'] = pdf_result
            fallback_used = True
            
            if pdf_result['success']:
                print(f"PDF generation with simple content successful ({pdf_result['duration']:.2f}s)")
            else:
                print(f"PDF generation failed even with simple content: {pdf_result['stderr'][:200]}..." if pdf_result['stderr'] else "No error details")
                
                # Try minimal content as last resort
                print("Trying minimal content as last resort...")
                minimal_content = get_minimal_latex_content("Method 4 - LuaLaTeX (Minimal)")
                minimal_file = TEST_DIR / "input" / "method4_input_minimal.tex"
                
                try:
                    with open(minimal_file, "w", encoding='utf-8') as f:
                        f.write(minimal_content)
                    result['files_created'].append(str(minimal_file))
                    print(f"Created minimal input file: {minimal_file}")
                    
                    # Try PDF generation with minimal content
                    pdf_result = run_command_with_timeout([
                        "lualatex", 
                        "-interaction=nonstopmode",
                        "-output-directory", str(temp_dir),
                        str(minimal_file)
                    ])
                    
                    result['steps']['pdf_generation_minimal'] = pdf_result
                    
                    if pdf_result['success']:
                        print(f"PDF generation with minimal content successful ({pdf_result['duration']:.2f}s)")
                    else:
                        print(f"PDF generation failed even with minimal content: {pdf_result['stderr'][:300]}..." if pdf_result['stderr'] else "No error details")
                        
                except Exception as e:
                    print(f"Failed to create minimal content: {e}")
                    
        except Exception as e:
            print(f"Failed to create fallback content: {e}")
    
    if pdf_result['success']:
        print(f"PDF generation successful ({pdf_result['duration']:.2f}s)")
        
        # Copy the resulting PDF to the pdf directory
        pdf_file = TEST_DIR / "pdf" / "method4_output.pdf"
        if fallback_used:
            if (temp_dir / "method4_input_minimal.pdf").exists():
                temp_pdf = temp_dir / "method4_input_minimal.pdf"
            else:
                temp_pdf = temp_dir / "method4_input_simple.pdf"
        else:
            temp_pdf = temp_dir / "method4_input.pdf"
        
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
        svg_file = TEST_DIR / "svg" / "method4_output.svg"
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
            print(f"Error output: {pdf_result['stderr'][:200]}...")
    
    return result

if __name__ == "__main__":
    result = test_method4()
    print(f"\nMethod 4 result: {'SUCCESS' if result['overall_success'] else 'FAILED'}") 