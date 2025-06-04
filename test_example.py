#!/usr/bin/env python3
"""
Example script demonstrating how to use the modular LaTeX testing system.
This shows different ways to run and integrate the tests.
"""

import time
from test_utils import clean_directory, check_prerequisites
from method1_pdflatex import test_method1
from method3_xelatex_inkscape import test_method3

def example_single_method():
    """Example: Test a single method and handle results."""
    print("=== Testing Single Method (Method 1) ===")
    
    # Clean directory first
    clean_directory()
    
    # Run the test
    result = test_method1()
    
    # Handle the result
    if result['overall_success']:
        print("✅ Method 1 succeeded!")
        print(f"Files created: {len(result['files_created'])}")
        
        # Find the SVG file
        svg_files = [f for f in result['files_created'] if f.endswith('.svg')]
        if svg_files:
            print(f"SVG output: {svg_files[0]}")
    else:
        print("❌ Method 1 failed!")
        failed_steps = [step for step, data in result['steps'].items() 
                       if not data['success']]
        print(f"Failed steps: {failed_steps}")
        
        # Show first error details
        for step_name, step_data in result['steps'].items():
            if not step_data['success']:
                print(f"Error in {step_name}: {step_data.get('error', 'Unknown')}")
                break

def example_compare_methods():
    """Example: Compare multiple methods."""
    print("\n=== Comparing Multiple Methods ===")
    
    methods = [
        ("Method 1", test_method1),
        ("Method 3", test_method3)
    ]
    
    results = {}
    
    for name, test_func in methods:
        print(f"\nTesting {name}...")
        
        clean_directory()
        
        start_time = time.time()
        result = test_func()
        duration = time.time() - start_time
        
        results[name] = {
            'success': result['overall_success'],
            'duration': duration,
            'files': len(result['files_created'])
        }
        
        status = "✅" if result['overall_success'] else "❌"
        print(f"{status} {name}: {duration:.2f}s")
    
    # Summary
    print("\n--- Comparison Summary ---")
    for name, data in results.items():
        status = "SUCCESS" if data['success'] else "FAILED"
        print(f"{name:15} | {status:7} | {data['duration']:6.2f}s | {data['files']} files")

def example_prerequisite_check():
    """Example: Check prerequisites before running tests."""
    print("\n=== Prerequisite Check ===")
    
    prereqs = check_prerequisites()
    
    available_methods = []
    
    # Check Method 1 requirements
    if prereqs["pdflatex"] and prereqs["pdf2svg"]:
        available_methods.append("Method 1: pdflatex → pdf2svg")
    
    # Check Method 3 requirements  
    if prereqs["xelatex"] and prereqs["inkscape"]:
        available_methods.append("Method 3: xelatex → Inkscape")
    
    print(f"\nAvailable methods ({len(available_methods)}):")
    for method in available_methods:
        print(f"  ✅ {method}")
    
    if not available_methods:
        print("  ❌ No methods available - install required tools")
        return False
    
    return True

def example_error_handling():
    """Example: Demonstrate error handling."""
    print("\n=== Error Handling Example ===")
    
    # Try to run a test that might fail
    result = test_method3()  # This might fail if Inkscape isn't installed
    
    print(f"Overall success: {result['overall_success']}")
    print(f"Steps executed: {len(result['steps'])}")
    
    for step_name, step_data in result['steps'].items():
        status = "✅" if step_data['success'] else "❌"
        duration = step_data['duration']
        print(f"  {status} {step_name}: {duration:.2f}s")
        
        if not step_data['success']:
            print(f"    Error: {step_data.get('error', 'Unknown')}")
            print(f"    Return code: {step_data.get('returncode', 'N/A')}")

if __name__ == "__main__":
    print("LaTeX to SVG Testing - Examples")
    print("=" * 50)
    
    # Check if we can run any tests
    if example_prerequisite_check():
        # Run examples
        example_single_method()
        example_compare_methods() 
        example_error_handling()
    else:
        print("\nPlease install LaTeX tools to run examples.")
        print("See README_LATEX_TESTS.md for installation instructions.") 