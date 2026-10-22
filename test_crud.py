import asyncio
import httpx
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

GATEWAY_URL = "http://127.0.0.1:8010"

def print_result(test_name, success, message=""):
    status = "SUCCESS" if success else "FAILED"
    color = "\033[92m" if success else "\033[91m"
    reset = "\033[0m"
    print(f"[{color}{status}{reset}] {test_name} - {message}")

async def run_crud_tests():
    print("=" * 75)
    print("COMPREHENSIVE RBAC (ADMIN vs CUSTOMER) & CRUD AUTOMATED TEST SUITE")
    print("=" * 75)

    results = []

    async with httpx.AsyncClient(timeout=10.0) as client:
        # -------------------------------------------------------------
        # 1. SETUP: ADMIN & CUSTOMER ACCOUNTS
        # -------------------------------------------------------------
        print("\n--- [1] Setting Up Admin & Customer Sessions ---")

        # 1.1 Register or Login Admin User
        admin_email = f"admin_{int(asyncio.get_event_loop().time() * 1000)}@example.com"
        res_admin = await client.post(f"{GATEWAY_URL}/auth/register", json={
            "name": "Super Admin",
            "email": admin_email,
            "role": "admin"
        })
        admin_ok = res_admin.status_code in (200, 201)
        results.append(admin_ok)
        admin_token = res_admin.json().get("access_token") if admin_ok else None
        admin_id = res_admin.json().get("user", {}).get("id") if admin_ok else None
        admin_header = {"Authorization": f"Bearer {admin_token}"} if admin_token else {}
        print_result("1.1 Register Admin User", admin_ok, f"Admin ID: {admin_id}, Role: {res_admin.json().get('user',{}).get('role')}")

        # 1.2 Register Customer User
        customer_email = f"customer_{int(asyncio.get_event_loop().time() * 1000)}@example.com"
        res_cust = await client.post(f"{GATEWAY_URL}/auth/register", json={
            "name": "Regular Customer",
            "email": customer_email,
            "role": "customer"
        })
        cust_ok = res_cust.status_code in (200, 201)
        results.append(cust_ok)
        cust_token = res_cust.json().get("access_token") if cust_ok else None
        cust_id = res_cust.json().get("user", {}).get("id") if cust_ok else None
        cust_header = {"Authorization": f"Bearer {cust_token}"} if cust_token else {}
        print_result("1.2 Register Customer User", cust_ok, f"Customer ID: {cust_id}, Role: {res_cust.json().get('user',{}).get('role')}")

        # -------------------------------------------------------------
        # 2. RBAC PRODUCT CRUD PERMISSION TESTS
        # -------------------------------------------------------------
        print("\n--- [2] Testing RBAC on Product Management ---")

        # 2.1 Customer CANNOT Add Product (Must be blocked with 403)
        res = await client.post(f"{GATEWAY_URL}/products", json={"name": "Hacked Product", "price": 10.0, "stock": 5}, headers=cust_header)
        cust_blocked = (res.status_code == 403)
        results.append(cust_blocked)
        print_result("2.1 Customer Blocked from Adding Product", cust_blocked, f"Expected 403, got {res.status_code}")

        # 2.2 Admin CAN Add Product
        prod_payload = {
            "name": f"Admin Gadget {int(asyncio.get_event_loop().time() * 1000) % 10000}",
            "price": 1299.00,
            "stock": 30
        }
        res = await client.post(f"{GATEWAY_URL}/products", json=prod_payload, headers=admin_header)
        admin_prod_created = (res.status_code == 201)
        results.append(admin_prod_created)
        created_prod = res.json() if admin_prod_created else {}
        prod_id = created_prod.get("id")
        print_result("2.2 Admin Adds Product", admin_prod_created, f"Product #{prod_id} (₹{prod_payload['price']})")

        # 2.3 Customer CANNOT Edit Product (Blocked with 403)
        if prod_id:
            res = await client.put(f"{GATEWAY_URL}/products/{prod_id}", json={"name": "Altered by Customer"}, headers=cust_header)
            cust_edit_blocked = (res.status_code == 403)
            results.append(cust_edit_blocked)
            print_result("2.3 Customer Blocked from Editing Product", cust_edit_blocked, f"Expected 403, got {res.status_code}")

        # 2.4 Admin CAN Edit Product (Update details, restock / reduce)
        if prod_id:
            res = await client.put(f"{GATEWAY_URL}/products/{prod_id}", json={"name": f"{prod_payload['name']} (Deluxe)", "price": 1499.00, "stock": 40}, headers=admin_header)
            admin_edit_ok = (res.status_code == 200 and res.json().get("stock") == 40)
            results.append(admin_edit_ok)
            print_result("2.4 Admin Edits Product & Restocks", admin_edit_ok, f"New Price: ₹{res.json().get('price')}, Stock: {res.json().get('stock')}")

        # 2.5 Customer CANNOT Delete Product (Blocked with 403)
        if prod_id:
            res = await client.delete(f"{GATEWAY_URL}/products/{prod_id}", headers=cust_header)
            cust_del_blocked = (res.status_code == 403)
            results.append(cust_del_blocked)
            print_result("2.5 Customer Blocked from Deleting Product", cust_del_blocked, f"Expected 403, got {res.status_code}")

        # -------------------------------------------------------------
        # 3. CUSTOMER PURCHASING & ORDER ISOLATION
        # -------------------------------------------------------------
        print("\n--- [3] Testing Customer Purchase & Order Scoping ---")

        # 3.1 Customer CAN Purchase Product (POST /orders)
        order_id = None
        if prod_id and cust_id:
            res = await client.post(
                f"{GATEWAY_URL}/orders",
                json={"product_id": prod_id, "quantity": 2, "user_id": cust_id},
                headers=cust_header
            )
            purchase_ok = (res.status_code == 201)
            results.append(purchase_ok)
            order_data = res.json() if purchase_ok else {}
            order_id = order_data.get("id")
            print_result("3.1 Customer Places Purchase Order", purchase_ok, f"Order #{order_id}, Cost: ₹{order_data.get('total_price')}")

        # 3.2 Verify Stock Reduced
        if prod_id:
            res = await client.get(f"{GATEWAY_URL}/products/{prod_id}")
            stock_ok = (res.status_code == 200 and res.json().get("stock") == 38) # 40 - 2
            results.append(stock_ok)
            print_result("3.2 Stock Automatically Deducted", stock_ok, f"Stock: 40 -> {res.json().get('stock')}")

        # 3.3 Customer Only Sees Their Own Orders
        res = await client.get(f"{GATEWAY_URL}/orders", headers=cust_header)
        cust_orders = res.json() if res.status_code == 200 else []
        all_own = all(o["user_id"] == cust_id for o in cust_orders)
        results.append(all_own and len(cust_orders) >= 1)
        print_result("3.3 Customer Scoped Orders View", all_own, f"Customer orders count: {len(cust_orders)} (all belong to customer)")

        # 3.4 Admin Can See All Orders Across Platform
        res = await client.get(f"{GATEWAY_URL}/orders", headers=admin_header)
        admin_orders = res.json() if res.status_code == 200 else []
        admin_sees_all = (res.status_code == 200 and len(admin_orders) >= len(cust_orders))
        results.append(admin_sees_all)
        print_result("3.4 Admin Sees All Platform Orders", admin_sees_all, f"Total platform orders visible: {len(admin_orders)}")

        # -------------------------------------------------------------
        # 4. ORDER CANCELLATION & SAFE DELETION BY ADMIN
        # -------------------------------------------------------------
        print("\n--- [4] Testing Cancellation & Cleanup by Admin ---")

        # 4.1 Cancel Order (Restores Stock)
        if order_id:
            res = await client.put(f"{GATEWAY_URL}/orders/{order_id}", json={"status": "CANCELLED"}, headers=admin_header)
            cancel_ok = (res.status_code == 200 and res.json().get("status") == "CANCELLED")
            results.append(cancel_ok)
            print_result("4.1 Cancel Order", cancel_ok, f"Order status updated to CANCELLED")

            # Verify stock was restored
            res_p = await client.get(f"{GATEWAY_URL}/products/{prod_id}")
            restored_ok = (res_p.status_code == 200 and res_p.json().get("stock") == 40)
            results.append(restored_ok)
            print_result("4.1b Inventory Restored on Cancellation", restored_ok, f"Stock restored to: {res_p.json().get('stock')}")

        # 4.2 Delete Order
        if order_id:
            res = await client.delete(f"{GATEWAY_URL}/orders/{order_id}", headers=admin_header)
            del_order_ok = (res.status_code == 200)
            results.append(del_order_ok)
            print_result("4.2 Delete Order", del_order_ok, f"Order #{order_id} deleted")

        # 4.3 Admin CAN Delete Product (Once order is removed)
        if prod_id:
            res = await client.delete(f"{GATEWAY_URL}/products/{prod_id}", headers=admin_header)
            del_prod_ok = (res.status_code == 200)
            results.append(del_prod_ok)
            print_result("4.3 Admin Deletes Product", del_prod_ok, f"Product #{prod_id} deleted successfully")

        # 4.4 Clean up Customer and Admin test accounts
        if cust_id:
            res = await client.delete(f"{GATEWAY_URL}/users/{cust_id}", headers=admin_header)
            results.append(res.status_code == 200)
            print_result("4.4 Clean up Customer User", res.status_code == 200, f"Customer #{cust_id} removed")

        if admin_id:
            res = await client.delete(f"{GATEWAY_URL}/users/{admin_id}", headers=admin_header)
            results.append(res.status_code == 200)
            print_result("4.5 Clean up Admin User", res.status_code == 200, f"Admin #{admin_id} removed")

    print("\n" + "=" * 75)
    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"RBAC & CRUD TEST SUMMARY: {passed}/{total} Passed ({(passed/total)*100:.1f}%)")
    print("=" * 75)
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(run_crud_tests())
    sys.exit(0 if success else 1)
