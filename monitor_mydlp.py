#!/usr/bin/env python3
"""
MyDLP Monitoring Script
يعرض مراقبة MyDLP في الوقت الفعلي
"""
import requests
import time
import json
import os
from datetime import datetime
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"
LOG_FILE = Path("backend/logs/app.log")

def clear_screen():
    """Clear console screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def get_mydlp_status():
    """Get MyDLP status from API"""
    try:
        response = requests.get(f"{BASE_URL}/api/monitoring/status", timeout=2)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

def get_recent_alerts():
    """Get recent alerts"""
    try:
        response = requests.get(f"{BASE_URL}/api/alerts/?limit=5", timeout=2)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return []

def get_recent_logs(lines=20):
    """Get recent log lines"""
    if LOG_FILE.exists():
        try:
            with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
                return all_lines[-lines:] if len(all_lines) > lines else all_lines
        except:
            pass
    return []

def format_status(status_data):
    """Format status data for display"""
    if not status_data:
        return "[ERROR] Server not responding - Make sure server is running!"
    
    mydlp = status_data.get("mydlp", {})
    presidio = status_data.get("presidio", {})
    
    result = []
    result.append("[SYSTEM STATUS]")
    result.append(f"  Presidio: {'[OK] Operational' if presidio.get('status') == 'operational' else '[ERROR]'}")
    
    if mydlp.get("enabled"):
        mode = "Localhost" if mydlp.get("is_localhost") else "Network"
        status = mydlp.get("status", "unknown")
        result.append(f"  MyDLP:   [OK] {status} ({mode} Mode)")
    else:
        result.append("  MyDLP:   [WARNING] Disabled (Simulation Mode)")
    
    return "\n".join(result)

def format_alerts(alerts):
    """Format alerts for display"""
    if not alerts:
        return "  No recent alerts"
    
    result = []
    for alert in alerts[:5]:
        severity = alert.get("severity", "unknown")
        title = alert.get("title", "No title")
        status = alert.get("status", "unknown")
        created = alert.get("created_at", "")
        if created:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                created = dt.strftime('%H:%M:%S')
            except:
                pass
        result.append(f"  [{severity.upper():8}] {title[:40]:40} [{status}] {created}")
    
    return "\n".join(result)

def main():
    """Main monitoring loop"""
    print("=" * 60)
    print("MyDLP Real-time Monitoring Dashboard")
    print("مراقبة MyDLP في الوقت الفعلي")
    print("=" * 60)
    print("\nPress Ctrl+C to stop\n")
    
    try:
        while True:
            clear_screen()
            
            print("=" * 60)
            print(f"MyDLP Monitoring - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 60)
            print()
            
            # Get status
            status = get_mydlp_status()
            print(format_status(status))
            print()
            
            # Get alerts
            print("🚨 Recent Alerts:")
            alerts = get_recent_alerts()
            print(format_alerts(alerts))
            print()
            
            # Get logs
            print("[RECENT LOGS - MyDLP Related]")
            print("-" * 60)
            logs = get_recent_logs(20)
            mydlp_logs = []
            for line in logs:
                line_lower = line.lower()
                # Filter MyDLP related logs
                if any(keyword in line_lower for keyword in ['mydlp', 'block', 'policy', 'alert', 'sensitive', 'entity', 'detected']):
                    mydlp_logs.append(line.rstrip())
            
            if mydlp_logs:
                for log in mydlp_logs[-10:]:  # Show last 10 MyDLP related logs
                    print(log)
            else:
                print("  No MyDLP-related logs yet")
            print("-" * 60)
            print()
            
            print("=" * 60)
            print("Refreshing every 3 seconds... (Ctrl+C to stop)")
            print("=" * 60)
            
            time.sleep(3)
            
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")
        print("Server is still running at http://127.0.0.1:8000")

if __name__ == "__main__":
    main()

