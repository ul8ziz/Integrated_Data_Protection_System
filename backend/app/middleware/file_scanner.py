"""
Middleware for scanning uploaded files for malicious content
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi import status
import logging
import re

logger = logging.getLogger(__name__)


class FileScannerMiddleware(BaseHTTPMiddleware):
    """Middleware to scan files for malicious content before processing"""
    
    # Dangerous file signatures (magic bytes)
    DANGEROUS_SIGNATURES = {
        b'MZ': 'PE executable (Windows)',
        b'\x7fELF': 'ELF executable (Linux)',
        b'\xca\xfe\xba\xbe': 'Java class file',
        b'PK\x03\x04': 'ZIP/Office file (could contain macros)',
    }
    
    # Maximum file size to scan (10MB)
    MAX_SCAN_SIZE = 10 * 1024 * 1024
    
    async def dispatch(self, request: Request, call_next):
        # Only scan file upload endpoints
        if request.method == "POST" and (
            "/api/analyze/file" in str(request.url.path) or
            "/api/monitoring/email" in str(request.url.path)
        ):
            try:
                # Check if request has files
                content_type = request.headers.get("content-type", "")
                if "multipart/form-data" in content_type:
                    # Read request body
                    body = await request.body()
                    
                    # Scan for dangerous patterns
                    scan_result = self._scan_content(body)
                    if not scan_result["safe"]:
                        logger.warning(f"File upload blocked: {scan_result['reason']}")
                        return JSONResponse(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            content={
                                "detail": f"File upload rejected: {scan_result['reason']}",
                                "blocked": True,
                                "reason": scan_result['reason']
                            }
                        )
                
            except Exception as e:
                logger.error(f"Error in file scanner middleware: {e}")
                # Allow request to proceed if scanning fails (fail open for availability)
                # In production, you might want to fail closed
        
        response = await call_next(request)
        return response
    
    def _scan_content(self, content: bytes) -> dict:
        """
        Scan content for malicious patterns
        
        Args:
            content: File content as bytes
            
        Returns:
            Dict with 'safe' (bool) and 'reason' (str) keys
        """
        if not content:
            return {"safe": True, "reason": ""}
        
        # Check file size
        if len(content) > self.MAX_SCAN_SIZE:
            return {"safe": False, "reason": "File too large for scanning"}
        
        # Check magic bytes (file signatures)
        for signature, description in self.DANGEROUS_SIGNATURES.items():
            if content.startswith(signature):
                # Allow ZIP/Office files but warn
                if signature == b'PK\x03\x04':
                    # Check for embedded scripts in Office files
                    if self._check_office_macros(content):
                        return {"safe": False, "reason": f"Office file contains macros: {description}"}
                else:
                    return {"safe": False, "reason": f"Dangerous file type detected: {description}"}
        
        # Convert to string for pattern matching (only first 1MB to avoid memory issues)
        try:
            text_content = content[:1024*1024].decode('utf-8', errors='ignore')
        except Exception:
            # Binary file, check for embedded scripts in binary
            return self._scan_binary_content(content)
        
        # Check for malicious script patterns
        malicious_patterns = [
            (r'<script[^>]*>.*?</script>', 'JavaScript script tag'),
            (r'javascript\s*:', 'JavaScript protocol'),
            (r'eval\s*\(', 'JavaScript/Python eval()'),
            (r'exec\s*\(', 'Python exec()'),
            (r'__import__\s*\(', 'Python __import__()'),
            (r'bash\s+-c', 'Bash command execution'),
            (r'sh\s+-c', 'Shell command execution'),
            (r"'\s*OR\s*['\"]?\s*1\s*=\s*1", 'SQL injection'),
            (r'UNION\s+SELECT', 'SQL UNION injection'),
            (r'<img[^>]*onerror\s*=', 'XSS img onerror'),
        ]
        
        for pattern, description in malicious_patterns:
            if re.search(pattern, text_content, re.IGNORECASE | re.DOTALL):
                return {"safe": False, "reason": f"Malicious pattern detected: {description}"}
        
        return {"safe": True, "reason": ""}
    
    def _check_office_macros(self, content: bytes) -> bool:
        """
        Check if Office file contains macros
        
        Args:
            content: File content as bytes
            
        Returns:
            True if macros detected, False otherwise
        """
        # Look for VBA macro signatures in Office files
        macro_patterns = [
            b'VBA',
            b'Macro',
            b'ThisWorkbook',
            b'ActiveSheet',
            b'Application.Run',
        ]
        
        for pattern in macro_patterns:
            if pattern in content:
                return True
        
        return False
    
    def _scan_binary_content(self, content: bytes) -> dict:
        """
        Scan binary content for dangerous patterns
        
        Args:
            content: Binary content
            
        Returns:
            Dict with 'safe' (bool) and 'reason' (str) keys
        """
        # Check for embedded executables or scripts in binary
        # Look for common script shebangs
        shebangs = [
            b'#!/bin/bash',
            b'#!/bin/sh',
            b'#!/usr/bin/python',
            b'#!/usr/bin/env python',
            b'#!/usr/bin/perl',
        ]
        
        for shebang in shebangs:
            if shebang in content[:1024]:  # Check first 1KB
                return {"safe": False, "reason": f"Executable script detected: {shebang.decode('utf-8', errors='ignore')}"}
        
        return {"safe": True, "reason": ""}
