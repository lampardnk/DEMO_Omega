
import os
import re
import tempfile
import subprocess
import shutil
import hashlib
import base64
import time
from typing import Dict, Any

# LaTeX compilation cache
LATEX_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_EXPIRY = 3600  # Cache expiry in seconds (1 hour)


class LaTeXProcessor:
    """Handle LaTeX compilation and caching"""
    
    @staticmethod
    def get_cache_key(latex_string: str) -> str:
        """Generate a cache key for LaTeX content"""
        return hashlib.md5(latex_string.encode('utf-8')).hexdigest()
    
    @staticmethod
    def clean_cache() -> None:
        """Remove expired items from the LaTeX cache"""
        current_time = time.time()
        expired_keys = [k for k, v in LATEX_CACHE.items() 
                       if current_time - v['timestamp'] > CACHE_EXPIRY]
        
        for key in expired_keys:
            del LATEX_CACHE[key]
    
    @staticmethod
    def latex_to_svg(latex_string: str) -> str:
        """Convert LaTeX to SVG using command line tools with caching"""
        # Check cache first
        cache_key = LaTeXProcessor.get_cache_key(latex_string)
        current_time = time.time()
        
        # Return from cache if available and not expired
        if cache_key in LATEX_CACHE:
            cached_item = LATEX_CACHE[cache_key]
            if current_time - cached_item['timestamp'] < CACHE_EXPIRY:
                return cached_item['svg']
        
        # Not in cache or expired, generate SVG
        svg_data = LaTeXProcessor._generate_svg(latex_string)
        
        # Store in cache
        LATEX_CACHE[cache_key] = {
            'svg': svg_data,
            'timestamp': current_time
        }
        
        # Clean old cache entries
        LaTeXProcessor.clean_cache()
        
        return svg_data
    
    @staticmethod
    def _generate_svg(latex_string: str) -> str:
        """Internal function to generate SVG from LaTeX"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tex_file = os.path.join(temp_dir, "content.tex")
            with open(tex_file, "w") as f:
                f.write(latex_string + "\n\n")
            
            try:
                # Run pdflatex
                result = subprocess.run(
                    ["pdflatex", "-shell-escape", "-interaction=nonstopmode", 
                     "-output-directory", temp_dir, tex_file],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                if result.returncode != 0:
                    error_message = LaTeXProcessor._extract_error(temp_dir, result)
                    raise subprocess.CalledProcessError(
                        result.returncode, result.args, 
                        output=result.stdout, stderr=error_message
                    )
                
                # Convert PDF to SVG
                pdf_file = os.path.join(temp_dir, "content.pdf")
                svg_file = os.path.join(temp_dir, "content.svg")
                
                if os.path.exists(pdf_file):
                    subprocess.run(
                        ["pdf2svg", pdf_file, svg_file],
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    
                    with open(svg_file, "r") as f:
                        svg_content = f.read()
                    
                    base64_data = base64.b64encode(svg_content.encode()).decode("ascii")
                    return f"data:image/svg+xml;base64,{base64_data}"
                else:
                    raise FileNotFoundError("PDF file was not created")
                    
            except subprocess.CalledProcessError as e:
                return LaTeXProcessor._create_error_svg(f"LaTeX error: {e.stderr}")
            except (FileNotFoundError, OSError) as e:
                return LaTeXProcessor._create_error_svg(f"System error: {str(e)}")
    
    @staticmethod
    def _extract_error(temp_dir: str, result: subprocess.CompletedProcess) -> str:
        """Extract error message from LaTeX log"""
        log_file = os.path.join(temp_dir, "content.log")
        error_message = "LaTeX compilation failed"
        
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                log_content = f.read()
                error_patterns = [
                    r'! (.+?)\n',
                    r'! LaTeX Error: (.+?)\n',
                    r'! Package (.+?) Error: (.+?)\n'
                ]
                
                for pattern in error_patterns:
                    matches = re.findall(pattern, log_content)
                    if matches:
                        if isinstance(matches[0], tuple):
                            error_message = ': '.join(matches[0])
                        else:
                            error_message = matches[0]
                        break
        
        return error_message
    
    @staticmethod
    def _create_error_svg(error_message: str) -> str:
        """Create an error SVG with the given message"""
        error_svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="500" height="100" viewBox="0 0 500 100">
    <rect width="500" height="100" fill="#f8d7da" stroke="#f5c6cb" stroke-width="1" rx="5" ry="5"/>
    <text x="50%" y="50%" text-anchor="middle" dominant-baseline="middle" font-family="Arial" font-size="14" fill="#721c24">
        {error_message}
    </text>
</svg>'''
        base64_data = base64.b64encode(error_svg.encode()).decode("ascii")
        return f"data:image/svg+xml;base64,{base64_data}"
    
    @staticmethod
    def ensure_complete_document(latex_content: str) -> str:
        """Ensure LaTeX content is a complete document"""
        if "\\documentclass" in latex_content:
            return latex_content
        
        packages = [
            "\\usepackage{amsmath}",
            "\\usepackage{amssymb}"
        ]
        
        if "\\begin{tikzpicture}" in latex_content:
            packages.append("\\usepackage{tikz}")
        
        if "\\begin{circuitikz}" in latex_content:
            packages.append("\\usepackage{circuitikz}")
        
        if "\\begin{enumerate}" in latex_content:
            packages.append("\\usepackage{enumitem}")
            
        packages.extend([
            "\\usepackage{geometry}",
            "\\geometry{margin=1in}",
            "\\usepackage[active,tightpage]{preview}"
        ])
        
        complete_document = "\\documentclass{exam}\n"
        complete_document += "\n".join(packages) + "\n\n"
        
        preview_env = "document"
        if "\\begin{questions}" in latex_content:
            preview_env = "questions"
        elif "\\begin{tikzpicture}" in latex_content:
            preview_env = "tikzpicture"
        elif "\\begin{circuitikz}" in latex_content:
            preview_env = "circuitikz"
            
        complete_document += f"\\PreviewEnvironment{{{preview_env}}}\n\n"
        complete_document += "\\begin{document}\n\n"
        
        if not any(env in latex_content for env in ["\\begin{questions}", "\\begin{tikzpicture}", "\\begin{circuitikz}"]):
            complete_document += "\\begin{questions}\n\\question\n"
            complete_document += latex_content + "\n"
            complete_document += "\\end{questions}\n"
        else:
            complete_document += latex_content + "\n\n"
            
        complete_document += "\\end{document}"
        
        return complete_document
