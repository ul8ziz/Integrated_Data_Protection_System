#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
سكريبت لتحويل التقرير الفني من Markdown إلى PDF
Script to convert Technical Report from Markdown to PDF
"""

import os
import sys
import markdown
from pathlib import Path

# Try to import PDF libraries
def check_libraries():
    """Check which PDF libraries are available"""
    REPORTLAB_AVAILABLE = False
    WEASYPRINT_AVAILABLE = False
    PDFKIT_AVAILABLE = False
    XHTML2PDF_AVAILABLE = False
    
    # Check ReportLab (best for Arabic)
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfmetrics
        REPORTLAB_AVAILABLE = True
    except ImportError:
        REPORTLAB_AVAILABLE = False
    
    # Check WeasyPrint (skip if not available to avoid error messages)
    WEASYPRINT_AVAILABLE = False
    # WeasyPrint requires system libraries on Windows, skip it for now
    
    # Check pdfkit
    try:
        import pdfkit  # type: ignore
        PDFKIT_AVAILABLE = True
    except ImportError:
        PDFKIT_AVAILABLE = False
    
    # Check xhtml2pdf
    try:
        from xhtml2pdf import pisa  # type: ignore
        XHTML2PDF_AVAILABLE = True
    except ImportError:
        XHTML2PDF_AVAILABLE = False
    
    return REPORTLAB_AVAILABLE, WEASYPRINT_AVAILABLE, PDFKIT_AVAILABLE, XHTML2PDF_AVAILABLE


def process_arabic_text(text: str) -> str:
    """Process Arabic text for better PDF rendering"""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        
        # Reshape Arabic text and apply bidirectional algorithm
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
        return bidi_text
    except ImportError:
        # If libraries not available, return original text
        return text


def process_arabic_in_html(html_content: str) -> str:
    """Process Arabic text in HTML using arabic_reshaper and python-bidi"""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        import re
        from html.parser import HTMLParser
        from html import unescape
        
        def process_arabic_text(text: str) -> str:
            """Process Arabic text with reshaping and bidi"""
            if not text or not re.search(r'[\u0600-\u06FF]', text):
                return text
            
            try:
                # Reshape Arabic text
                reshaped = arabic_reshaper.reshape(text)
                # Apply bidirectional algorithm
                bidi_text = get_display(reshaped)
                return bidi_text
            except Exception as e:
                print(f"[DEBUG] Error processing Arabic text: {e}")
                return text
        
        # Process text content in HTML tags (but preserve tags and code blocks)
        def process_html_text(match):
            """Process text content within HTML tags"""
            full_match = match.group(0)
            tag_start = match.group(1)
            text_content = match.group(2)
            tag_end = match.group(3)
            
            # Skip if it's a code block or contains HTML entities
            if '<code' in full_match or '<pre' in full_match:
                return full_match
            
            # Process Arabic text
            processed_text = process_arabic_text(text_content)
            return tag_start + processed_text + tag_end
        
        # More comprehensive approach: process all text nodes
        from html.parser import HTMLParser
        from html import unescape
        
        class ArabicHTMLProcessor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.result = []
                self.skip_tags = {'script', 'style', 'code', 'pre'}
                self.current_tag = None
                self.in_skip_tag = False
            
            def handle_starttag(self, tag, attrs):
                self.current_tag = tag
                if tag in self.skip_tags:
                    self.in_skip_tag = True
                attrs_str = ' '.join(f'{k}="{v}"' for k, v in attrs)
                if attrs_str:
                    self.result.append(f'<{tag} {attrs_str}>')
                else:
                    self.result.append(f'<{tag}>')
            
            def handle_endtag(self, tag):
                if tag in self.skip_tags:
                    self.in_skip_tag = False
                self.result.append(f'</{tag}>')
                self.current_tag = None
            
            def handle_data(self, data):
                if not self.in_skip_tag and data.strip():
                    # Process Arabic text
                    processed = process_arabic_text(data)
                    self.result.append(processed)
                else:
                    self.result.append(data)
            
            def get_result(self):
                return ''.join(self.result)
        
        # Use HTMLParser for better processing
        processor = ArabicHTMLProcessor()
        processor.feed(html_content)
        processed_html = processor.get_result()
        
        return processed_html
    except ImportError:
        print("[WARNING] arabic_reshaper أو python-bidi غير مثبت. النص العربي قد لا يظهر بشكل صحيح.")
        print("[WARNING] arabic_reshaper or python-bidi not installed. Arabic text may not display correctly.")
        return html_content
    except Exception as e:
        print(f"[WARNING] خطأ في معالجة النص العربي: {e}")
        return html_content


def create_html_with_rtl(markdown_content: str) -> str:
    """Convert Markdown to HTML with RTL support"""
    
    # Convert Markdown to HTML
    html_content = markdown.markdown(
        markdown_content,
        extensions=['extra', 'codehilite', 'tables', 'fenced_code']
    )
    
    # Process Arabic text in HTML
    html_content = process_arabic_in_html(html_content)
    
    # Create full HTML document with RTL support
    html_template = f"""<!DOCTYPE html>
