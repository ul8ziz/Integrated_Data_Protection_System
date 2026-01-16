# تحويل التقرير إلى PDF
# Convert Report to PDF

## الاستخدام / Usage

لتحويل التقرير الفني من Markdown إلى PDF:

```bash
python convert_to_pdf.py
```

سيتم إنشاء ملف `TECHNICAL_REPORT_AR.pdf` في مجلد `docs/`

## المتطلبات / Requirements

```bash
pip install markdown xhtml2pdf
```

## الميزات / Features

- ✅ دعم كامل للغة العربية (RTL)
- ✅ تنسيق واضح ومنسق
- ✅ دعم الكود البرمجي مع تنسيق
- ✅ جداول منسقة
- ✅ عناوين وأقسام واضحة

## الملف الناتج / Output File

`docs/TECHNICAL_REPORT_AR.pdf`

---

## استخدام بديل / Alternative

إذا كنت تفضل استخدام أدوات أخرى:

### باستخدام Pandoc (إن كان مثبتاً):
```bash
pandoc docs/TECHNICAL_REPORT_AR.md -o docs/TECHNICAL_REPORT_AR.pdf --pdf-engine=xelatex -V dir=rtl -V lang=ar
```

### باستخدام Markdown PDF (VS Code Extension):
1. تثبيت extension "Markdown PDF" في VS Code
2. فتح الملف `TECHNICAL_REPORT_AR.md`
3. الضغط على `Ctrl+Shift+P` واختيار "Markdown PDF: Export (pdf)"
