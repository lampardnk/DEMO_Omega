import socket
import subprocess
import platform
from app import app

def get_local_ip():
    """Get the local IP address of this machine"""
    try:
        # Method 1: Connect to a remote address to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # Connect to Google's DNS server (doesn't actually send data)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            return local_ip
    except Exception:
        pass
    
    try:
        # Method 2: Use platform-specific commands
        system = platform.system().lower()
        
        if system == "darwin":  # macOS
            result = subprocess.run(['ifconfig'], capture_output=True, text=True)
            lines = result.stdout.split('\n')
            for line in lines:
                if 'inet ' in line and '127.0.0.1' not in line and 'inet 169.254' not in line:
                    ip = line.split('inet ')[1].split(' ')[0]
                    if ip.startswith('192.168.') or ip.startswith('10.') or ip.startswith('172.'):
                        return ip
        
        elif system == "windows":
            result = subprocess.run(['ipconfig'], capture_output=True, text=True)
            lines = result.stdout.split('\n')
            for line in lines:
                if 'IPv4 Address' in line:
                    ip = line.split(':')[1].strip()
                    if ip.startswith('192.168.') or ip.startswith('10.') or ip.startswith('172.'):
                        return ip
        
        elif system == "linux":
            result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
            ips = result.stdout.strip().split()
            for ip in ips:
                if ip.startswith('192.168.') or ip.startswith('10.') or ip.startswith('172.'):
                    return ip
    
    except Exception:
        pass
    
    # Fallback: return localhost
    return "127.0.0.1"

def display_network_info(port=8081):
    """Display network access information"""
    local_ip = get_local_ip()
    
    print("=" * 60)
    print("🚀 OMEGA QUESTIONBANK & QUIZ APP")
    print("=" * 60)
    print(f"✅ Server starting on port {port}")
    print()
    print("📱 ACCESS LINKS:")
    print(f"   Local (this computer): http://127.0.0.1:{port}")
    print(f"   Network (share this):  http://{local_ip}:{port}")
    print()
    print("🌐 SHARE WITH OTHERS:")
    print(f"   Send this link to users on your network:")
    print(f"   👉 http://{local_ip}:{port}")
    print()
    print("📋 FEATURES AVAILABLE:")
    print("   • Dashboard - Student performance analytics")
    print("   • Courses - Class management")
    print("   • Questionbank - Create and manage questions")
    print("   • Quiz Engine - Create and take quizzes")
    print()
    print("⚠️  NETWORK REQUIREMENTS:")
    print("   • All devices must be on the same WiFi/network")
    print("   • Firewall may need to allow incoming connections")
    print("   • Keep this terminal window open while others use the app")
    print()
    print("🛑 TO STOP: Press Ctrl+C")
    print("=" * 60)
    print()

if __name__ == '__main__':
    port = 8081
    
    # Display network information before starting
    display_network_info(port)
    
    try:
        # Start the Flask app
        app.run(debug=True, host='0.0.0.0', port=port)
    except KeyboardInterrupt:
        print("\n")
        print("=" * 60)
        print("🛑 Server stopped by user")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        print("Try running with a different port or check if port 8081 is already in use.") 