#!/usr/bin/env python3
"""
Main test runner for LaTeX to SVG rendering methods.
This script runs all individual method tests and generates comprehensive reports.
"""

import sys
import time
from pathlib import Path
from test_utils import clean_directory, check_prerequisites, create_test_results_report

# Import all method test functions
from method1_pdflatex import test_method1
from method2_latex_dvisvgm import test_method2
from method3_xelatex_inkscape import test_method3
from method4_lualatex import test_method4
from method5_pandoc import test_method5

def print_header():
    """Print a nice header for the test suite."""
    print("=" * 80)
    print("LATEX TO SVG RENDERING METHODS - COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print(f"Test started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

def print_summary(results):
    """Print a summary of all test results."""
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    total_tests = len(results)
    successful_tests = sum(1 for r in results.values() if r['overall_success'])
    failed_tests = total_tests - successful_tests
    
    print(f"Total methods tested: {total_tests}")
    print(f"Successful methods: {successful_tests}")
    print(f"Failed methods: {failed_tests}")
    print(f"Success rate: {(successful_tests/total_tests)*100:.1f}%")
    print()
    
    # Show detailed results for each method
    for method_name, result in results.items():
        status = "✓ SUCCESS" if result['overall_success'] else "✗ FAILED"
        print(f"{status:12} - {method_name}")
        
        if not result['overall_success'] and 'steps' in result:
            # Show which specific steps failed
            failed_steps = [step for step, data in result['steps'].items() if not data['success']]
            if failed_steps:
                print(f"             Failed steps: {', '.join(failed_steps)}")
    
    print()

def check_method_prerequisites():
    """Check prerequisites and determine which methods can be tested."""
    prereqs = check_prerequisites()
    
    testable_methods = {}
    
    # Method 1: pdflatex + pdf2svg
    testable_methods['method1'] = prereqs["pdflatex"] and prereqs["pdf2svg"]
    
    # Method 2: latex + dvisvgm  
    testable_methods['method2'] = prereqs["latex"] and prereqs["dvisvgm"]
    
    # Method 3: xelatex + inkscape
    testable_methods['method3'] = prereqs["xelatex"] and prereqs["inkscape"]
    
    # Method 4: lualatex + pdf2svg
    testable_methods['method4'] = prereqs["lualatex"] and prereqs["pdf2svg"]
    
    # Method 5: pandoc + pdf2svg
    testable_methods['method5'] = prereqs["pandoc"] and prereqs["pdf2svg"]
    
    print("\nMethod feasibility check:")
    for method, testable in testable_methods.items():
        status = "✓" if testable else "✗"
        print(f"{status} {method}")
    
    return testable_methods

def run_all_tests():
    """Run all available LaTeX to SVG conversion tests."""
    print_header()
    
    # Clean the test directory
    print("Cleaning test directory...")
    clean_directory()
    
    # Check prerequisites
    print("\nChecking prerequisites...")
    testable_methods = check_method_prerequisites()
    
    # Define the test methods with their functions
    test_methods = [
        ('method1', test_method1, "Method 1: pdflatex → pdf2svg"),
        ('method2', test_method2, "Method 2: latex → dvisvgm"),
        ('method3', test_method3, "Method 3: xelatex → Inkscape"),
        ('method4', test_method4, "Method 4: lualatex → pdf2svg"),
        ('method5', test_method5, "Method 5: pandoc pipeline")
    ]
    
    # Run the tests
    results = {}
    total_start_time = time.time()
    
    for method_key, test_func, method_name in test_methods:
        if testable_methods[method_key]:
            try:
                print(f"\n{'='*60}")
                print(f"RUNNING: {method_name}")
                print('='*60)
                
                start_time = time.time()
                result = test_func()
                end_time = time.time()
                
                result['total_duration'] = end_time - start_time
                results[method_name] = result
                
                status = "SUCCESS" if result['overall_success'] else "FAILED"
                print(f"\n{method_name}: {status} (Total time: {result['total_duration']:.2f}s)")
                
            except Exception as e:
                print(f"\nEXCEPTION in {method_name}: {str(e)}")
                results[method_name] = {
                    'overall_success': False,
                    'steps': {
                        'execution': {
                            'success': False,
                            'error': f'Exception: {str(e)}',
                            'duration': 0,
                            'returncode': -99
                        }
                    },
                    'files_created': [],
                    'method_name': method_name,
                    'total_duration': 0
                }
        else:
            print(f"\nSKIPPING: {method_name} (missing prerequisites)")
            results[method_name] = {
                'overall_success': False,
                'steps': {
                    'prerequisites': {
                        'success': False,
                        'error': 'Missing required tools',
                        'duration': 0,
                        'returncode': -98
                    }
                },
                'files_created': [],
                'method_name': method_name,
                'total_duration': 0
            }
    
    total_end_time = time.time()
    total_duration = total_end_time - total_start_time
    
    # Print summary
    print_summary(results)
    
    # Create detailed report
    report_file = create_test_results_report(results)
    
    # Print final information
    print(f"Total test suite duration: {total_duration:.2f} seconds")
    print(f"Test completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Detailed report saved to: {report_file}")
    print("\nTest files are stored in: app/data/latex/")
    print("- input/: LaTeX source files")
    print("- pdf/: Generated PDF files") 
    print("- svg/: Generated SVG files")
    print("- temp/: Temporary build files")
    
    return results

def create_requirements_guide():
    """Create a comprehensive requirements and installation guide."""
    content = """# LaTeX to SVG Rendering Methods - Requirements Guide

## Overview
This test suite evaluates 5 different methods for converting LaTeX documents to SVG format.
Each method uses different tools and has different strengths.

## Test Content
Each test uses LaTeX documents containing at least 2 of these required environments:
- `tikzpicture` - TikZ graphics
- `circuitikz` - Electronic circuit diagrams  
- `tabular` - Tables
- `questions` - Exam questions (requires exam package)
- `parts` - Question parts
- `subparts` - Question sub-parts

## Method Requirements

### Method 1: pdflatex → pdf2svg
**Tools needed:**
- `pdflatex` (part of texlive)
- `pdf2svg` (poppler-based)

**Best for:** General documents, good compatibility

### Method 2: latex → dvisvgm  
**Tools needed:**
- `latex` (part of texlive)
- `dvisvgm` (part of texlive)

**Best for:** Simple documents, small file sizes

### Method 3: xelatex → Inkscape
**Tools needed:**
- `xelatex` (part of texlive-xetex)
- `inkscape`

**Best for:** Unicode support, custom fonts, highest quality output

### Method 4: lualatex → pdf2svg
**Tools needed:**
- `lualatex` (part of texlive-luatex)
- `pdf2svg`

**Best for:** Documents with Lua code, OpenType fonts

### Method 5: pandoc pipeline
**Tools needed:**
- `pandoc`
- `texlive` (for LaTeX processing)
- `pdf2svg`

**Best for:** Document format conversion pipelines

## Installation Instructions

### Ubuntu/Debian
```bash
# Update package list
sudo apt-get update

# Install complete TeX Live distribution
sudo apt-get install texlive-full

# Install pdf2svg
sudo apt-get install pdf2svg

# Install Inkscape
sudo apt-get install inkscape

# Install pandoc
sudo apt-get install pandoc
```

### macOS (using Homebrew)
```bash
# Install TeX Live
brew install mactex

# Install pdf2svg
brew install pdf2svg

# Install Inkscape
brew install inkscape

# Install pandoc
brew install pandoc
```

### Windows
1. **TeX Live**: Download from https://tug.org/texlive/
2. **pdf2svg**: Download from https://github.com/dawbarton/pdf2svg/
3. **Inkscape**: Download from https://inkscape.org/
4. **pandoc**: Download from https://pandoc.org/installing.html

## Error Code Reference

- **-1**: Timeout (process took too long)
- **-2**: Command not found (tool not installed)
- **-3**: Input file creation failed
- **-4**: File copy operation failed
- **-5**: Expected output file not generated
- **-98**: Missing prerequisites (skipped)
- **-99**: Python exception during execution

## Troubleshooting

### Common Issues
1. **Package not found errors**: Install missing LaTeX packages
2. **Font errors**: Use system fonts or install font packages
3. **Permission errors**: Check file/directory permissions
4. **Memory errors**: Increase system memory or reduce document complexity

### LaTeX Package Dependencies
The test documents require these LaTeX packages:
- `amsmath`, `amssymb` - Mathematics
- `tikz` - Graphics
- `circuitikz` - Circuit diagrams
- `exam` - Question formatting
- `array`, `booktabs` - Enhanced tables
- `fontspec` - Font selection (XeLaTeX/LuaLaTeX only)
- `unicode-math` - Unicode math (XeLaTeX only)
- `luacode` - Lua code blocks (LuaLaTeX only)

## Performance Expectations
- **PDF generation**: 1-10 seconds depending on complexity
- **SVG conversion**: 0.5-5 seconds depending on method
- **Total per method**: 2-15 seconds typically

## Quality Comparison
- **Inkscape**: Highest quality, best font handling
- **pdf2svg**: Good quality, fast processing
- **dvisvgm**: Compact output, basic quality
"""
    
    guide_file = Path("app/data/latex/requirements_guide.md")
    with open(guide_file, "w") as f:
        f.write(content)
    
    print(f"Requirements guide created: {guide_file}")

if __name__ == "__main__":
    try:
        # Create requirements guide
        create_requirements_guide()
        
        # Run all tests
        results = run_all_tests()
        
        # Exit with appropriate code
        successful_tests = sum(1 for r in results.values() if r['overall_success'])
        if successful_tests == 0:
            print("\n⚠️  All tests failed!")
            sys.exit(1)
        elif successful_tests < len(results):
            print(f"\n⚠️  {len(results) - successful_tests} test(s) failed!")
            sys.exit(1)
        else:
            print("\n✅ All tests passed!")
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n\nTest suite interrupted by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nFatal error in test suite: {e}")
        sys.exit(1)