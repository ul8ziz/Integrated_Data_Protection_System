"""
API routes for receiving real emails from email servers
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from app.database import get_db
from app.services.email_monitoring_service import EmailMonitoringService
import logging
import email
from email.utils import parseaddr

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/email", tags=["Email Receiver"])

email_monitoring = EmailMonitoringService()


@router.post("/receive")
async def receive_email(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Receive email from email server (SMTP webhook, IMAP, etc.)
    
    This endpoint can be called by:
    - Email servers (via webhook)
    - SMTP proxies
    - Email gateways
    - Custom email handlers
    
    Expected payload format:
    {
        "from": "sender@example.com",
        "to": ["recipient@example.com"],
        "subject": "Email subject",
        "body": "Email body text",
        "html_body": "<html>...</html>",  # optional
        "attachments": [{"filename": "file.pdf", "content": "base64..."}],  # optional
        "headers": {},  # optional
        "source_ip": "192.168.1.1",  # optional
        "source_user": "sender@example.com"  # optional
    }
    """
    try:
        # Get email data from request
        data = await request.json()
        
        # Extract email information
        from_email = data.get("from", "")
        to_emails = data.get("to", [])
        subject = data.get("subject", "")
        body = data.get("body", "")
        html_body = data.get("html_body", "")
        attachments = data.get("attachments", [])
        source_ip = data.get("source_ip", request.client.host if request.client else "127.0.0.1")
        source_user = data.get("source_user", from_email)
        
        # Use HTML body if available, otherwise use plain text
        email_body = html_body if html_body else body
        
        # Prepare email data for monitoring
        email_data = {
            "from": from_email,
            "to": to_emails if isinstance(to_emails, list) else [to_emails],
            "subject": subject,
            "body": email_body,
            "attachments": attachments,
            "source_ip": source_ip,
            "source_user": source_user
        }
        
        # Analyze email
        result = email_monitoring.analyze_email(db=db, email_data=email_data)
        
        # Return result
        return {
            "received": True,
            "analysis": result,
            "action": result.get("action", "allow"),
            "blocked": result.get("blocked", False),
            "message": result.get("message", "Email processed")
        }
        
    except Exception as e:
        logger.error(f"Error receiving email: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing email: {str(e)}")


@router.post("/receive/raw")
async def receive_raw_email(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Receive raw email (RFC 2822 format) from email server
    
    This endpoint accepts raw email messages in RFC 2822 format
    and parses them automatically.
    """
    try:
        # Get raw email content
        raw_email = await request.body()
        raw_email_str = raw_email.decode('utf-8', errors='ignore')
        
        # Parse email
        msg = email.message_from_string(raw_email_str)
        
        # Extract email information
        from_email = parseaddr(msg.get("From", ""))[1] or "unknown@localhost"
        to_header = msg.get("To", "")
        cc_header = msg.get("Cc", "")
        bcc_header = msg.get("Bcc", "")
        
        # Parse recipients
        to_emails = []
        if to_header:
            to_emails.extend([parseaddr(addr)[1] for addr in to_header.split(",")])
        if cc_header:
            to_emails.extend([parseaddr(addr)[1] for addr in cc_header.split(",")])
        if bcc_header:
            to_emails.extend([parseaddr(addr)[1] for addr in bcc_header.split(",")])
        
        to_emails = [e for e in to_emails if e]  # Remove empty emails
        
        subject = msg.get("Subject", "")
        
        # Extract body
        body = ""
        html_body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                elif content_type == "text/html":
                    html_body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
        else:
            body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        
        # Extract attachments
        attachments = []
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_disposition() == "attachment":
                    filename = part.get_filename()
                    if filename:
                        attachments.append({
                            "filename": filename,
                            "content_type": part.get_content_type()
                        })
        
        # Get source IP from headers or request
        source_ip = request.client.host if request.client else "127.0.0.1"
        received_headers = msg.get_all("Received", [])
        if received_headers:
            # Try to extract IP from Received header
            for header in received_headers:
                if "from" in header.lower():
                    # Simple extraction - can be improved
                    import re
                    ip_match = re.search(r'\d+\.\d+\.\d+\.\d+', header)
                    if ip_match:
                        source_ip = ip_match.group()
                        break
        
        # Prepare email data
        email_data = {
            "from": from_email,
            "to": to_emails,
            "subject": subject,
            "body": html_body if html_body else body,
            "attachments": attachments,
            "source_ip": source_ip,
            "source_user": from_email
        }
        
        # Analyze email
        result = email_monitoring.analyze_email(db=db, email_data=email_data)
        
        return {
            "received": True,
            "parsed": True,
            "analysis": result,
            "action": result.get("action", "allow"),
            "blocked": result.get("blocked", False),
            "message": result.get("message", "Email processed")
        }
        
    except Exception as e:
        logger.error(f"Error receiving raw email: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing raw email: {str(e)}")


@router.get("/webhook/info")
async def webhook_info():
    """
    Get information about email webhook endpoints
    """
    return {
        "endpoints": {
            "json": {
                "url": "/api/email/receive",
                "method": "POST",
                "description": "Receive email in JSON format",
                "payload": {
                    "from": "sender@example.com",
                    "to": ["recipient@example.com"],
                    "subject": "Email subject",
                    "body": "Email body text",
                    "html_body": "<html>...</html>",  # optional
                    "attachments": [],  # optional
                    "source_ip": "192.168.1.1",  # optional
                    "source_user": "sender@example.com"  # optional
                }
            },
            "raw": {
                "url": "/api/email/receive/raw",
                "method": "POST",
                "description": "Receive raw email (RFC 2822 format)",
                "content_type": "message/rfc822 or text/plain",
                "example": "Raw email message in RFC 2822 format"
            }
        },
        "integration": {
            "smtp_proxy": "Configure your SMTP proxy to forward emails to these endpoints",
            "email_gateway": "Use these endpoints as webhook URLs in your email gateway",
            "custom_script": "Send emails from your custom scripts using these endpoints"
        }
    }

