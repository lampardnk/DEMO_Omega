import os
import subprocess
import tempfile
import shutil
from pathlib import Path
import time

# Define the test directory
TEST_DIR = Path("app/data/latex")
TEST_DIR.mkdir(exist_ok=True, parents=True)

def clean_directory():
    """Clean up the test directory before starting tests."""
    for file in TEST_DIR.glob("*"):
        if file.is_file():
            file.unlink()
        elif file.is_dir():
            shutil.rmtree(file)
    
    # Create subdirectories for organized test outputs
    for subdir in ["input", "pdf", "svg", "temp"]:
        (TEST_DIR / subdir).mkdir(exist_ok=True)

def check_prerequisites():
    """Check if required tools are available."""
    prerequisites = {
        "pdflatex": False,
        "latex": False,
        "xelatex": False,
        "lualatex": False,
        "pdf2svg": False,
        "dvisvgm": False,
        "inkscape": False,
        "pandoc": False
    }
    
    print("Checking prerequisites...")
    
    for cmd in prerequisites:
        try:
            result = subprocess.run([cmd, "--version"], capture_output=True, text=True)
            prerequisites[cmd] = True
            print(f"✓ {cmd} is available")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"✗ {cmd} is not available")
    
    return prerequisites

def get_robust_latex_content(method_name):
    """
    Generate robust LaTeX content with at least 2 required environments.
    Required environments: scope, tikzpicture, circuitikz, tabular, questions, part, subparts
    Uses only available packages (no exam package - using custom question environment)
    """
    return f"""\\documentclass{{article}}
\\usepackage{{amsmath}}
\\usepackage{{amssymb}}
\\usepackage{{tikz}}
\\usepackage{{circuitikz}}
\\usepackage{{array}}
\\usepackage{{amsthm}}
\\usepackage{{geometry}}

% Custom environments to replace exam package
\\newcounter{{question}}
\\newcounter{{part}}[question]
\\newcounter{{subpart}}[part]

\\newenvironment{{questions}}{{%
  \\setcounter{{question}}{{0}}%
  \\list{{}}{{%
    \\usecounter{{question}}%
    \\setlength{{\\leftmargin}}{{1em}}%
    \\setlength{{\\labelsep}}{{0.5em}}%
  }}%
}}{{\\endlist}}

\\newcommand{{\\question}}{{%
  \\item[\\textbf{{\\arabic{{question}}.}}]%
}}

\\newenvironment{{parts}}{{%
  \\setcounter{{part}}{{0}}%
  \\list{{}}{{%
    \\usecounter{{part}}%
    \\setlength{{\\leftmargin}}{{2em}}%
    \\setlength{{\\labelsep}}{{0.5em}}%
  }}%
}}{{\\endlist}}

\\newcommand{{\\part}}{{%
  \\item[(\\alph{{part}})]%
}}

\\newenvironment{{subparts}}{{%
  \\setcounter{{subpart}}{{0}}%
  \\list{{}}{{%
    \\usecounter{{subpart}}%
    \\setlength{{\\leftmargin}}{{3em}}%
    \\setlength{{\\labelsep}}{{0.5em}}%
  }}%
}}{{\\endlist}}

\\newcommand{{\\subpart}}{{%
  \\item[(\\roman{{subpart}})]%
}}

\\begin{{document}}

\\title{{{method_name} Test Document}}
\\maketitle

\\section{{Mathematical Content}}
The quadratic formula is $x = \\frac{{-b \\pm \\sqrt{{b^2 - 4ac}}}}{{2a}}$

\\begin{{align}}
E &= mc^2\\\\
F &= ma\\\\
\\nabla \\times \\vec{{E}} &= -\\frac{{\\partial \\vec{{B}}}}{{\\partial t}}
\\end{{align}}

\\section{{TikZ Graphics with Scope}}
\\begin{{tikzpicture}}
\\draw[->] (-2,0) -- (2,0) node[right] {{$x$}};
\\draw[->] (0,-2) -- (0,2) node[above] {{$y$}};
\\draw[domain=-1.5:1.5,smooth,variable=\\x,blue] plot ({{\\x}},{{\\x*\\x-1}});
\\draw (0,0) circle (1cm);
\\draw (0,0) -- (1,0);
\\draw (0,0) -- (0,1);

% Scope environment - required
\\begin{{scope}}[shift={{(3,0)}}, scale=0.7]
\\draw[thick,red] (0,0) rectangle (2,1.5);
\\draw[dashed] (0,0) -- (2,1.5);
\\draw[dashed] (0,1.5) -- (2,0);
\\end{{scope}}

\\begin{{scope}}[shift={{(0,3)}}, rotate=30]
\\draw[fill=green!20] (0,0) -- (1,0) -- (1,1) -- (0,1) -- cycle;
\\end{{scope}}
\\end{{tikzpicture}}

\\section{{Circuit Diagrams}}
\\begin{{circuitikz}}
\\draw (0,0) to[V,v=$V_s$] (0,2) to[R,l=$R_1$] (2,2) to[R,l=$R_2$] (2,0) -- (0,0);
\\draw (2,2) to[C,l=$C$] (4,2) to[L,l=$L$] (4,0) -- (2,0);
\\draw (4,2) to[short,-*] (5,2) node[above] {{$V_{{out}}$}};
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

\\section{{Additional Complex Table}}
\\begin{{table}}[h]
\\centering
\\begin{{tabular}}{{|l|r|c|p{{3cm}}|}}
\\hline
Package & Lines & Status & Description \\\\
\\hline
circuitikz & 10000+ & Available & Circuit diagrams \\\\
tikz & 50000+ & Available & General graphics \\\\
amsmath & 2000+ & Available & Mathematical typesetting \\\\
geometry & 1500+ & Available & Page layout control \\\\
\\hline
\\end{{tabular}}
\\caption{{Available LaTeX packages}}
\\end{{table}}

\\section{{Custom Question Environment}}
\\begin{{questions}}
\\question What is the derivative of $x^2$?
\\begin{{parts}}
\\part $2x$ (Correct)
\\part $x$ (Incorrect)
\\part $2x^2$ (Incorrect)
\\end{{parts}}

\\question Solve for $x$: $2x + 5 = 11$
\\begin{{subparts}}
\\subpart Show your work: $2x = 11 - 5 = 6$, so $x = 3$
\\subpart Verify your answer: $2(3) + 5 = 6 + 5 = 11$ ✓
\\end{{subparts}}

\\question Evaluate the integral $\\int_0^1 x^2 \\, dx$
\\begin{{parts}}
\\part $\\frac{{1}}{{3}}$ (Correct)
\\part $\\frac{{1}}{{2}}$ (Incorrect)
\\part $1$ (Incorrect)
\\end{{parts}}
\\end{{questions}}

\\end{{document}}
"""

