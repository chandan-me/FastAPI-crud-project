import subprocess
import sys
import time
import os

# =====================================================================
# SYSTEM ORCHESTRATOR SCRIPT (React + Gateway + Microservices)
# This script launches all 5 components of the system concurrently.
# It captures logs to separate files and monitors startup diagnostic checks.
# =====================================================================

def free_ports(ports):
    """Kills any orphaned processes on the target ports to avoid [Errno 10048]."""
    for port in ports:
        try:
            cmd = f'powershell -Command "Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }}"'
            subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

def main():
    processes = []
    log_files = []
    try:
        print("=" * 60)
        print("STARTING MICROSERVICES WORKSPACE")
        print("=" * 60)
        
        # Proactively free any ports that may have remained open from a previous run
        print("[System] Checking and freeing ports (8011, 8012, 8013, 8010, 5173)...")
        free_ports([8011, 8012, 8013, 8010, 5173])
        time.sleep(1)

        # Open write streams for each component's log files
        user_log = open("user_service.log", "w", encoding="utf-8")
        product_log = open("product_service.log", "w", encoding="utf-8")
        order_log = open("order_service.log", "w", encoding="utf-8")
        gateway_log = open("gateway_service.log", "w", encoding="utf-8")
        frontend_log = open("frontend.log", "w", encoding="utf-8")
        
        log_files.extend([user_log, product_log, order_log, gateway_log, frontend_log])
        
        # 1. Start User Service (Port 8011)
        print("[System] Launching User Service on http://127.0.0.1:8011 ...")
        user_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "user_service.main:app", "--port", "8011", "--reload"],
            stdout=user_log,
            stderr=subprocess.STDOUT
        )
        processes.append((user_proc, "User Service", "user_service.log"))
        
        # 2. Start Product Service (Port 8012)
        print("[System] Launching Product Service on http://127.0.0.1:8012 ...")
        product_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "product_service.main:app", "--port", "8012", "--reload"],
            stdout=product_log,
            stderr=subprocess.STDOUT
        )
        processes.append((product_proc, "Product Service", "product_service.log"))

        # 3. Start Order Service (Port 8013)
        print("[System] Launching Order Service on http://127.0.0.1:8013 ...")
        order_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "order_service.main:app", "--port", "8013", "--reload"],
            stdout=order_log,
            stderr=subprocess.STDOUT
        )
        processes.append((order_proc, "Order Service", "order_service.log"))

        # 4. Start API Gateway (Port 8010)
        print("[System] Launching API Gateway on http://127.0.0.1:8010 ...")
        gateway_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "gateway_service.main:app", "--port", "8010", "--reload"],
            stdout=gateway_log,
            stderr=subprocess.STDOUT
        )
        processes.append((gateway_proc, "API Gateway", "gateway_service.log"))

        # 5. Start React Frontend (Port 5173 via Vite)
        print("[System] Launching React Frontend on http://localhost:5173 ...")
        frontend_proc = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=os.path.join(os.path.dirname(__file__), "frontend"),
            stdout=frontend_log,
            stderr=subprocess.STDOUT,
            shell=True # Required on Windows
        )
        processes.append((frontend_proc, "React Frontend", "frontend.log"))

        # Pause execution to let services initialize
        time.sleep(3)
        
        # Perform check to see if any process crashed immediately
        any_failed = False
        for proc, name, log_name in processes:
            exit_code = proc.poll()
            if exit_code is not None:
                print(f"[Error] {name} failed to start! (Exit code: {exit_code})")
                print(f"        Please check '{log_name}' for detailed error logs.")
                any_failed = True
        
        if any_failed:
            print("\n[System] One or more services failed to start. Shutting down workspace...")
            raise KeyboardInterrupt
        
        print("\n[System] All microservices and frontend started successfully!")
        print("  - React Frontend App:         http://localhost:5173")
        print("  - API Gateway API Docs:       http://127.0.0.1:8010/docs")
        print("\nPress Ctrl+C to terminate all components.")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n[System] Shutting down services...")
        # Terminate and wait for all running subprocesses to close gracefully
        for proc, name, _ in processes:
            if proc.poll() is None:
                try:
                    proc.terminate()
                    proc.wait(timeout=2)
                except Exception:
                    proc.kill()
        print("[System] All components stopped.")
    finally:
        for f in log_files:
            try:
                f.close()
            except Exception:
                pass
        free_ports([8011, 8012, 8013, 8010, 5173])

if __name__ == "__main__":
    main()
