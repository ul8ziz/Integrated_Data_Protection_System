# حل مشكلة عرض النص العربي في PDF
# Fix Arabic Text Display in PDF

## المشكلة / Problem

النص العربي يظهر كـ squares (مربعات) في PDF المولّد باستخدام `xhtml2pdf`.

## الحلول / Solutions

### الحل 1: استخدام Pandoc مع XeLaTeX (الأفضل) ✅

`pandoc` مع `xelatex` يوفر أفضل دعم للغة العربية في PDF.

#### التثبيت / Installation

**Windows:**
```bash
# تثبيت MiKTeX أو TeX Live (يتضمن xelatex)
# ثم تثبيت pandoc:
choco install pandoc
# أو
scoop install pandoc
```

**Linux:**
```bash
sudo apt-get install pandoc texlive-xetex texlive-fonts-recommended
```

**macOS:**
```bash
brew install pandoc
brew install --cask mactex
```

#### الاستخدام / Usage

```bash
pandoc docs/TECHNICAL_REPORT_AR.md -o docs/TECHNICAL_REPORT_AR.pdf \
  --pdf-engine=xelatex \
  -V dir=rtl \
  -V lang=ar \
  -V mainfont="Arial Unicode MS" \
  -V geometry:margin=2cm \
  --toc
```

أو استخدام ملف إعداد مخصص:

```bash
pandoc docs/TECHNICAL_REPORT_AR.md -o docs/TECHNICAL_REPORT_AR.pdf \
  --pdf-engine=xelatex \
  --template=arabic_template.tex
```

### الحل 2: استخدام WeasyPrint (يتطلب مكتبات نظام)

WeasyPrint يدعم العربية بشكل أفضل من xhtml2pdf.

#### التثبيت / Installation

**Windows:**
```bash
# تثبيت GTK+ Runtime
# ثم:
pip install weasyprint
```

**Linux:**
```bash
sudo apt-get install python3-cffi python3-brotli libpango-1.0-0 libpangoft2-1.0-0
pip install weasyprint
```

### الحل 3: تحسين xhtml2pdf الحالي

تم تحسين السكريبت الحالي لـ:
- ✅ تسجيل خطوط عربية (Tahoma, Arial Unicode MS)
- ✅ استخدام `-pdf-font-name` في CSS
- ✅ معالجة النص العربي باستخدام `arabic_reshaper` و `python-bidi`

لكن قد لا يزال هناك مشاكل في بعض الحالات.

#### للتحقق من الخطوط المتاحة:

```python
from reportlab.pdfbase import pdfmetrics
print(pdfmetrics.getRegisteredFontNames())
```

## التوصية / Recommendation

**استخدم Pandoc مع XeLaTeX للحصول على أفضل نتائج للعربية.**

## سكريبت مساعد / Helper Script

يمكنك إنشاء سكريبت `convert_to_pdf_pandoc.py`:

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import subprocess
import sys
from pathlib import Path

def convert_with_pandoc():
    script_dir = Path(__file__).parent
    md_file = script_dir / "docs" / "TECHNICAL_REPORT_AR.md"
    output_file = script_dir / "docs" / "TECHNICAL_REPORT_AR.pdf"
    
    cmd = [
        "pandoc",
        str(md_file),
        "-o", str(output_file),
        "--pdf-engine=xelatex",
        "-V", "dir=rtl",
        "-V", "lang=ar",
        "-V", "mainfont=Arial Unicode MS",
        "-V", "geometry:margin=2cm",
        "--toc"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print(f"[SUCCESS] تم إنشاء PDF بنجاح: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] فشل التحويل: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("[ERROR] pandoc غير مثبت. يرجى تثبيته أولاً.")
        sys.exit(1)

if __name__ == "__main__":
    convert_with_pandoc()
```

## مراجع / References

- [Pandoc User's Guide](https://pandoc.org/MANUAL.html)
- [XeLaTeX Arabic Support](https://www.overleaf.com/learn/latex/Arabic)
- [WeasyPrint Documentation](https://weasyprint.org/)