<html dir="rtl" lang="ar" xmlns="http://www.w3.org/1999/xhtml">
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Language" content="ar" />
    <title>تقرير فني شامل - نظام حماية البيانات المتكامل</title>
    <style>
        @page {{
            size: A4;
            margin: 2cm;
        }}
        
        @font-face {{
            font-family: 'ArabicFont';
            src: local('Tahoma'), local('Arial Unicode MS'), local('DejaVu Sans');
        }}
        
        body {{
            font-family: 'Tahoma', 'ArialUnicodeMS', 'Arial Unicode MS', 'DejaVu Sans', 'Arial', sans-serif;
            -pdf-font-name: 'Tahoma';
            direction: rtl;
            text-align: right;
            line-height: 1.8;
            color: #333;
            font-size: 12pt;
            margin: 0;
            padding: 20px;
        }}
        
        /* Ensure all text elements are RTL */
        p, li, td, th, div, span, h1, h2, h3, h4, h5, h6, blockquote, strong, em {{
            direction: rtl;
            text-align: right;
            -pdf-font-name: 'Tahoma';
        }}
        
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-top: 30px;
            margin-bottom: 20px;
            font-size: 24pt;
            page-break-after: avoid;
        }}
        
        h2 {{
            color: #34495e;
            border-bottom: 2px solid #95a5a6;
            padding-bottom: 8px;
            margin-top: 25px;
            margin-bottom: 15px;
            font-size: 20pt;
            page-break-after: avoid;
        }}
        
        h3 {{
            color: #555;
            margin-top: 20px;
            margin-bottom: 12px;
            font-size: 16pt;
            page-break-after: avoid;
        }}
        
        h4 {{
            color: #666;
            margin-top: 15px;
            margin-bottom: 10px;
            font-size: 14pt;
        }}
        
        p {{
            margin-bottom: 12px;
            text-align: justify;
        }}
        
        ul, ol {{
            margin-right: 30px;
            margin-left: 0;
            margin-bottom: 15px;
            padding-right: 20px;
            padding-left: 0;
            direction: rtl;
            text-align: right;
        }}
        
        li {{
            margin-bottom: 8px;
            margin-right: 0;
            direction: rtl;
            text-align: right;
            list-style-position: inside;
        }}
        
        ul li {{
            list-style-type: disc;
        }}
        
        ol li {{
            list-style-type: decimal;
        }}
        
        code {{
            background-color: #f4f4f4;
            border: 1px solid #ddd;
            border-radius: 3px;
            padding: 2px 6px;
            font-family: 'Courier New', 'Consolas', 'Monaco', monospace;
            font-size: 11pt;
            direction: ltr !important;
            text-align: left !important;
            display: inline-block;
            unicode-bidi: embed;
        }}
        
        pre {{
            background-color: #f8f8f8;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            overflow-x: auto;
            direction: ltr !important;
            text-align: left !important;
            font-family: 'Courier New', 'Consolas', 'Monaco', monospace;
            font-size: 10pt;
            line-height: 1.5;
            page-break-inside: avoid;
            unicode-bidi: embed;
        }}
        
        pre code {{
            background: none;
            border: none;
            padding: 0;
            display: block;
            direction: ltr !important;
            text-align: left !important;
        }}
        
        blockquote {{
            border-right: 4px solid #3498db;
            margin: 15px 0;
            padding-right: 15px;
            padding-left: 15px;
            color: #555;
            font-style: italic;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            page-break-inside: avoid;
        }}
        
        th, td {{
            border: 1px solid #ddd;
            padding: 10px;
            text-align: right;
            direction: rtl;
        }}
        
        /* Ensure table content is RTL */
        table {{
            direction: rtl;
        }}
        
        th {{
            background-color: #3498db;
            color: white;
            font-weight: bold;
        }}
        
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        
        .toc {{
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            padding: 20px;
            margin: 20px 0;
        }}
        
        .toc ul {{
            list-style-type: none;
            padding-right: 0;
        }}
        
        .toc a {{
            color: #3498db;
            text-decoration: none;
        }}
        
        .toc a:hover {{
            text-decoration: underline;
        }}
        
        hr {{
            border: none;
            border-top: 2px solid #ddd;
            margin: 30px 0;
        }}
        
        strong {{
            color: #2c3e50;
            font-weight: bold;
        }}
        
        em {{
            font-style: italic;
            color: #555;
        }}
        
        /* Print styles */
        @media print {{
            body {{
                padding: 0;
            }}
        }}
    </style>
