#!/usr/bin/env python3
"""
Method 2: latex → dvisvgm
Use latex to generate DVI, then dvisvgm to convert to SVG.
"""

from pathlib import Path
from test_utils import TEST_DIR, get_robust_latex_content, get_simple_latex_content, get_minimal_latex_content, run_command_with_timeout

def test_method2():
    """
    Test Method 2: latex → dvisvgm
    
    Requirements:
    - latex (texlive)
    - dvisvgm
    """
    method_name = "Method 2: latex → dvisvgm"
    print(f"\n--- Testing {method_name} ---")
    
    result = {
        'overall_success': False,
        'steps': {},
        'files_created': [],
        'method_name': method_name
    }
    
    # Try robust content first, fallback to simple if needed
    latex_content = get_robust_latex_content("Method 2 - latex")
    input_file = TEST_DIR / "input" / "method2_input.tex"
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
    
    # Create a temporary directory for latex auxiliary files
    temp_dir = TEST_DIR / "temp" / "method2"
    temp_dir.mkdir(exist_ok=True)
    
        # Step 1: Run latex to generate DVI
    print("Step 1: Generating DVI with latex...")
    dvi_result = run_command_with_timeout([
        "latex",
        "-interaction=nonstopmode",
        "-output-directory", str(temp_dir),
        str(input_file)
    ])
    
    # Check if DVI was actually created (latex may return non-zero even on success)
    temp_dvi = temp_dir / "method2_input.dvi"
    if temp_dvi.exists():
        dvi_result['success'] = True
        print(f"DVI generation successful - robust content worked! ({dvi_result['duration']:.2f}s)")
    
    result['steps']['dvi_generation'] = dvi_result
    
    # If DVI generation failed and we haven't tried fallback yet, try simple content
    if not dvi_result['success'] and not fallback_used:
        print("DVI generation failed with robust content. Trying simple fallback...")
        print(f"Error details: {dvi_result['stderr'][:200]}..." if dvi_result['stderr'] else "No error details")
        
        # Try simple content
        latex_content = get_simple_latex_content("Method 2 - latex (Simple)")
        fallback_file = TEST_DIR / "input" / "method2_input_simple.tex"
        
        try:
            with open(fallback_file, "w", encoding='utf-8') as f:
                f.write(latex_content)
            result['files_created'].append(str(fallback_file))
            print(f"Created fallback input file: {fallback_file}")
            
            # Try DVI generation again with simple content
            dvi_result = run_command_with_timeout([
                "latex", 
                "-interaction=nonstopmode",
                "-output-directory", str(temp_dir),
                str(fallback_file)
            ])
            
            result['steps']['dvi_generation_fallback'] = dvi_result
            fallback_used = True
            
            if dvi_result['success']:
                print(f"DVI generation with simple content successful ({dvi_result['duration']:.2f}s)")
            else:
                print(f"DVI generation failed even with simple content: {dvi_result['stderr'][:200]}..." if dvi_result['stderr'] else "No error details")
                
                # Try minimal content as last resort
                print("Trying minimal content as last resort...")
                minimal_content = get_minimal_latex_content("Method 2 - latex (Minimal)")
                minimal_file = TEST_DIR / "input" / "method2_input_minimal.tex"
                
                try:
                    with open(minimal_file, "w", encoding='utf-8') as f:
                        f.write(minimal_content)
                    result['files_created'].append(str(minimal_file))
                    print(f"Created minimal input file: {minimal_file}")
                    
                    # Try DVI generation with minimal content
                    dvi_result = run_command_with_timeout([
                        "latex", 
                        "-interaction=nonstopmode",
                        "-output-directory", str(temp_dir),
                        str(minimal_file)
                    ])
                    
                    result['steps']['dvi_generation_minimal'] = dvi_result
                    
                    if dvi_result['success']:
                        print(f"DVI generation with minimal content successful ({dvi_result['duration']:.2f}s)")
                    else:
                        print(f"DVI generation failed even with minimal content: {dvi_result['stderr'][:300]}..." if dvi_result['stderr'] else "No error details")
                        
                except Exception as e:
                    print(f"Failed to create minimal content: {e}")
                    
        except Exception as e:
            print(f"Failed to create fallback content: {e}")
    
    if dvi_result['success']:
        print(f"DVI generation successful ({dvi_result['duration']:.2f}s)")
        
        if fallback_used:
            if (temp_dir / "method2_input_minimal.dvi").exists():
                dvi_file = temp_dir / "method2_input_minimal.dvi"
            else:
                dvi_file = temp_dir / "method2_input_simple.dvi"
        else:
            dvi_file = temp_dir / "method2_input.dvi"
        
        if dvi_file.exists():
            result['files_created'].append(str(dvi_file))
            print(f"DVI file created: {dvi_file}")
            
            # Step 2: Convert DVI to SVG using dvisvgm
            print("Step 2: Converting DVI to SVG with dvisvgm...")
            svg_file = TEST_DIR / "svg" / "method2_output.svg"
            svg_result = run_command_with_timeout([
                "dvisvgm", 
                "--no-fonts",
                "--output=" + str(svg_file),
                str(dvi_file)
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
            result['steps']['dvi_check'] = {
                'success': False,
                'error': 'DVI file not generated',
                'duration': 0,
                'returncode': -5
            }
            print("DVI file was not generated")
    else:
        print(f"DVI generation failed: {dvi_result['error']}")
        print(f"Return code: {dvi_result['returncode']}")
        if dvi_result['stderr']:
            print(f"Error output: {dvi_result['stderr'][:500]}...")
        if dvi_result['stdout']:
            print(f"LaTeX output: {dvi_result['stdout'][:500]}...")
    
    return result

if __name__ == "__main__":
    result = test_method2()
    print(f"\nMethod 2 result: {'SUCCESS' if result['overall_success'] else 'FAILED'}") 