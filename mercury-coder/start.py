#!/usr/bin/env python3
"""
Mercury Coder Startup Script
Starts backend and frontend, checking for existing processes first.
"""

import os
import sys
import time
import signal
import subprocess
import socket
from pathlib import Path

# Colors for terminal output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

def print_colored(message, color=Colors.NC):
    """Print colored message."""
    print(f"{color}{message}{Colors.NC}")

def check_port(port):
    """Check if a port is in use."""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result == 0

def kill_port(port, service_name):
    """Kill process using a specific port."""
    if not check_port(port):
        print_colored(f"✓ Port {port} is free", Colors.GREEN)
        return True
    
    print_colored(f"⚠️  {service_name} is already running on port {port}", Colors.YELLOW)
    print_colored(f"   Killing existing process...", Colors.YELLOW)
    
    try:
        if sys.platform == "win32":
            # Windows
            result = subprocess.run(
                ['netstat', '-ano'], 
                capture_output=True, 
                text=True
            )
            for line in result.stdout.split('\n'):
                if f':{port}' in line and 'LISTENING' in line:
                    parts = line.split()
                    if len(parts) > 4:
                        pid = parts[-1]
                        subprocess.run(['taskkill', '/F', '/PID', pid], 
                                     capture_output=True)
        else:
            # Linux/Mac
            result = subprocess.run(
                ['lsof', '-ti', f':{port}'], 
                capture_output=True, 
                text=True
            )
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid:
                        try:
                            os.kill(int(pid), signal.SIGTERM)
                        except:
                            pass
                        time.sleep(0.5)
                        try:
                            os.kill(int(pid), signal.SIGKILL)
                        except:
                            pass
        
        time.sleep(2)
        
        if check_port(port):
            print_colored(f"✗ Failed to kill process on port {port}", Colors.RED)
            return False
        else:
            print_colored(f"✓ Killed existing {service_name} process", Colors.GREEN)
            return True
    except Exception as e:
        print_colored(f"✗ Error killing process: {e}", Colors.RED)
        return False

def wait_for_backend(max_attempts=30):
    """Wait for backend to be ready."""
    print_colored("⏳ Waiting for backend to be ready...", Colors.BLUE)
    
    for attempt in range(max_attempts):
        # Check if port is open and responding
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', 8000))
        sock.close()
        
        if result == 0:
            # Port is open, try to get health endpoint
            try:
                import urllib.request
                req = urllib.request.Request('http://127.0.0.1:8000/health')
                with urllib.request.urlopen(req, timeout=2) as response:
                    if response.getcode() == 200:
                        print_colored("✓ Backend is ready!", Colors.GREEN)
                        return True
            except:
                pass
        
        print(".", end="", flush=True)
        time.sleep(1)
    
    print()
    print_colored(f"✗ Backend failed to start within {max_attempts} seconds", Colors.RED)
    return False

def cleanup(backend_process, frontend_process, electron_process=None):
    """Cleanup function."""
    print()
    print_colored("🛑 Shutting down...", Colors.YELLOW)
    
    # Kill backend
    if backend_process:
        try:
            backend_process.terminate()
            backend_process.wait(timeout=5)
        except:
            backend_process.kill()
    
    # Kill frontend
    if frontend_process:
        try:
            frontend_process.terminate()
            frontend_process.wait(timeout=5)
        except:
            frontend_process.kill()
    
    # Kill Electron
    if electron_process:
        try:
            electron_process.terminate()
            electron_process.wait(timeout=5)
        except:
            electron_process.kill()
    
    # Kill any remaining Electron processes
    if sys.platform == "win32":
        subprocess.run(['taskkill', '/F', '/IM', 'electron.exe'], 
                      capture_output=True)
    else:
        subprocess.run(['pkill', '-f', 'electron'], 
                      capture_output=True)
    
    # Ensure ports are free
    kill_port(4096, "OpenCode Backend")
    kill_port(5173, "Frontend")
    
    print_colored("✓ All processes stopped", Colors.GREEN)