def get_simple_latex_content(method_name):
    """
    Generate simple LaTeX content using only basic packages.
    Still includes at least 2 required environments: tikzpicture, tabular
    """
    return f"""\\documentclass{{article}}
\\usepackage{{amsmath}}
\\usepackage{{amssymb}}
\\usepackage{{tikz}}
\\usepackage{{array}}

\\begin{{document}}

\\title{{{method_name} Test Document - Simple Version}}
\\maketitle

\\section{{Mathematical Content}}
The quadratic formula is $x = \\frac{{-b \\pm \\sqrt{{b^2 - 4ac}}}}{{2a}}$

\\begin{{align}}
E &= mc^2\\\\
F &= ma\\\\
\\nabla \\times \\vec{{E}} &= -\\frac{{\\partial \\vec{{B}}}}{{\\partial t}}
\\end{{align}}

\\section{{TikZ Graphics}}
\\begin{{tikzpicture}}
\\draw[->] (-2,0) -- (2,0) node[right] {{$x$}};
\\draw[->] (0,-2) -- (0,2) node[above] {{$y$}};
\\draw[domain=-1.5:1.5,smooth,variable=\\x,blue] plot ({{\\x}},{{\\x*\\x-1}});
\\draw (0,0) circle (1cm);
\\draw (0,0) -- (1,0);
\\draw (0,0) -- (0,1);
\\fill[red,opacity=0.3] (0,0) circle (0.5cm);
\\end{{tikzpicture}}

\\section{{Additional TikZ - Scope Environment}}
\\begin{{tikzpicture}}
\\begin{{scope}}[shift={{(3,0)}}, scale=0.8]
\\draw[thick] (0,0) rectangle (2,1.5);
\\draw[dashed] (0,0) -- (2,1.5);
\\draw[dashed] (0,1.5) -- (2,0);
\\end{{scope}}
\\begin{{scope}}[shift={{(0,3)}}, rotate=45]
\\draw[fill=blue!20] (0,0) -- (1,0) -- (1,1) -- (0,1) -- cycle;
\\end{{scope}}
\\end{{tikzpicture}}

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

\\section{{Additional Table}}
\\begin{{table}}[h]
\\centering
\\begin{{tabular}}{{|l|r|r|}}
\\hline
Package & Lines & Complexity \\\\
\\hline
amsmath & 2000+ & Medium \\\\
tikz & 50000+ & High \\\\
array & 500+ & Low \\\\
\\hline
\\end{{tabular}}
\\caption{{Package statistics}}
\\end{{table}}

\\section{{Mathematical Examples}}
Some inline math: $\\int_0^\\infty e^{{-x^2}} dx = \\frac{{\\sqrt{{\\pi}}}}{{2}}$

Display math:
\\begin{{equation}}
\\sum_{{n=1}}^\\infty \\frac{{1}}{{n^2}} = \\frac{{\\pi^2}}{{6}}
\\end{{equation}}

Matrix example:
\\begin{{equation}}
\\begin{{pmatrix}}
a & b \\\\
c & d
\\end{{pmatrix}}
\\begin{{pmatrix}}
x \\\\
y
\\end{{pmatrix}}
=
\\begin{{pmatrix}}
ax + by \\\\
cx + dy
\\end{{pmatrix}}
\\end{{equation}}

\\end{{document}}
"""

