#!/usr/bin/env python3
"""
LaTeX to SVG Generator

This script processes a JSON file containing LaTeX content and generates SVG files
using pdflatex and pdf2svg. It updates the JSON file to mark items as processed.

Requirements:
- pdflatex (from TeX Live or MiKTeX)
- pdf2svg
- Python 3.6+

Usage:
    python latex_svg_generator.py input.json [output_dir]
"""

import json
import os
import subprocess
import tempfile
import shutil
import sys
import argparse
from pathlib import Path
import logging
import base64

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LaTeXSVGGenerator:
    def __init__(self, output_dir="temp_svg"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.temp_dir = None
        
    def check_dependencies(self):
        """Check if required external tools are available."""
        dependencies = {
            'pdflatex': ['--version'],
            'pdf2svg': []  # pdf2svg doesn't support --version, just check if it exists
        }
        missing = []
        
        for dep, args in dependencies.items():
            try:
                if args:
                    # Tools that support --version
                    subprocess.run([dep] + args, 
                                 stdout=subprocess.DEVNULL, 
                                 stderr=subprocess.DEVNULL, 
                                 check=True)
                else:
                    # Tools that don't support --version, just check if they exist
                    subprocess.run([dep], 
                                 stdout=subprocess.DEVNULL, 
                                 stderr=subprocess.DEVNULL)
                logger.info(f"✓ {dep} found")
            except FileNotFoundError:
                missing.append(dep)
                logger.error(f"✗ {dep} not found")
            except subprocess.CalledProcessError:
                # For pdf2svg, a CalledProcessError is expected when run without args
                # This means the tool exists but needs proper arguments
                if dep == 'pdf2svg':
                    logger.info(f"✓ {dep} found")
                else:
                    missing.append(dep)
                    logger.error(f"✗ {dep} not found")
        
        if missing:
            raise RuntimeError(f"Missing dependencies: {', '.join(missing)}")
    
    def create_temp_dir(self):
        """Create a temporary directory for processing."""
        self.temp_dir = tempfile.mkdtemp(prefix='latex_svg_')
        logger.debug(f"Created temp directory: {self.temp_dir}")
    
    def cleanup_temp_dir(self):
        """Clean up temporary directory."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            logger.debug(f"Cleaned up temp directory: {self.temp_dir}")
    
    def generate_svg_from_latex(self, latex_content, item_id):
        """
        Generate SVG from LaTeX content and return as base64 data URI.
        
        Args:
            latex_content (str): LaTeX source code
            item_id (str): Unique identifier for the item
            
        Returns:
            str: SVG content as data:image/svg+xml;base64,... URI, or None if generation failed
        """
        if not latex_content.strip():
            logger.warning(f"Empty LaTeX content for item {item_id}")
            return None
        
        try:
            # Create temporary files
            tex_file = os.path.join(self.temp_dir, f"{item_id}.tex")
            pdf_file = os.path.join(self.temp_dir, f"{item_id}.pdf")
            svg_file = self.output_dir / f"{item_id}.svg"
            
            # Write LaTeX content to file
            with open(tex_file, 'w', encoding='utf-8') as f:
                # Replace \r\n with \n for proper line endings
                clean_content = latex_content.replace('\r\n', '\n')
                f.write(clean_content)
            
            # Run pdflatex
            logger.info(f"Generating PDF for item {item_id}...")
            pdflatex_cmd = [
                'pdflatex',
                '-interaction=nonstopmode',
                '-halt-on-error',
                '-output-directory', self.temp_dir,
                tex_file
            ]
            
            result = subprocess.run(
                pdflatex_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.temp_dir
            )
            
            if result.returncode != 0:
                logger.error(f"pdflatex failed for item {item_id}")
                logger.error(f"stdout: {result.stdout}")
                logger.error(f"stderr: {result.stderr}")
                return None
            
            # Check if PDF was created
            if not os.path.exists(pdf_file):
                logger.error(f"PDF file not created for item {item_id}")
                return None
            
            # Run pdf2svg
            logger.info(f"Converting PDF to SVG for item {item_id}...")
            pdf2svg_cmd = [
                'pdf2svg',
                pdf_file,
                str(svg_file)
            ]
            
            result = subprocess.run(
                pdf2svg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"pdf2svg failed for item {item_id}")
                logger.error(f"stdout: {result.stdout}")
                logger.error(f"stderr: {result.stderr}")
                return None
            
            # Check if SVG was created
            if not svg_file.exists():
                logger.error(f"SVG file not created for item {item_id}")
                return None
            
            # Read SVG content and convert to data URI
            try:
                with open(svg_file, 'r', encoding='utf-8') as f:
                    svg_content = f.read().strip()
                
                # Encode SVG content as base64
                svg_bytes = svg_content.encode('utf-8')
                svg_b64 = base64.b64encode(svg_bytes).decode('ascii')
                
                # Create data URI
                data_uri = f"data:image/svg+xml;base64,{svg_b64}"
                
                logger.info(f"✓ Successfully generated SVG data URI for item {item_id}")
                return data_uri
            except Exception as e:
                logger.error(f"Error reading/encoding SVG file for item {item_id}: {e}")
                return None
            
        except Exception as e:
            logger.error(f"Error generating SVG for item {item_id}: {e}")
            return None
    
    def process_json_file(self, json_file_path):
        """
        Process the JSON file and generate SVGs for items with svg_generated=false.
        
        Args:
            json_file_path (str): Path to the JSON file
            
        Returns:
            bool: True if processing was successful
        """
        try:
            # Load JSON data
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                logger.error("JSON file should contain a list of items")
                return False
            
            # Create temporary directory
            self.create_temp_dir()
            
            processed_count = 0
            success_count = 0
            
            # Process each item
            for item in data:
                if not isinstance(item, dict):
                    logger.warning("Skipping non-dict item")
                    continue
                
                item_id = item.get('id', 'unknown')
                
                # Skip if SVG already generated
                if item.get('svg_generated', False):
                    logger.info(f"Skipping item {item_id} (already processed)")
                    continue
                
                # Skip if no content
                content = item.get('content', '')
                if not content.strip():
                    logger.warning(f"Skipping item {item_id} (no content)")
                    continue
                
                processed_count += 1
                logger.info(f"Processing item {item_id}...")
                
                # Generate SVG data URI
                svg_data_uri = self.generate_svg_from_latex(content, item_id)
                
                if svg_data_uri:
                    # Update the item with SVG data URI
                    item['svg'] = svg_data_uri
                    item['svg_generated'] = True
                    success_count += 1
                    logger.info(f"✓ Updated item {item_id}")
                else:
                    logger.error(f"✗ Failed to process item {item_id}")
            
            # Save updated JSON
            if processed_count > 0:
                with open(json_file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                logger.info(f"Updated JSON file: {json_file_path}")
                
                # Clean up temporary SVG files since we've embedded the content
                try:
                    if self.output_dir.exists():
                        shutil.rmtree(self.output_dir)
                        logger.debug(f"Cleaned up temporary SVG directory: {self.output_dir}")
                except Exception as e:
                    logger.warning(f"Could not clean up SVG directory: {e}")
            
            logger.info(f"Processing complete: {success_count}/{processed_count} items successful")
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON file: {e}")
            return False
        except Exception as e:
            logger.error(f"Error processing JSON file: {e}")
            return False
        finally:
            self.cleanup_temp_dir()

def main():
    parser = argparse.ArgumentParser(description='Generate SVG files from LaTeX content in JSON')
    parser.add_argument('json_file', help='Path to the JSON file')
    parser.add_argument('-o', '--output', default='temp_svg', 
                       help='Temporary directory for SVG generation (default: temp_svg)')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check if JSON file exists
    if not os.path.exists(args.json_file):
        logger.error(f"JSON file not found: {args.json_file}")
        sys.exit(1)
    
    # Create generator
    generator = LaTeXSVGGenerator(args.output)
    
    try:
        # Check dependencies
        generator.check_dependencies()
        
        # Process the file
        success = generator.process_json_file(args.json_file)
        
        if success:
            logger.info("All done! 🎉")
            sys.exit(0)
        else:
            logger.error("Processing failed")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()