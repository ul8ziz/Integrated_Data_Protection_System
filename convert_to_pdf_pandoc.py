#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
سكريبت لتحويل التقرير الفني من Markdown إلى PDF باستخدام Pandoc
Script to convert Technical Report from Markdown to PDF using Pandoc
هذا السكريبت يوفر دعم أفضل للغة العربية من xhtml2pdf
This script provides better Arabic support than xhtml2pdf
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path


def check_pandoc():
    """Check if pandoc is installed"""
    try:
        result = subprocess.run(
            ["pandoc", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_xelatex():
    """Check if xelatex is available"""
    import shutil
    # First check if xelatex is in PATH
    if shutil.which("xelatex"):
        return True
    
    # Try to find xelatex in common MiKTeX locations
    common_paths = [
        r"C:\Users\Ul8ziz\AppData\Local\Programs\MiKTeX\miktex\bin\x64\xelatex.exe",
        r"C:\Program Files\MiKTeX\miktex\bin\x64\xelatex.exe",
        r"C:\Program Files (x86)\MiKTeX\miktex\bin\xelatex.exe",
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            # Add to PATH for this session
            bin_dir = os.path.dirname(path)
            os.environ["PATH"] = f"{bin_dir};{os.environ.get('PATH', '')}"
            return True
    
    return False


def convert_with_pandoc():
    """Convert Markdown to PDF using Pandoc with XeLaTeX"""
    # Set UTF-8 encoding for console output
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    # Check if pandoc is installed
    if not check_pandoc():
        print("[ERROR] pandoc غير مثبت!")
        print("[ERROR] pandoc is not installed!")
        print("\n[INFO] يرجى تثبيت pandoc:")
        print("[INFO] Please install pandoc:")
        print("   Windows: choco install pandoc")
        print("   Linux: sudo apt-get install pandoc")
        print("   macOS: brew install pandoc")
        sys.exit(1)
    
    # Check if xelatex is available
    if not check_xelatex():
        print("[WARNING] xelatex غير متاح. سيتم استخدام محرك PDF افتراضي.")
        print("[WARNING] xelatex not available. Will use default PDF engine.")
        print("[INFO] للحصول على أفضل دعم للعربية، يرجى تثبيت MiKTeX أو TeX Live")
        print("[INFO] For best Arabic support, please install MiKTeX or TeX Live")
        use_xelatex = False
    else:
        use_xelatex = True
        print("[INFO] تم العثور على xelatex. سيتم استخدامه للعربية.")
        print("[INFO] xelatex found. Will use it for Arabic support.")
    
    # Get file paths
    script_dir = Path(__file__).parent
    md_file = script_dir / "docs" / "TECHNICAL_REPORT_AR.md"
    output_file = script_dir / "docs" / "TECHNICAL_REPORT_AR.pdf"
    
    if not md_file.exists():
        print(f"[ERROR] الملف غير موجود: {md_file}")
        print(f"[ERROR] File not found: {md_file}")
        sys.exit(1)
    
    print("[INFO] قراءة ملف Markdown...")
    print("[INFO] Reading Markdown file...")
    
    # Build pandoc command
    cmd = [
        "pandoc",
        str(md_file),
        "-o", str(output_file),
        "-V", "geometry:margin=2cm",
        "--toc",
        "--toc-depth=3",
    ]
    
    if use_xelatex:
        # Use custom template for better Arabic support
        template_file = script_dir / "arabic_template.tex"
        if template_file.exists():
            cmd.extend([
                "--pdf-engine=xelatex",
                f"--template={template_file}",
            ])
        else:
            # Fallback: use xelatex with basic settings
            cmd.extend([
                "--pdf-engine=xelatex",
                "-V", "dir=rtl",
                "-V", "lang=ar",
                "-V", "mainfont=Tahoma",
                "-V", "sansfont=Tahoma",
                "-V", "monofont=Consolas",
            ])
        
        # Environment variables will be set in subprocess.run
    else:
        # Fallback to default engine (may not support Arabic well)
        cmd.extend([
            "-V", "dir=rtl",
            "-V", "lang=ar",
        ])
    
    print("[INFO] تحويل Markdown إلى PDF باستخدام Pandoc...")
    print("[INFO] Converting Markdown to PDF using Pandoc...")
    
    try:
        # Set environment for MiKTeX non-interactive mode
        env = os.environ.copy()
        env['MIKTEX_ENABLE_INSTALLER'] = '1'
        env['MIKTEX_NON_INTERACTIVE'] = '1'
        
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes timeout (MiKTeX may need to install packages)
            env=env
        )
        
        if output_file.exists():
            file_size = output_file.stat().st_size / 1024  # KB
            print(f"[SUCCESS] تم إنشاء PDF بنجاح: {output_file}")
            print(f"[SUCCESS] PDF created successfully: {output_file}")
            print(f"[INFO] حجم الملف: {file_size:.1f} KB")
            print(f"[INFO] File size: {file_size:.1f} KB")
        else:
            print("[ERROR] تم تنفيذ الأمر لكن الملف لم يُنشأ!")
            print("[ERROR] Command executed but file was not created!")
            sys.exit(1)
            
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] فشل التحويل: {e}")
        print(f"[ERROR] Conversion failed: {e}")
        if e.stderr:
            print(f"[ERROR] تفاصيل الخطأ:")
            print(f"[ERROR] Error details:")
            print(e.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("[ERROR] انتهت مهلة التحويل (أكثر من دقيقتين)")
        print("[ERROR] Conversion timeout (more than 2 minutes)")
        sys.exit(1)
    except FileNotFoundError:
        print("[ERROR] pandoc غير موجود في PATH")
        print("[ERROR] pandoc not found in PATH")
        sys.exit(1)


if __name__ == "__main__":
    convert_with_pandoc()