</head>
<body>
    {html_content}
</body>
</html>"""
    
    return html_template


def convert_with_reportlab(markdown_content: str, output_path: str):
    """Convert Markdown to PDF using ReportLab directly (best Arabic support)"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib import colors
    import re
    from html.parser import HTMLParser
    
    # Check for Arabic support libraries
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        ARABIC_SUPPORT = True
    except ImportError:
        ARABIC_SUPPORT = False
        print("[WARNING] arabic_reshaper أو python-bidi غير مثبت. النص العربي قد لا يظهر بشكل صحيح.")
    
    # Register Arabic fonts
    font_paths = [
        (r'C:\Windows\Fonts\arialuni.ttf', 'ArialUnicodeMS'),
        (r'C:\Windows\Fonts\tahoma.ttf', 'Tahoma'),
        (r'C:\Windows\Fonts\tahomabd.ttf', 'TahomaBold'),
        (r'C:\Windows\Fonts\arial.ttf', 'Arial'),
    ]
    
    arabic_font = 'Tahoma'
    for font_path, font_name in font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                arabic_font = font_name
                break
            except:
                pass
    
    # Convert markdown to HTML
    html_content = markdown.markdown(
        markdown_content,
        extensions=['extra', 'codehilite', 'tables', 'fenced_code']
    )
    
    # Create PDF with custom page template
    from reportlab.platypus import PageTemplate, BaseDocTemplate, Frame
    from reportlab.lib.units import mm
    
    class NumberedCanvas:
        """Custom canvas for page numbers and headers"""
        def __init__(self, canvas, doc):
            self.canvas = canvas
            self.doc = doc
            
        def draw_page_number(self, canvas, doc):
            """Draw page number"""
            page_num = canvas.getPageNumber()
            text = f"صفحة {page_num}"
            canvas.saveState()
            canvas.setFont(arabic_font, 10)
            canvas.setFillColor(colors.grey)
            # Right bottom corner (RTL)
            canvas.drawRightString(A4[0] - 2*cm, 1*cm, text)
            canvas.restoreState()
        
        def draw_header(self, canvas, doc):
            """Draw header"""
            canvas.saveState()
            canvas.setFont(arabic_font, 10)
            canvas.setFillColor(colors.HexColor('#3498db'))
            # Header text
            header_text = "تقرير فني شامل - نظام حماية البيانات المتكامل"
            canvas.drawRightString(A4[0] - 2*cm, A4[1] - 1.5*cm, header_text)
            # Header line
            canvas.setStrokeColor(colors.HexColor('#3498db'))
            canvas.setLineWidth(0.5)
            canvas.line(2*cm, A4[1] - 2*cm, A4[0] - 2*cm, A4[1] - 2*cm)
            canvas.restoreState()
    
    # Create PDF
    doc = BaseDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2.5*cm,
        leftMargin=2.5*cm,
        topMargin=3*cm,
        bottomMargin=2.5*cm
    )
    
    # Create frame
    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        leftPadding=0,
        bottomPadding=0,
        rightPadding=0,
        topPadding=0,
        id='normal'
    )
    
    # Process Arabic text for canvas
    def process_arabic_for_canvas(text: str) -> str:
        """Process Arabic text for canvas drawing"""
        if not text or not re.search(r'[\u0600-\u06FF]', text):
            return text
        try:
            if ARABIC_SUPPORT:
                reshaped = arabic_reshaper.reshape(text)
                bidi_text = get_display(reshaped)
                return bidi_text
            return text
        except:
            return text
    
    # Create page template with footer only (no headers/titles)
    def on_first_page(canvas, doc):
        canvas.saveState()
        # Footer - Page number only
        page_num = canvas.getPageNumber()
        text = process_arabic_for_canvas(f"صفحة {page_num}")
        canvas.setFont(arabic_font, 9)
        canvas.setFillColor(colors.grey)
        canvas.drawRightString(A4[0] - 2.5*cm, 1.5*cm, text)
        canvas.restoreState()
    
    def on_later_pages(canvas, doc):
        canvas.saveState()
        # Footer - Page number only
        page_num = canvas.getPageNumber()
        text = process_arabic_for_canvas(f"صفحة {page_num}")
        canvas.setFont(arabic_font, 9)
        canvas.setFillColor(colors.grey)
        canvas.drawRightString(A4[0] - 2.5*cm, 1.5*cm, text)
        canvas.restoreState()
    
    # Create page templates - use first page template for first page, later pages template for rest
    first_page_template = PageTemplate(id='FirstPage', frames=frame, onPage=on_first_page)
    later_pages_template = PageTemplate(id='LaterPages', frames=frame, onPage=on_later_pages)
    doc.addPageTemplates([first_page_template, later_pages_template])
    
    # Create styles with better formatting
    styles = getSampleStyleSheet()
    
    arabic_normal = ParagraphStyle(
        'ArabicNormal',
        parent=styles['Normal'],
        fontName=arabic_font,
        fontSize=11,
        alignment=TA_RIGHT,
        leading=20,
        spaceBefore=6,
        spaceAfter=6,
        leftIndent=0,
        rightIndent=0,
    )
    
    arabic_heading1 = ParagraphStyle(
        'ArabicHeading1',
        parent=styles['Heading1'],
        fontName=arabic_font,
        fontSize=22,
        alignment=TA_RIGHT,
        textColor=colors.HexColor('#2c3e50'),
        spaceBefore=25,
        spaceAfter=15,
    )
    
    arabic_heading2 = ParagraphStyle(
        'ArabicHeading2',
        parent=styles['Heading2'],
        fontName=arabic_font,
        fontSize=18,
        alignment=TA_RIGHT,
        textColor=colors.HexColor('#34495e'),
        spaceBefore=20,
        spaceAfter=12,
    )
    
    arabic_heading3 = ParagraphStyle(
        'ArabicHeading3',
        parent=styles['Heading3'],
        fontName=arabic_font,
        fontSize=14,
        alignment=TA_RIGHT,
        textColor=colors.HexColor('#555'),
        spaceBefore=15,
        spaceAfter=10,
    )
    
    arabic_heading4 = ParagraphStyle(
        'ArabicHeading4',
        parent=styles['Heading4'],
        fontName=arabic_font,
        fontSize=12,
        alignment=TA_RIGHT,
        textColor=colors.HexColor('#666'),
        spaceBefore=12,
        spaceAfter=8,
    )
    
    story = []
    
    class HTMLToReportLab(HTMLParser):
        def __init__(self, arabic_support_flag):
            super().__init__()
            self.current_text = []
            self.current_style = arabic_normal
            self.skip_tags = {'script', 'style', 'code', 'pre'}
            self.in_skip = False
            self.arabic_support = arabic_support_flag
            self.list_level = 0
            self.in_list = False
            
        def handle_starttag(self, tag, attrs):
            if tag in self.skip_tags:
                self.in_skip = True
                return
            if tag == 'h1':
                self._flush_text()
                story.append(Spacer(1, 5))
                self.current_style = arabic_heading1
            elif tag == 'h2':
                self._flush_text()
                story.append(Spacer(1, 5))
                self.current_style = arabic_heading2
            elif tag == 'h3':
                self._flush_text()
                story.append(Spacer(1, 4))
                self.current_style = arabic_heading3
            elif tag == 'h4':
                self._flush_text()
                story.append(Spacer(1, 3))
                self.current_style = arabic_heading4
            elif tag == 'p':
                self._flush_text()
                self.current_style = arabic_normal
            elif tag == 'ul' or tag == 'ol':
                self.in_list = True
                self.list_level += 1
            elif tag == 'li':
                self._flush_text()
                # Add bullet or number
                if self.list_level > 0:
                    bullet = "• " if tag == 'ul' else f"{self.list_level}. "
                    self.current_text.append(bullet)
                self.current_style = arabic_normal
            elif tag == 'strong' or tag == 'b':
                # Bold text - will be handled in text processing
                pass
            elif tag == 'em' or tag == 'i':
                # Italic text
                pass
            elif tag == 'br':
                self._flush_text()
                story.append(Spacer(1, 6))
        
        def handle_endtag(self, tag):
            if tag in self.skip_tags:
                self.in_skip = False
                return
            if tag == 'ul' or tag == 'ol':
                self.list_level = max(0, self.list_level - 1)
                if self.list_level == 0:
                    self.in_list = False
                story.append(Spacer(1, 8))
            elif tag in ['h1', 'h2', 'h3', 'h4']:
                self._flush_text()
                # Add line under heading
                from reportlab.platypus import HRFlowable
                if tag == 'h1':
                    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#3498db'), spaceAfter=10))
                elif tag == 'h2':
                    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#95a5a6'), spaceAfter=8))
                story.append(Spacer(1, 5))
            elif tag == 'p':
                self._flush_text()
                story.append(Spacer(1, 8))
            elif tag == 'li':
                self._flush_text()
                story.append(Spacer(1, 4))
        
        def handle_data(self, data):
            if not self.in_skip and data.strip():
                # Process Arabic text
                if self.arabic_support and re.search(r'[\u0600-\u06FF]', data):
                    try:
                        reshaped = arabic_reshaper.reshape(data)
                        bidi_text = get_display(reshaped)
                        self.current_text.append(bidi_text)
                    except:
                        self.current_text.append(data)
                else:
                    self.current_text.append(data)
        
        def _flush_text(self):
            if self.current_text:
                text = ''.join(self.current_text)
                text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                if text.strip():
                    story.append(Paragraph(text, self.current_style))
                self.current_text = []
    
    parser = HTMLToReportLab(ARABIC_SUPPORT)
    parser.feed(html_content)
    parser._flush_text()
    
    # Build PDF with page templates
    doc.build(story)


