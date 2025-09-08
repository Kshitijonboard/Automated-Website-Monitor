
import requests
import time
import json
import os
import sys
from datetime import datetime, timedelta
from threading import Thread
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


if sys.platform == "win32":
    import winsound
else:
    winsound = None

class WebsiteMonitor:
    def __init__(self, url, check_interval=30, timeout=10, user_email=None, sender_email=None, sender_password=None):
        self.url = url
        self.check_interval = check_interval
        self.timeout = timeout
        self.is_running = False
        self.status_history = []
        self.user_email = user_email
        self.sender_email = sender_email
        self.sender_password = sender_password

        # Create Logs directory if it doesn't exist
        self.log_dir = "Logs"
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            print(f"📁 Created '{self.log_dir}' directory for storing logs")

        # Create log file in Logs directory
        log_filename = f"monitor_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.log_file = os.path.join(self.log_dir, log_filename)
        self.last_status = None

    def send_email_notification(self, status_data):
        if not (self.user_email and self.sender_email and self.sender_password):
            print("[!] Email credentials not set. Skipping email notification.")
            return
        try:
            subject = f"[ALERT] Website DOWN: {self.url}"
            body = f"The monitored website is DOWN!\n\nURL: {self.url}\nTime: {status_data['timestamp']}\nError: {status_data['error']}\n"
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.user_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.sendmail(self.sender_email, self.user_email, msg.as_string())
            server.quit()
            print(f"📧 Email notification sent to {self.user_email}")
        except Exception as e:
            print(f"[!] Failed to send email notification: {e}")
    def check_website(self):
        """Check if website is accessible"""
        try:
            start_time = time.time()
            response = requests.get(self.url, timeout=self.timeout)
            response_time = (time.time() - start_time) * 1000
            
            return {
                'status': 'UP',
                'status_code': response.status_code,
                'response_time': round(response_time, 2),
                'timestamp': datetime.now().isoformat(),
                'error': None
            }
        except requests.exceptions.RequestException as e:
            return {
                'status': 'DOWN',
                'status_code': None,
                'response_time': None,
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def log_status(self, status_data):
        """Log status to file"""
        # Append to JSON log file
        log_entry = {
            'url': self.url,
            **status_data
        }
        
        # Read existing logs if file exists
        logs = []
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    logs = json.load(f)
            except:
                logs = []
        
        # Append new log
        logs.append(log_entry)
        
        # Write back to file
        with open(self.log_file, 'w') as f:
            json.dump(logs, f, indent=2)
    
    def send_alert(self, status_data):
        print("\n" + "="*60)
        print("🚨 ALERT: WEBSITE DOWN! 🚨")
        print(f"URL: {self.url}")
        print(f"Time: {status_data['timestamp']}")
        print(f"Error: {status_data['error']}")
        print("="*60 + "\n")
        # Play Windows alert sound if on Windows
        if winsound:
            try:
                winsound.Beep(1000, 500)
            except:
                pass  # If there is a problem, skip sound
        # Send email notification
        self.send_email_notification(status_data)
    
    def display_status(self, status_data, check_number):
        """Display current status with check number"""
        status_icon = "✅" if status_data['status'] == 'UP' else "❌"
        
        # Calculate current statistics
        up_count = sum(1 for s in self.status_history if s['status'] == 'UP')
        down_count = len(self.status_history) - up_count
        uptime = (up_count / len(self.status_history) * 100) if self.status_history else 0
        
        if status_data['status'] == 'UP':
            print(f"{status_icon} Check #{check_number} [{datetime.now().strftime('%H:%M:%S')}] "
                  f"Status: {status_data['status']} | "
                  f"Response: {status_data['response_time']}ms | "
                  f"Code: {status_data['status_code']} | "
                  f"Stats: {up_count} UP, {down_count} DOWN ({uptime:.1f}% uptime)")
        else:
            print(f"{status_icon} Check #{check_number} [{datetime.now().strftime('%H:%M:%S')}] "
                  f"Status: {status_data['status']} | "
                  f"Error: {status_data['error'][:50]}... | "
                  f"Stats: {up_count} UP, {down_count} DOWN ({uptime:.1f}% uptime)")
    
    def monitor(self, duration_minutes):
        """Main monitoring loop"""
        self.is_running = True
        self.status_history = []  # Reset history for new monitoring session
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        check_number = 0
        
        print(f"\n🔍 Starting monitor for {self.url}")
        print(f"Duration: {duration_minutes} minutes")
        print(f"Check interval: {self.check_interval} seconds")
        print(f"Log location: {self.log_file}")
        print(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 100)
        
        while self.is_running and datetime.now() < end_time:
            check_number += 1
            
            # Check website status
            status_data = self.check_website()
            
            # Add to history
            self.status_history.append(status_data)
            
            # Log the status
            self.log_status(status_data)
            
            # Display status with check number
            self.display_status(status_data, check_number)
            
            # Check if status changed from UP to DOWN
            if self.last_status == 'UP' and status_data['status'] == 'DOWN':
                self.send_alert(status_data)
            
            # Update last status
            self.last_status = status_data['status']
            
            # Calculate remaining time
            remaining = end_time - datetime.now()
            if remaining.total_seconds() > 0 and remaining.total_seconds() > self.check_interval:
                # Wait for next check
                time.sleep(self.check_interval)
            else:
                # If less time remaining than check interval, break
                break
        
        self.stop_monitoring()
    
    def stop_monitoring(self):
        """Stop monitoring and show summary"""
        self.is_running = False
        print("\n\n" + "="*60)
        print("📊 MONITORING SUMMARY")
        print("="*60)
        
        # Calculate statistics from status_history
        total_checks = len(self.status_history)
        up_count = sum(1 for s in self.status_history if s['status'] == 'UP')
        down_count = total_checks - up_count
        uptime_percentage = (up_count / total_checks * 100) if total_checks > 0 else 0
        
        # Calculate average response time for UP checks
        up_response_times = [s['response_time'] for s in self.status_history 
                           if s['status'] == 'UP' and s['response_time'] is not None]
        avg_response_time = sum(up_response_times) / len(up_response_times) if up_response_times else 0
        
        print(f"URL Monitored: {self.url}")
        print(f"Total checks: {total_checks}")
        print(f"✅ UP: {up_count} times")
        print(f"❌ DOWN: {down_count} times")
        print(f"📈 Uptime: {uptime_percentage:.2f}%")
        print(f"⚡ Average Response Time: {avg_response_time:.2f}ms")
        print(f"📁 Log file saved: {self.log_file}")
        
        # Show downtime periods if any
        if down_count > 0:
            print("\n🔴 Downtime Periods:")
            for i, status in enumerate(self.status_history):
                if status['status'] == 'DOWN':
                    print(f"   - Check #{i+1} at {status['timestamp']}: {status['error']}")
        
        print("="*60)

# Function to list all log files
def list_log_files():
    """List all log files in the Logs directory"""
    log_dir = "Logs"
    if not os.path.exists(log_dir):
        print(f"No '{log_dir}' directory found.")
        return []
    
    log_files = [f for f in os.listdir(log_dir) if f.endswith('.json')]
    
    if log_files:
        print(f"\n📁 Found {len(log_files)} log file(s) in '{log_dir}' directory:")
        for i, file in enumerate(sorted(log_files, reverse=True), 1):
            file_path = os.path.join(log_dir, file)
            file_size = os.path.getsize(file_path) / 1024  # Size in KB
            mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            print(f"   {i}. {file} ({file_size:.2f} KB) - Modified: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
        return sorted(log_files, reverse=True)
    else:
        print(f"No log files found in '{log_dir}' directory.")
        return []

# Function to analyze existing log file
def analyze_log_file(log_file):
    """Analyze an existing log file and show statistics"""
    try:
        # If only filename is provided, prepend Logs directory
        if not os.path.dirname(log_file):
            log_file = os.path.join("Logs", log_file)
            
        with open(log_file, 'r') as f:
            logs = json.load(f)
        
        if not logs:
            print("Log file is empty.")
            return
            
        total = len(logs)
        up_count = sum(1 for log in logs if log['status'] == 'UP')
        down_count = total - up_count
        uptime = (up_count / total * 100) if total > 0 else 0
        
        # Get URL and time range
        url = logs[0].get('url', 'Unknown')
        start_time = logs[0]['timestamp']
        end_time = logs[-1]['timestamp']
        
        print(f"\n📊 Log Analysis")
        print("="*50)
        print(f"Log file: {log_file}")
        print(f"URL: {url}")
        print(f"Period: {start_time} to {end_time}")
        print(f"Total pings: {total}")
        print(f"✅ UP: {up_count} times")
        print(f"❌ DOWN: {down_count} times")
        print(f"📈 Uptime: {uptime:.2f}%")
        
        # Show response time statistics
        response_times = [log['response_time'] for log in logs 
                         if log['status'] == 'UP' and log['response_time']]
        if response_times:
            print(f"\n📊 Response Time Statistics:")
            print(f"   Min: {min(response_times):.2f}ms")
            print(f"   Max: {max(response_times):.2f}ms")
            print(f"   Avg: {sum(response_times)/len(response_times):.2f}ms")
            
        # Show downtime details
        if down_count > 0:
            print(f"\n🔴 Downtime Events:")
            for i, log in enumerate(logs):
                if log['status'] == 'DOWN':
                    print(f"   - {log['timestamp']}: {log['error']}")
                    
    except FileNotFoundError:
        print(f"Error: Log file '{log_file}' not found.")
    except Exception as e:
        print(f"Error analyzing log file: {e}")

# Main execution
if __name__ == "__main__":
    print("🌐 Website Monitoring Tool")
    print("="*40)

    # Show menu
    print("\nOptions:")
    print("1. Start new monitoring session")
    print("2. Analyze existing log file")
    print("3. List all log files")

    choice = input("\nSelect option (1-3): ").strip()

    if choice == '1':
        # Get user input for monitoring
        url = input("Enter the URL to monitor: ").strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        user_email = input("Enter your email address to receive alerts: ").strip()
        sender_email = input("Enter the sender Gmail address (for sending alerts): ").strip()
        sender_password = input("Enter the sender Gmail app password: ").strip()

        try:
            duration = float(input("Enter monitoring duration (minutes): "))
            interval = int(input("Enter check interval (seconds) [default: 30]: ") or "30")
        except ValueError:
            print("Invalid input. Using defaults.")
            duration = 5
            interval = 30

        # Create monitor instance
        monitor = WebsiteMonitor(url, check_interval=interval, user_email=user_email, sender_email=sender_email, sender_password=sender_password)

        try:
            # Start monitoring
            monitor.monitor(duration)
        except KeyboardInterrupt:
            print("\n\n⚠️  Monitoring stopped by user")
            monitor.stop_monitoring()

        # Ask if user wants to analyze the log
        analyze = input("\nWould you like to analyze the log file now? (y/n): ")
        if analyze.lower() == 'y':
            analyze_log_file(monitor.log_file)

    elif choice == '2':
        # List available log files
        log_files = list_log_files()
        if log_files:
            file_num = input("\nEnter file number to analyze (or full filename): ").strip()
            try:
                # Check if user entered a number
                file_index = int(file_num) - 1
                if 0 <= file_index < len(log_files):
                    analyze_log_file(log_files[file_index])
                else:
                    print("Invalid file number.")
            except ValueError:
                # User entered filename
                analyze_log_file(file_num)

    elif choice == '3':
        list_log_files()

    else:
        print("Invalid option selected.")