import subprocess
import sys
import os
from dotenv import load_dotenv

load_dotenv()

def run_command(command):
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        print(f"Error running command: {command}")
        print(stderr.decode())
        sys.exit(1)
    return stdout.decode()

def main():
    # Start Celery worker
    print("Starting Celery worker...")
    celery_process = subprocess.Popen(
        "celery -A app.worker.celery_app worker --loglevel=info",
        shell=True
    )
    
    # Start FastAPI server
    print("Starting FastAPI server...")
    fastapi_process = subprocess.Popen(
        "uvicorn app.main:app --reload --host 0.0.0.0 --port 8000",
        shell=True
    )
    
    try:
        # Keep the script running
        while True:
            pass
    except KeyboardInterrupt:
        print("\nShutting down...")
        celery_process.terminate()
        fastapi_process.terminate()

if __name__ == "__main__":
    main() 