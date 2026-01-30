"""
AIKO LATEX ENGINE
Handles LaTeX compilation and automated table generation.
"""

import os
import subprocess
import tempfile
import asyncio
from pylatex import Document, Section, Subsection, Tabular, MultiColumn, Command
from pylatex.utils import italic, NoEscape

class LatexEngine:
    def __init__(self, output_dir=None):
        self.output_dir = output_dir or os.path.join(os.path.expanduser("~"), "Downloads", "Aiko_Latex")
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_table(self, title, headers, rows):
        """Generate a professional LaTeX table and return the code."""
        doc = Document()
        with doc.create(Section(title)):
            with doc.create(Tabular('|' + 'c|' * len(headers))) as table:
                table.add_hline()
                table.add_row(headers)
                table.add_hline()
                for row in rows:
                    table.add_row(row)
                    table.add_hline()
        
        return doc.dumps()

    async def compile_to_pdf(self, tex_code, filename="aiko_output"):
        """Compile LaTeX code to PDF using pdflatex."""
        filepath = os.path.join(self.output_dir, f"{filename}.tex")
        pdf_path = os.path.join(self.output_dir, f"{filename}.pdf")
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(tex_code)
            
            # Run pdflatex (non-interactive)
            process = await asyncio.create_subprocess_exec(
                "pdflatex", "-interaction=nonstopmode", f"-output-directory={self.output_dir}", filepath,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return f"Success! I've compiled your paper to PDF. You can find it at: {pdf_path} (⁠ꈍ⁠ᴗ⁠ꈍ⁠)"
            else:
                return f"Ehh? Compilation failed, Master... There might be an error in the LaTeX code. Error: {stderr.decode()[:200]}"
                
        except Exception as e:
            return f"I tried to compile it, but I got a headache... {str(e)}"

    def format_math(self, expression, block=True):
        """Format a math expression for rendering."""
        if block:
            return f"$$\n{expression}\n$$"
        return f"${expression}$"