def convert_with_weasyprint(html_content: str, output_path: str):
    """Convert HTML to PDF using WeasyPrint"""
    from weasyprint import HTML, CSS  # type: ignore
    HTML(string=html_content).write_pdf(
        output_path,
        stylesheets=[CSS(string="""
            @page {
                size: A4;
                margin: 2cm;
            }
        """)]
    )


def convert_with_pdfkit(html_content: str, output_path: str):
    """Convert HTML to PDF using pdfkit (requires wkhtmltopdf)"""
    import pdfkit  # type: ignore
    options = {
        'page-size': 'A4',
        'margin-top': '2cm',
        'margin-right': '2cm',
        'margin-bottom': '2cm',
        'margin-left': '2cm',
        'encoding': "UTF-8",
        'enable-local-file-access': None
    }
    pdfkit.from_string(html_content, output_path, options=options)


def convert_with_xhtml2pdf(html_content: str, output_path: str):
    """Convert HTML to PDF using xhtml2pdf with Arabic support"""
    from xhtml2pdf import pisa  # type: ignore
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import os
    
    # Register Arabic fonts with ReportLab for better rendering
    # xhtml2pdf uses ReportLab under the hood
    try:
        # Try to find and register fonts that support Arabic
        font_paths = [
            (r'C:\Windows\Fonts\arialuni.ttf', 'ArialUnicodeMS'),  # Best Arabic support
            (r'C:\Windows\Fonts\tahoma.ttf', 'Tahoma'),
            (r'C:\Windows\Fonts\tahomabd.ttf', 'TahomaBold'),
            (r'C:\Windows\Fonts\arial.ttf', 'Arial'),
        ]
        
        registered = False
        for font_path, font_name in font_paths:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                    registered = True
                    print(f"[INFO] تم تسجيل الخط: {font_name}")
                except Exception:
                    pass
        
        if not registered:
            print("[WARNING] لم يتم العثور على خطوط عربية. قد يظهر النص كـ squares.")
            print("[WARNING] Arabic fonts not found. Text may appear as squares.")
    except Exception as e:
        print(f"[WARNING] خطأ في تسجيل الخطوط: {e}")
    
    # Save HTML to temporary file with UTF-8 BOM to ensure proper encoding
    import tempfile
    import codecs
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8-sig') as tmp_file:
        # Write UTF-8 BOM for better compatibility
        tmp_file.write('\ufeff')  # UTF-8 BOM
        tmp_file.write(html_content)
        tmp_html_path = tmp_file.name
    
    try:
        with open(output_path, 'wb') as pdf_file:
            # Read from file with UTF-8 encoding
            with open(tmp_html_path, 'rb') as html_file:
                result = pisa.CreatePDF(
                    src=html_file,
                    dest=pdf_file,
                    encoding='utf-8',
                    link_callback=None,
                    show_error_as_pdf=True
                )
            
            if result.err:
                raise Exception(f"Error creating PDF: {result.err}")
            
            pdf_file.close()
    finally:
        # Clean up temporary file
        try:
            os.unlink(tmp_html_path)
        except:
            pass