def main():
    """Main function."""
    print_colored("=" * 40, Colors.BLUE)
    print_colored("  Mercury Coder Startup Script", Colors.BLUE)
    print_colored("=" * 40, Colors.BLUE)
    print()
    
    # Get script directory
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)
    
    backend_process = None
    frontend_process = None
    electron_process = None
    
    def signal_handler(sig, frame):
        cleanup(backend_process, frontend_process, electron_process)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Step 1: Check and kill existing processes
    print_colored("Step 1: Checking existing processes...", Colors.BLUE)
    print()
    
    kill_port(4096, "OpenCode Backend")
    kill_port(5173, "Frontend (Vite dev server)")
    
    print()
    print_colored("Step 2: Starting OpenCode backend...", Colors.BLUE)
    print()
    
    # Check if bun is available
    try:
        subprocess.run(["bun", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_colored("✗ Error: bun not found", Colors.RED)
        print_colored("   Please install bun: curl -fsSL https://bun.sh/install | bash", Colors.YELLOW)
        sys.exit(1)
    
    # Check if opencode-backend exists
    opencode_backend_dir = script_dir.parent / "opencode-backend"
    opencode_packages_dir = opencode_backend_dir / "packages" / "opencode"
    if not opencode_packages_dir.exists():
        print_colored("✗ Error: opencode-backend/packages/opencode not found", Colors.RED)
        print_colored("   Please ensure opencode-backend is properly checked out", Colors.YELLOW)
        sys.exit(1)
    
    # Install dependencies if needed
    if not (opencode_backend_dir / "node_modules").exists():
        print_colored("Installing OpenCode backend dependencies...", Colors.BLUE)
        subprocess.run(["bun", "install"], cwd=opencode_backend_dir, check=True)
    
    # Start OpenCode backend
    backend_log = script_dir / "opencode-backend.log"
    
    try:
        # Start OpenCode backend using bun
        print_colored("✓ Starting OpenCode backend server on port 4096...", Colors.GREEN)
        
        with open(backend_log, 'w') as log_file:
            backend_process = subprocess.Popen(
                [
                    "bun", "run",
                    "--cwd", str(opencode_packages_dir),
                    "--conditions=browser",
                    "src/index.ts",
                    "serve",
                    "--port", "4096",
                    "--hostname", "127.0.0.1",
                    "--print-logs",
                    "--log-level", "DEBUG"
                ],
                cwd=opencode_backend_dir,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                env={**os.environ, "NODE_ENV": "development"}
            )
        print_colored(f"✓ OpenCode backend process started (PID: {backend_process.pid})", Colors.GREEN)
    except Exception as e:
        print_colored(f"✗ Failed to start OpenCode backend: {e}", Colors.RED)
        sys.exit(1)
    
    # Wait for OpenCode backend to be ready
    print_colored("⏳ Waiting for OpenCode backend to be ready...", Colors.BLUE)
    for attempt in range(30):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', 4096))
        sock.close()
        
        if result == 0:
            # Port is open, try to get config endpoint
            try:
                import urllib.request
                req = urllib.request.Request('http://127.0.0.1:4096/config')
                with urllib.request.urlopen(req, timeout=2) as response:
                    if response.getcode() == 200:
                        print_colored("✓ OpenCode backend is ready!", Colors.GREEN)
                        break
            except:
                pass
        
        print(".", end="", flush=True)
        time.sleep(1)
    else:
        print()
        print_colored("✗ OpenCode backend failed to start", Colors.RED)
        print_colored("   Check opencode-backend.log for details", Colors.YELLOW)
        if backend_process:
            backend_process.kill()
        sys.exit(1)
    print()
    
    print()
    print_colored("Step 3: Starting frontend (Vite)...", Colors.BLUE)
    print()
    
    # Start frontend (Vite dev server)
    frontend_log = script_dir / "frontend.log"
    electron_process = None
    
    try:
        with open(frontend_log, 'w') as log_file:
            frontend_process = subprocess.Popen(
                ["npm", "run", "dev:vite"],
                cwd=script_dir,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True
            )
        print_colored(f"✓ Frontend (Vite) process started (PID: {frontend_process.pid})", Colors.GREEN)
    except Exception as e:
        print_colored(f"✗ Failed to start frontend: {e}", Colors.RED)
        cleanup(backend_process, None, None)
        sys.exit(1)
    
    # Wait for Vite to be ready (both port open and HTTP response)
    print_colored("⏳ Waiting for Vite dev server to be ready...", Colors.BLUE)
    for attempt in range(30):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', 5173))
        sock.close()
        if result == 0:
            # Port is open, try to get HTTP response
            try:
                import urllib.request
                req = urllib.request.Request('http://localhost:5173')
                with urllib.request.urlopen(req, timeout=2) as response:
                    if response.getcode() == 200:
                        print_colored("✓ Vite dev server is ready!", Colors.GREEN)
                        time.sleep(2)  # Give it a moment to fully initialize
                        break
            except:
                pass
        
        time.sleep(1)
        print(".", end="", flush=True)
    else:
        print()
        print_colored("⚠️  Vite may not be ready, but continuing...", Colors.YELLOW)
    
    print()
    print_colored("Step 4: Starting Electron desktop app...", Colors.BLUE)
    print()
    
    # Start Electron
    electron_log = script_dir / "electron.log"
    
    try:
        env = os.environ.copy()
        env['NODE_ENV'] = 'development'
        with open(electron_log, 'w') as log_file:
            electron_process = subprocess.Popen(
                ["npm", "run", "dev:electron"],
                cwd=script_dir,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                env=env
            )
        print_colored(f"✓ Electron process started (PID: {electron_process.pid})", Colors.GREEN)
    except Exception as e:
        print_colored(f"✗ Failed to start Electron: {e}", Colors.RED)
        print_colored("   Frontend is still running at http://localhost:5173", Colors.YELLOW)
        electron_process = None
    
    time.sleep(2)
    
    print()
    print_colored("=" * 40, Colors.GREEN)
    print_colored("  ✓ All services are running!", Colors.GREEN)
    print_colored("=" * 40, Colors.GREEN)
    print()
    print_colored("OpenCode Backend: http://127.0.0.1:4096", Colors.BLUE)
    print_colored("Frontend:         http://localhost:5173", Colors.BLUE)
    if electron_process:
        print_colored("Electron:         Desktop app window should be open", Colors.BLUE)
    print()
    print_colored("Press Ctrl+C to stop all services", Colors.YELLOW)
    print()
    
    # Wait for processes
    try:
        while True:
            if backend_process and backend_process.poll() is not None:
                print_colored("Backend process died unexpectedly", Colors.RED)
                break
            if frontend_process and frontend_process.poll() is not None:
                print_colored("Frontend process died unexpectedly", Colors.RED)
                break
            if electron_process and electron_process.poll() is not None:
                print_colored("Electron process died unexpectedly", Colors.RED)
                break
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    
    cleanup(backend_process, frontend_process, electron_process)

if __name__ == "__main__":
    main()

