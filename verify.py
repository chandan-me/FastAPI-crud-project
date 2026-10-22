import httpx
import sys
import time

# =====================================================================
# INTEGRATION TESTING & GATEWAY VERIFICATION SCRIPT
# This script sends HTTP requests to the API Gateway (Port 8000) to 
# verify the unified router proxying, JWT authentication checks, and
# end-to-end integration mapping.
# =====================================================================

GATEWAY_URL = "http://127.0.0.1:8010"

def print_result(test_name, success, message=""):
    """Prints a styled test output log to the console."""
    status = "SUCCESS" if success else "FAILED"
    color = "\033[92m" if success else "\033[91m"
    reset = "\033[0m"
    print(f"[{color}{status}{reset}] {test_name} {message}")

async def run_tests():
    print("=" * 60)
    print("RUNNING END-TO-END GATEWAY & AUTH VERIFICATION")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        # -------------------------------------------------------------
        # 1. Assert JWT Gatekeeper Blocks Unauthorized requests
        # -------------------------------------------------------------
        try:
            # Attempt to fetch orders without providing a JWT token
            res = await client.get(f"{GATEWAY_URL}/orders")
            if res.status_code in (401, 403): # API Gateway blocks it
                print_result("Gateway Security: Block Unauthorized Request", True, f"(Orders list blocked successfully, got {res.status_code})")
            else:
                print_result("Gateway Security: Block Unauthorized Request", False, f"Expected 401 or 403, got {res.status_code}")
        except Exception as e:
            print_result("Gateway Security: Block Unauthorized Request", False, f"Exception: {e}")

        # -------------------------------------------------------------
        # 2. Perform Login via Gateway auth and obtain JWT Token
        # -------------------------------------------------------------
        token = ""
        user_id = None
        try:
            payload = {"email": "alice@example.com"}
            res = await client.post(f"{GATEWAY_URL}/auth/login", json=payload)
            if res.status_code == 200:
                data = res.json()
                token = data["access_token"]
                user_id = data["user"]["id"]
                print_result("Gateway Authentication: Login Alice", True, f"(Received JWT Token: {token[:20]}...)")
            else:
                print_result("Gateway Authentication: Login Alice", False, f"Status: {res.status_code}, Body: {res.json()}")
        except Exception as e:
            print_result("Gateway Authentication: Login Alice", False, f"Exception: {e}")

        # -------------------------------------------------------------
        # 3. Retrieve Public Products list via Gateway (Unprotected)
        # -------------------------------------------------------------
        stock_before = 0
        try:
            res = await client.get(f"{GATEWAY_URL}/products")
            if res.status_code == 200:
                products = res.json()
                mouse = next((p for p in products if p["id"] == 1), None)
                if mouse:
                    print_result("Gateway Routing: Fetch Public Products", True, f"(Mouse Stock: {mouse['stock']})")
                    stock_before = mouse["stock"]
                else:
                    print_result("Gateway Routing: Fetch Public Products", False, "Mouse product not found in catalog")
            else:
                print_result("Gateway Routing: Fetch Public Products", False, f"Status: {res.status_code}")
        except Exception as e:
            print_result("Gateway Routing: Fetch Public Products", False, f"Exception: {e}")

        # -------------------------------------------------------------
        # 4. Place Order via Gateway (Protected - Injecting JWT Token)
        # -------------------------------------------------------------
        if not token:
            print_result("Gateway Routing: Place Order (JWT)", False, "Skipped: login failed.")
            return

        order_id = None
        try:
            # Place order (Alice buys 1 Wireless Mouse)
            headers = {"Authorization": f"Bearer {token}"}
            payload = {"product_id": 1, "quantity": 1, "user_id": user_id}
            res = await client.post(f"{GATEWAY_URL}/orders", json=payload, headers=headers)
            if res.status_code == 201:
                order = res.json()
                order_id = order["id"]
                print_result("Gateway Routing: Place Order (JWT)", True, f"Order ID: {order_id}, Total: ₹{order['total_price']}")
            else:
                print_result("Gateway Routing: Place Order (JWT)", False, f"Status: {res.status_code}, Body: {res.text}")
        except Exception as e:
            print_result("Gateway Routing: Place Order (JWT)", False, f"Exception: {e}")

        # -------------------------------------------------------------
        # 5. Verify stock decreased by checking Products list again
        # -------------------------------------------------------------
        try:
            res = await client.get(f"{GATEWAY_URL}/products")
            if res.status_code == 200:
                products = res.json()
                mouse = next((p for p in products if p["id"] == 1), None)
                reduced_correctly = (stock_before - mouse["stock"] == 1)
                print_result("Inventory Check: Stock Decremented", reduced_correctly, f"Stock: {stock_before} -> {mouse['stock']}")
            else:
                print_result("Inventory Check: Stock Decremented", False, f"Status: {res.status_code}")
        except Exception as e:
            print_result("Inventory Check: Stock Decremented", False, f"Exception: {e}")

        # -------------------------------------------------------------
        # 6. Retrieve Detailed Aggregated Order Details via Gateway
        # -------------------------------------------------------------
        if not order_id:
            print_result("Gateway Routing: Retrieve Federated Order Details", False, "Skipped: order placement failed.")
            return

        try:
            headers = {"Authorization": f"Bearer {token}"}
            res = await client.get(f"{GATEWAY_URL}/orders/{order_id}/details", headers=headers)
            if res.status_code == 200:
                data = res.json()
                has_details = "user_details" in data and "product_details" in data
                print_result("Gateway Routing: Retrieve Federated Order Details", has_details,
                             f"\n  Customer Name: {data.get('user_details', {}).get('name')}\n  Product Bought: {data.get('product_details', {}).get('name')}")
            else:
                print_result("Gateway Routing: Retrieve Federated Order Details", False, f"Status: {res.status_code}")
        except Exception as e:
            print_result("Gateway Routing: Retrieve Federated Order Details", False, f"Exception: {e}")

    print("=" * 60)

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_tests())