def main():
    """Main function"""
    # Set UTF-8 encoding for console output
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    # Get the markdown file path
    script_dir = Path(__file__).parent
    md_file = script_dir / "docs" / "TECHNICAL_REPORT_AR.md"
    output_file = script_dir / "docs" / "TECHNICAL_REPORT_AR.pdf"
    
    if not md_file.exists():
        print(f"[ERROR] الملف غير موجود: {md_file}")
        print(f"[ERROR] File not found: {md_file}")
        sys.exit(1)
    
    print("[INFO] قراءة ملف Markdown...")
    print("[INFO] Reading Markdown file...")
    
    # Read markdown file
    with open(md_file, 'r', encoding='utf-8') as f:
        markdown_content = f.read()
    
    print("[INFO] تحويل Markdown إلى HTML...")
    print("[INFO] Converting Markdown to HTML...")
    
    # Convert to HTML with RTL
    html_content = create_html_with_rtl(markdown_content)
    
    print("[INFO] تحويل HTML إلى PDF...")
    print("[INFO] Converting HTML to PDF...")
    
    # Check available libraries
    REPORTLAB_AVAILABLE, WEASYPRINT_AVAILABLE, PDFKIT_AVAILABLE, XHTML2PDF_AVAILABLE = check_libraries()
    
    # Print available libraries (only if debug needed)
    if not REPORTLAB_AVAILABLE and not XHTML2PDF_AVAILABLE and not PDFKIT_AVAILABLE:
        print(f"[DEBUG] المكتبات المتاحة / Available libraries:")
        print(f"[DEBUG]   reportlab: {REPORTLAB_AVAILABLE}")
        print(f"[DEBUG]   xhtml2pdf: {XHTML2PDF_AVAILABLE}")
        print(f"[DEBUG]   pdfkit: {PDFKIT_AVAILABLE}")
        print(f"[DEBUG]   weasyprint: {WEASYPRINT_AVAILABLE}")
    
    # Try different PDF libraries (ReportLab first for best Arabic support)
    success = False
    
    if REPORTLAB_AVAILABLE:
        try:
            print("[INFO] استخدام ReportLab (أفضل دعم للعربية)...")
            convert_with_reportlab(markdown_content, str(output_file))
            success = True
            print(f"[SUCCESS] تم إنشاء PDF بنجاح: {output_file}")
            print(f"[SUCCESS] PDF created successfully: {output_file}")
        except Exception as e:
            print(f"[ERROR] خطأ في ReportLab: {e}")
            success = False
    
    if not success and XHTML2PDF_AVAILABLE:
        try:
            print("[INFO] استخدام xhtml2pdf...")
            convert_with_xhtml2pdf(html_content, str(output_file))
            success = True
            print(f"[SUCCESS] تم إنشاء PDF بنجاح: {output_file}")
            print(f"[SUCCESS] PDF created successfully: {output_file}")
        except Exception as e:
            print(f"[ERROR] خطأ في xhtml2pdf: {e}")
            success = False
    
    if not success and PDFKIT_AVAILABLE:
        try:
            print("[INFO] استخدام pdfkit...")
            convert_with_pdfkit(html_content, str(output_file))
            success = True
            print(f"[SUCCESS] تم إنشاء PDF بنجاح: {output_file}")
            print(f"[SUCCESS] PDF created successfully: {output_file}")
        except Exception as e:
            print(f"[ERROR] خطأ في pdfkit: {e}")
            success = False
    
    if not success and WEASYPRINT_AVAILABLE:
        try:
            print("[INFO] استخدام WeasyPrint...")
            convert_with_weasyprint(html_content, str(output_file))
            success = True
            print(f"[SUCCESS] تم إنشاء PDF بنجاح: {output_file}")
            print(f"[SUCCESS] PDF created successfully: {output_file}")
        except Exception as e:
            print(f"[ERROR] خطأ في WeasyPrint: {e}")
            success = False
    
    if not success:
        print("\n[ERROR] لم يتم العثور على مكتبة PDF متاحة!")
        print("[ERROR] No PDF library found!")
        print("\n[INFO] يرجى تثبيت إحدى المكتبات التالية:")
        print("[INFO] Please install one of the following libraries:")
        print("   pip install reportlab  # الأفضل للعربية / Best for Arabic")
        print("   pip install xhtml2pdf")
        print("   pip install pdfkit  # requires wkhtmltopdf")
        print("   pip install weasyprint")
        print("\n   pip install markdown arabic-reshaper python-bidi")
        sys.exit(1)


if __name__ == "__main__":
    main()
