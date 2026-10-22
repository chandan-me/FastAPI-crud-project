import threading
import time
import httpx
import socket
import uuid

# =====================================================================
# SERVICE DISCOVERY CLIENT MODULE
# 
# This module runs inside each individual microservice. It is responsible for:
#   1. Automatic registration with the Discovery Server (Port 8761) on startup.
#   2. Sending periodic heartbeats (renew lease) in a background thread.
#   3. Clean deregistration on server shutdown.
# =====================================================================

DISCOVERY_URL = "http://localhost:8762/eureka/apps"

class DiscoveryClient:
    def __init__(self, app_name: str, port: int):
        self.app_name = app_name.upper()
        self.port = port
        self.host = "127.0.0.1" # Run locally
        # Generate a unique instance ID combining hostname, service type, and UUID
        self.instance_id = f"{socket.gethostname()}:{self.app_name}:{self.port}:{uuid.uuid4().hex[:6]}"
        self.heartbeat_thread = None
        self.stop_event = threading.Event()

    def register(self) -> bool:
        """Sends service registration payload to the Discovery Registry."""
        payload = {
            "instance_id": self.instance_id,
            "host": self.host,
            "port": self.port,
            "status": "UP"
        }
        try:
            with httpx.Client() as client:
                res = client.post(f"{DISCOVERY_URL}/{self.app_name}", json=payload)
                if res.status_code == 201:
                    print(f"[{self.app_name}] Successfully registered with Discovery Server (ID: {self.instance_id})")
                    return True
                print(f"[{self.app_name}] Registration failed with status: {res.status_code}")
        except Exception as e:
            print(f"[{self.app_name}] Cannot connect to Discovery Server: {e}")
        return False

    def heartbeat_loop(self):
        """Background loop that sends a renewal ping every 10 seconds."""
        while not self.stop_event.is_set():
            try:
                with httpx.Client() as client:
                    res = client.put(f"{DISCOVERY_URL}/{self.app_name}/{self.instance_id}")
                    if res.status_code != 200:
                        print(f"[{self.app_name}] Heartbeat failed, re-registering...")
                        self.register()
            except Exception:
                # Silently ignore connection issues during temporary restarts
                pass
            time.sleep(10)

    def start(self):
        """Starts registration and spins up the heartbeat daemon thread."""
        if self.register():
            self.stop_event.clear()
            self.heartbeat_thread = threading.Thread(target=self.heartbeat_loop, daemon=True)
            self.heartbeat_thread.start()

    def stop(self):
        """Stops the heartbeat loop and deregisters from the Discovery Registry."""
        print(f"[{self.app_name}] Stopping heartbeat and deregistering...")
        self.stop_event.set()
        try:
            with httpx.Client() as client:
                client.delete(f"{DISCOVERY_URL}/{self.app_name}/{self.instance_id}", timeout=2.0)
        except Exception as e:
            print(f"[{self.app_name}] Failed to deregister cleanly: {e}")
