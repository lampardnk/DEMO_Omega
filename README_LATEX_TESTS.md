# LaTeX to SVG Rendering Test Suite

This comprehensive test suite evaluates different methods for converting LaTeX documents to SVG format, with robust error handling and detailed reporting.

## 🏗️ Architecture

The test suite is modularized into separate files for maintainability:

### Core Files
- **`run_latex_tests.py`** - Main test runner and orchestrator
- **`test_utils.py`** - Common utilities and helper functions

### Method Test Files
- **`method1_pdflatex.py`** - pdflatex → pdf2svg conversion
- **`method2_latex_dvisvgm.py`** - latex → dvisvgm conversion  
- **`method3_xelatex_inkscape.py`** - xelatex → Inkscape conversion
- **`method4_lualatex.py`** - lualatex → pdf2svg conversion
- **`method5_pandoc.py`** - pandoc pipeline conversion

## 🧪 Test Content Requirements

Each test uses LaTeX documents containing **at least 2** of these environments:
- `tikzpicture` - TikZ graphics and diagrams
- `circuitikz` - Electronic circuit diagrams
- `tabular` - Tables and tabular data
- `questions` - Exam questions (requires exam package)
- `parts` - Question parts
- `subparts` - Question sub-parts

## 🚀 Quick Start

### Run All Tests
```bash
python run_latex_tests.py
```

### Run Individual Method Tests
```bash
python method1_pdflatex.py
python method2_latex_dvisvgm.py
python method3_xelatex_inkscape.py
python method4_lualatex.py
python method5_pandoc.py
```

## 📊 Test Results and Reporting

### Console Output
- Real-time progress updates
- Step-by-step success/failure indication
- Error codes and detailed error messages
- Performance timing for each step
- Summary with success rates

### Generated Files
- **`app/data/latex/test_results.md`** - Detailed test report
- **`app/data/latex/requirements_guide.md`** - Installation guide
- **`app/data/latex/input/`** - LaTeX source files
- **`app/data/latex/pdf/`** - Generated PDF files
- **`app/data/latex/svg/`** - Generated SVG files
- **`app/data/latex/temp/`** - Temporary build files

## 🔧 Error Handling

### Error Codes
- **-1**: Timeout (process exceeded time limit)
- **-2**: Command not found (tool not installed)
- **-3**: Input file creation failed
- **-4**: File copy operation failed
- **-5**: Expected output file not generated
- **-98**: Missing prerequisites (test skipped)
- **-99**: Python exception during execution

### Partial Success Reporting
Each method test reports success/failure for individual steps:
- Input file creation
- PDF/DVI generation
- File copying
- SVG conversion

## 🛠️ Installation Requirements

### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install texlive-full pdf2svg inkscape pandoc
```

### macOS (Homebrew)
```bash
brew install mactex pdf2svg inkscape pandoc
```

### Windows
1. Install MiKTeX or TeX Live
2. Install Inkscape, pdf2svg, and pandoc
3. Ensure all tools are in PATH

## 📋 Method Comparison

| Method | Tools | Best For | Quality | Speed |
|--------|-------|----------|---------|-------|
| Method 1 | pdflatex + pdf2svg | General use, compatibility | Good | Fast |
| Method 2 | latex + dvisvgm | Simple docs, small files | Basic | Very Fast |
| Method 3 | xelatex + Inkscape | Unicode, fonts, quality | Excellent | Medium |
| Method 4 | lualatex + pdf2svg | Lua code, OpenType fonts | Very Good | Medium |
| Method 5 | pandoc + pdf2svg | Document pipelines | Good | Medium |

## 🎯 Use Cases

### For Web Applications
- Method 1 or 4 for general math rendering
- Method 3 for multilingual content
- Method 2 for simple equations (fastest)

### For Question Banks
- Method 1 with robust exam package support
- Method 3 for international symbols
- All methods support complex question structures

### For Technical Documentation
- Method 3 for publication-quality output
- Method 4 for advanced typography
- Method 5 for integrated documentation workflows

## 🐛 Troubleshooting

### Common Issues
1. **LaTeX package errors**: Install missing packages or use `texlive-full`
2. **Font issues**: Use system fonts or install required font packages
3. **Permission errors**: Check directory write permissions
4. **Memory issues**: Reduce document complexity or increase system memory

### Debugging Steps
1. Run individual method tests to isolate issues
2. Check prerequisite installation with `--version` flags
3. Examine error output in generated reports
4. Verify LaTeX package installations

## 🔍 Example Usage in Application

```python
from method1_pdflatex import test_method1
from test_utils import clean_directory

# Clean and run specific test
clean_directory()
result = test_method1()

if result['overall_success']:
    svg_file = result['files_created'][-1]  # Last file is usually SVG
    print(f"SVG generated: {svg_file}")
else:
    print("Failed steps:", [step for step, data in result['steps'].items() if not data['success']])
```

## 📈 Performance Expectations

- **PDF Generation**: 1-10 seconds (depends on document complexity)
- **SVG Conversion**: 0.5-5 seconds (depends on method and file size)  
- **Total per method**: 2-15 seconds typically
- **Full test suite**: 1-5 minutes (depends on available tools)

## 🎨 Output Quality

### SVG Features Preserved
- Mathematical equations and symbols
- TikZ graphics and diagrams
- Circuit diagrams
- Tables and formatting
- Font styling and sizing

### Quality Rankings
1. **Inkscape** - Best font handling and vector quality
2. **pdf2svg** - Good balance of quality and speed
3. **dvisvgm** - Compact output, basic rendering

---

For detailed installation instructions and troubleshooting, see the generated `requirements_guide.md` after running the test suite. 