def get_minimal_latex_content(method_name):
    """
    Generate minimal LaTeX content using only core packages.
    Only basic math and simple table, no TikZ or complex packages.
    """
    return f"""\\documentclass{{article}}
\\usepackage{{amsmath}}

\\begin{{document}}

\\title{{{method_name} Test Document - Minimal Version}}
\\maketitle

\\section{{Mathematical Content}}
The quadratic formula is $x = \\frac{{-b \\pm \\sqrt{{b^2 - 4ac}}}}{{2a}}$

\\begin{{align}}
E &= mc^2\\\\
F &= ma\\\\
\\nabla \\times \\vec{{E}} &= -\\frac{{\\partial \\vec{{B}}}}{{\\partial t}}
\\end{{align}}

\\section{{Basic Table}}
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

\\section{{More Mathematics}}
Some inline math: $\\int_0^\\infty e^{{-x^2}} dx = \\frac{{\\sqrt{{\\pi}}}}{{2}}$

Display math:
\\begin{{equation}}
\\sum_{{n=1}}^\\infty \\frac{{1}}{{n^2}} = \\frac{{\\pi^2}}{{6}}
\\end{{equation}}

Matrix example:
\\begin{{equation}}
\\begin{{pmatrix}}
a & b \\\\
c & d
\\end{{pmatrix}}
\\begin{{pmatrix}}
x \\\\
y
\\end{{pmatrix}}
=
\\begin{{pmatrix}}
ax + by \\\\
cx + dy
\\end{{pmatrix}}
\\end{{equation}}

\\section{{Additional Content}}
Here are some more mathematical expressions to make the document substantial:

\\begin{{align}}
\\sin^2(x) + \\cos^2(x) &= 1\\\\
e^{{i\\pi}} + 1 &= 0\\\\
\\frac{{d}}{{dx}}[f(x)g(x)] &= f'(x)g(x) + f(x)g'(x)\\\\
\\int u \\, dv &= uv - \\int v \\, du
\\end{{align}}

A second table to meet the requirement of multiple environments:
\\begin{{table}}[h]
\\centering
\\begin{{tabular}}{{|l|r|}}
\\hline
Package & Status \\\\
\\hline
amsmath & Required \\\\
amsfonts & Optional \\\\
geometry & Optional \\\\
\\hline
\\end{{tabular}}
\\caption{{Package requirements}}
\\end{{table}}

\\end{{document}}
"""

def run_command_with_timeout(command, timeout=60):
    """Run a command with timeout and return detailed results."""
    start_time = time.time()
    try:
        result = subprocess.run(
            command, 
            check=True, 
            capture_output=True, 
            text=True,
            timeout=timeout
        )
        end_time = time.time()
        return {
            'success': True,
            'duration': end_time - start_time,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired as e:
        return {
            'success': False,
            'error': 'Timeout',
            'duration': timeout,
            'stdout': e.stdout.decode() if e.stdout else '',
            'stderr': e.stderr.decode() if e.stderr else '',
            'returncode': -1
        }
    except subprocess.CalledProcessError as e:
        end_time = time.time()
        return {
            'success': False,
            'error': 'Command failed',
            'duration': end_time - start_time,
            'stdout': e.stdout if e.stdout else '',
            'stderr': e.stderr if e.stderr else '',
            'returncode': e.returncode
        }
    except FileNotFoundError as e:
        return {
            'success': False,
            'error': 'Command not found',
            'duration': 0,
            'stdout': '',
            'stderr': str(e),
            'returncode': -2
        }

def create_test_results_report(results):
    """Create a detailed test results report."""
    content = f"""# LaTeX to SVG Rendering Test Results

Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}

## Test Summary
"""
    
    total_tests = len(results)
    successful_tests = sum(1 for r in results.values() if r['overall_success'])
    
    content += f"- Total methods tested: {total_tests}\n"
    content += f"- Successful methods: {successful_tests}\n"
    content += f"- Failed methods: {total_tests - successful_tests}\n\n"
    
    content += "## Detailed Results\n\n"
    
    for method_name, result in results.items():
        content += f"### {method_name}\n"
        content += f"- Overall Success: {'✓' if result['overall_success'] else '✗'}\n"
        
        if 'steps' in result:
            content += "- Step Results:\n"
            for step_name, step_result in result['steps'].items():
                status = '✓' if step_result['success'] else '✗'
                duration = f"{step_result['duration']:.2f}s"
                content += f"  - {step_name}: {status} ({duration})\n"
                
                if not step_result['success']:
                    content += f"    - Error: {step_result.get('error', 'Unknown')}\n"
                    content += f"    - Return Code: {step_result.get('returncode', 'N/A')}\n"
                    if step_result.get('stderr'):
                        content += f"    - Error Output: {step_result['stderr'][:200]}...\n"
        
        if 'files_created' in result:
            content += "- Files Created:\n"
            for file_path in result['files_created']:
                exists = "✓" if Path(file_path).exists() else "✗"
                content += f"  - {file_path}: {exists}\n"
        
        content += "\n"
    
    # Save the report
    report_file = TEST_DIR / "test_results.md"
    with open(report_file, "w") as f:
        f.write(content)
    
    print(f"Test results report created: {report_file}")
    return report_file 