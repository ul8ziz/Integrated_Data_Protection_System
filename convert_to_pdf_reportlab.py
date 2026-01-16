#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
سكريبت لتحويل التقرير الفني من Markdown إلى PDF باستخدام ReportLab مباشرة
Script to convert Technical Report from Markdown to PDF using ReportLab directly
هذا يوفر دعم أفضل للغة العربية
This provides better Arabic support
"""

import sys
import os
from pathlib import Path
import markdown
import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.platypus.flowables import Image
from reportlab.lib.enums import TA_RIGHT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
import re


def register_arabic_fonts():
    """Register Arabic fonts with ReportLab"""
    font_paths = [
        (r'C:\Windows\Fonts\arialuni.ttf', 'ArialUnicodeMS'),
        (r'C:\Windows\Fonts\tahoma.ttf', 'Tahoma'),
        (r'C:\Windows\Fonts\tahomabd.ttf', 'TahomaBold'),
        (r'C:\Windows\Fonts\arial.ttf', 'Arial'),
    ]
    
    registered_fonts = []
    for font_path, font_name in font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                registered_fonts.append(font_name)
                print(f"[INFO] تم تسجيل الخط: {font_name}")
            except Exception as e:
                print(f"[DEBUG] فشل تسجيل {font_name}: {e}")
    
    return registered_fonts[0] if registered_fonts else 'Helvetica'


def process_arabic_text(text: str) -> str:
    """Process Arabic text for proper display"""
    if not text or not re.search(r'[\u0600-\u06FF]', text):
        return text
    
    try:
        reshaped = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped)
        return bidi_text
    except Exception:
        return text


def markdown_to_pdf(md_file: Path, output_file: Path, arabic_font: str = 'Tahoma'):
    """Convert Markdown to PDF with Arabic support"""
    
    # Read markdown file
    with open(md_file, 'r', encoding='utf-8') as f:
        markdown_content = f.read()
    
    # Convert markdown to HTML first
    html_content = markdown.markdown(
        markdown_content,
        extensions=['extra', 'codehilite', 'tables', 'fenced_code']
    )
    
    # Create PDF
    doc = SimpleDocTemplate(
        str(output_file),
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # Create styles
    styles = getSampleStyleSheet()
    
    # Arabic styles with RTL
    arabic_normal = ParagraphStyle(
        'ArabicNormal',
        parent=styles['Normal'],
        fontName=arabic_font,
        fontSize=12,
        alignment=TA_RIGHT,
        leading=22,
        rightIndent=0,
        leftIndent=0,
    )
    
    arabic_heading1 = ParagraphStyle(
        'ArabicHeading1',
        parent=styles['Heading1'],
        fontName=arabic_font,
        fontSize=24,
        alignment=TA_RIGHT,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=20,
    )
    
    arabic_heading2 = ParagraphStyle(
        'ArabicHeading2',
        parent=styles['Heading2'],
        fontName=arabic_font,
        fontSize=20,
        alignment=TA_RIGHT,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=15,
    )
    
    arabic_heading3 = ParagraphStyle(
        'ArabicHeading3',
        parent=styles['Heading3'],
        fontName=arabic_font,
        fontSize=16,
        alignment=TA_RIGHT,
        spaceAfter=12,
    )
    
    # Build story (content)
    story = []
    
    # Parse HTML properly
    from html.parser import HTMLParser
    from html import unescape
    
    class HTMLToReportLab(HTMLParser):
        def __init__(self, story, arabic_font):
            super().__init__()
            self.story = story
            self.arabic_font = arabic_font
            self.current_text = []
            self.current_style = arabic_normal
            self.skip_tags = {'script', 'style', 'code', 'pre'}
            self.in_skip = False
            
        def handle_starttag(self, tag, attrs):
            if tag in self.skip_tags:
                self.in_skip = True
                return
            
            if tag == 'h1':
                self.current_style = arabic_heading1
            elif tag == 'h2':
                self.current_style = arabic_heading2
            elif tag == 'h3':
                self.current_style = arabic_heading3
            elif tag == 'h4':
                self.current_style = arabic_heading3
            elif tag == 'p':
                self.current_style = arabic_normal
            elif tag == 'br':
                if self.current_text:
                    self._flush_text()
                self.story.append(Spacer(1, 6))
        
        def handle_endtag(self, tag):
            if tag in self.skip_tags:
                self.in_skip = False
                return
            
            if tag in ['h1', 'h2', 'h3', 'h4', 'p', 'li', 'td', 'th']:
                self._flush_text()
                self.story.append(Spacer(1, 8))
            elif tag == 'ul' or tag == 'ol':
                self.story.append(Spacer(1, 12))
        
        def handle_data(self, data):
            if not self.in_skip and data.strip():
                # Process Arabic text
                processed = process_arabic_text(data)
                self.current_text.append(processed)
        
        def _flush_text(self):
            if self.current_text:
                text = ''.join(self.current_text)
                # Escape for ReportLab
                text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                if text.strip():
                    story.append(Paragraph(text, self.current_style))
                self.current_text = []
    
    # Parse HTML
    parser = HTMLToReportLab(story, arabic_font)
    parser.feed(html_content)
    parser._flush_text()  # Flush any remaining text
    
    # Build PDF
    doc.build(story)
    print(f"[SUCCESS] تم إنشاء PDF بنجاح: {output_file}")


def main():
    """Main function"""
    # Set UTF-8 encoding for console
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    # Register Arabic fonts
    print("[INFO] تسجيل الخطوط العربية...")
    arabic_font = register_arabic_fonts()
    
    # Get file paths
    script_dir = Path(__file__).parent
    md_file = script_dir / "docs" / "TECHNICAL_REPORT_AR.md"
    output_file = script_dir / "docs" / "TECHNICAL_REPORT_AR.pdf"
    
    if not md_file.exists():
        print(f"[ERROR] الملف غير موجود: {md_file}")
        sys.exit(1)
    
    print("[INFO] قراءة ملف Markdown...")
    print("[INFO] تحويل Markdown إلى PDF...")
    
    try:
        markdown_to_pdf(md_file, output_file, arabic_font)
        print(f"[SUCCESS] PDF created successfully: {output_file}")
    except Exception as e:
        print(f"[ERROR] فشل التحويل: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
