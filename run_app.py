import subprocess
import threading
import time
import signal
import sys
import os

# Define paths and commands
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, 'backend')
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')
RAG_DIR = os.path.join(BASE_DIR, 'rag')

COMMANDS = [
    {
        'name': 'backend',
        'cwd': BACKEND_DIR,
        'command': [sys.executable, 'run.py'],
        'env': {**os.environ, 'PORT': '14440'},
    },
    {
        'name': 'frontend',
        'cwd': FRONTEND_DIR,
        'command': ['npm', 'run', 'dev'],
        'shell': True,  # npm requires shell=True on some systems
    },
    {
        'name': 'rag',
        'cwd': RAG_DIR,
        'command': ['uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8043', '--reload'],
    },
    {
        'name': 'mypy',
        'cwd': '.',
        'command': ['mypy', 'backend', 'rag']
    },
    {
        'name': 'pylint',
        'cwd': '.',
        'command': ['pylint', 'backend', 'rag']
    }
]

# Store processes
processes = []


def run_command(cmd_info):
    """Run a command and stream its output."""
    try:
        process = subprocess.Popen(
            cmd_info['command'],
            cwd=cmd_info['cwd'],
            env=cmd_info.get('env', os.environ),
            shell=cmd_info.get('shell', False),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        processes.append(process)
        print(f"Started {cmd_info['name']} (PID: {process.pid})")

        # Stream output
        for line in process.stdout:
            print(f"[{cmd_info['name']}] {line}", end='')

        process.wait()
        if process.returncode != 0:
            print(f"[{cmd_info['name']}] Exited with code {process.returncode}")
    except Exception as e:
        print(f"[{cmd_info['name']}] Error: {e}")


def signal_handler(sig, frame):
    """Handle termination signals."""
    print("\nStopping all services...")
    for process in processes:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
    print("All services stopped.")
    sys.exit(0)


def main():
    # Register signal handlers for clean shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start each command in a separate thread
    threads = []
    for cmd_info in COMMANDS:
        thread = threading.Thread(target=run_command, args=(cmd_info,))
        thread.daemon = True  # Threads exit when main process exits
        thread.start()
        threads.append(thread)

    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == '__main__':
    print("Starting all services...")
    main()