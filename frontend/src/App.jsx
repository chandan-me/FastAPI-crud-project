import React, { useState, useEffect } from "react";

// API Gateway base URL
const GATEWAY_URL = "http://localhost:8010";

function App() {
  // Authentication & Session States
  const [token, setToken] = useState(localStorage.getItem("token") || "");
  const [user, setUser] = useState(null);

  // Form input States (Auth)
  const [email, setEmail] = useState("");
  const [regName, setRegName] = useState("");
  const [regEmail, setRegEmail] = useState("");
  const [regRole, setRegRole] = useState("customer");
  const [isRegisterMode, setIsRegisterMode] = useState(false);

  // Profile Management Modal State
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);
  const [profileName, setProfileName] = useState("");
  const [profileEmail, setProfileEmail] = useState("");
  const [isSavingProfile, setIsSavingProfile] = useState(false);

  // Product Catalog & Filter States
  const [products, setProducts] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [isAddProductModalOpen, setIsAddProductModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [productForm, setProductForm] = useState({ name: "", price: "", stock: "" });
  const [isSavingProduct, setIsSavingProduct] = useState(false);

  // Orders State
  const [orders, setOrders] = useState([]);
  const [selectedProductId, setSelectedProductId] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [detailedOrder, setDetailedOrder] = useState(null);
  const [isPurchasing, setIsPurchasing] = useState(false);

  // Notification States
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Admin Users Directory State
  const [usersList, setUsersList] = useState([]);
  const [isUsersModalOpen, setIsUsersModalOpen] = useState(false);
  const [isLoadingUsers, setIsLoadingUsers] = useState(false);

  const isAdmin = user?.role === "admin";

  // ---------------------------------------------------------------------
  // 1. Lifecycle Effects
  // ---------------------------------------------------------------------
  useEffect(() => {
    fetchProducts();

    const savedUser = localStorage.getItem("user");
    if (savedUser && token) {
      const parsedUser = JSON.parse(savedUser);
      setUser(parsedUser);
      setProfileName(parsedUser.name);
      setProfileEmail(parsedUser.email);
      fetchOrders(token, parsedUser);
    }
  }, []);

  // ---------------------------------------------------------------------
  // 2. REST API Fetch Calls
  // ---------------------------------------------------------------------

  // Fetch product catalog (supports query filtering)
  const fetchProducts = async (query = "") => {
    try {
      const url = query.trim()
        ? `${GATEWAY_URL}/products?q=${encodeURIComponent(query.trim())}`
        : `${GATEWAY_URL}/products`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setProducts(data);
        setSelectedProductId((prev) => {
          if (prev && data.some((p) => p.id.toString() === prev)) {
            return prev;
          }
          return data.length > 0 ? data[0].id.toString() : "";
        });
      } else {
        const data = await res.json().catch(() => ({}));
        setError(data.detail || "Failed to load products.");
      }
    } catch (err) {
      setError("Product Service is offline.");
    }
  };

  // Fetch orders history (Admins see all; Customers see their own)
  const fetchOrders = async (authToken, currentUser) => {
    try {
      const activeUser = currentUser || user;
      // If admin, retrieve all orders; if customer, scope by user_id
      const url =
        activeUser?.role === "admin"
          ? `${GATEWAY_URL}/orders`
          : `${GATEWAY_URL}/orders?user_id=${activeUser?.id || ""}`;

      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      if (res.ok) {
        const data = await res.json();
        setOrders(data);
      } else if (res.status === 401) {
        const data = await res.json().catch(() => ({}));
        handleSessionExpired(data.detail || "Access token is invalid or expired. Please log in again.");
      }
    } catch (err) {
      setError("Order Service is offline.");
    }
  };

  // Retrieve federated details for a specific order
  const fetchOrderDetails = async (orderId) => {
    setError("");
    try {
      const res = await fetch(`${GATEWAY_URL}/orders/${orderId}/details`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setDetailedOrder(data);
      } else {
        const data = await res.json().catch(() => ({}));
        if (res.status === 401) {
          handleSessionExpired(data.detail || "Access token is invalid or expired. Please log in again.");
        } else {
          setError(data.detail || "Failed to fetch detailed order information.");
        }
      }
    } catch (err) {
      setError("Connection to Order Service lost.");
    }
  };

  // Fetch all users list (Admin Only)
  const fetchUsersList = async () => {
    setIsLoadingUsers(true);
    try {
      const res = await fetch(`${GATEWAY_URL}/users`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setUsersList(data);
        setIsUsersModalOpen(true);
      } else {
        const data = await res.json().catch(() => ({}));
        setError(data.detail || "Failed to fetch users directory.");
      }
    } catch (err) {
      setError("User Service is offline.");
    } finally {
      setIsLoadingUsers(false);
    }
  };

  // ---------------------------------------------------------------------
  // 3. User & Auth Logic
  // ---------------------------------------------------------------------

  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    try {
      const res = await fetch(`${GATEWAY_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });

      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || "Login failed.");
        return;
      }

      localStorage.setItem("token", data.access_token);
      localStorage.setItem("user", JSON.stringify(data.user));

      setToken(data.access_token);
      setUser(data.user);
      setProfileName(data.user.name);
      setProfileEmail(data.user.email);
      setSuccess(`Logged in successfully as ${data.user.name} (${(data.user.role || "customer").toUpperCase()})!`);

      fetchOrders(data.access_token, data.user);
    } catch (err) {
      setError("API Gateway is offline.");
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    try {
      const res = await fetch(`${GATEWAY_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: regName, email: regEmail, role: regRole }),
      });

      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || "Registration failed.");
        return;
      }

      localStorage.setItem("token", data.access_token);
      localStorage.setItem("user", JSON.stringify(data.user));

      setToken(data.access_token);
      setUser(data.user);
      setProfileName(data.user.name);
      setProfileEmail(data.user.email);
      setSuccess(`Account registered successfully as ${data.user.name} (${(data.user.role || "customer").toUpperCase()})!`);
      setIsRegisterMode(false);
      fetchOrders(data.access_token, data.user);
    } catch (err) {
      setError("API Gateway registration failed.");
    }
  };

  const handleUpdateProfile = async (e) => {
    e.preventDefault();
    if (!user) return;
    setError("");
    setSuccess("");
    setIsSavingProfile(true);

    try {
      const res = await fetch(`${GATEWAY_URL}/users/${user.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ name: profileName, email: profileEmail }),
      });

      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || "Failed to update profile.");
        setIsSavingProfile(false);
        return;
      }

      setUser(data);
      localStorage.setItem("user", JSON.stringify(data));
      setSuccess("Profile updated successfully!");
      setIsProfileModalOpen(false);
    } catch (err) {
      setError("Failed to communicate with User Service.");
    } finally {
      setIsSavingProfile(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (!user) return;
    const confirmed = window.confirm(
      "Are you sure you want to permanently delete your account? All orders must be settled or cancelled first."
    );
    if (!confirmed) return;

    setError("");
    setSuccess("");

    try {
      const res = await fetch(`${GATEWAY_URL}/users/${user.id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(data.detail || "Failed to delete account.");
        return;
      }

      handleLogout();
      setSuccess("Your account was successfully deleted.");
    } catch (err) {
      setError("Failed to delete account.");
    }
  };

  const handleSessionExpired = (message = "Access token is invalid or expired. Please log in again.") => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    setToken("");
    setUser(null);
    setOrders([]);
    setDetailedOrder(null);
    setError(message);
    setSuccess("");
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    setToken("");
    setUser(null);
    setOrders([]);
    setDetailedOrder(null);
    setIsProfileModalOpen(false);
    setError("");
    setSuccess("Logged out successfully.");
  };

  // ---------------------------------------------------------------------
  // 4. Product CRUD Operations (ADMIN Only)
  // ---------------------------------------------------------------------

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchProducts(searchQuery);
  };

  const handleClearSearch = () => {
    setSearchQuery("");
    fetchProducts("");
  };

  const openAddProductModal = () => {
    setProductForm({ name: "", price: "", stock: "" });
    setIsAddProductModalOpen(true);
  };

  const openEditProductModal = (prod) => {
    setEditingProduct(prod);
    setProductForm({ name: prod.name, price: prod.price.toString(), stock: prod.stock.toString() });
  };

  const handleSaveProduct = async (e) => {
    e.preventDefault();
    if (!isAdmin) {
      setError("Permission denied: Admin role required to create or edit products.");
      return;
    }

    setError("");
    setSuccess("");
    setIsSavingProduct(true);

    const payload = {
      name: productForm.name.trim(),
      price: parseFloat(productForm.price),
      stock: parseInt(productForm.stock),
    };

    if (isNaN(payload.price) || payload.price <= 0) {
      setError("Product price must be greater than 0.");
      setIsSavingProduct(false);
      return;
    }
    if (isNaN(payload.stock) || payload.stock < 0) {
      setError("Product stock cannot be negative.");
      setIsSavingProduct(false);
      return;
    }

    try {
      const isEdit = !!editingProduct;
      const url = isEdit ? `${GATEWAY_URL}/products/${editingProduct.id}` : `${GATEWAY_URL}/products`;
      const method = isEdit ? "PUT" : "POST";

      const res = await fetch(url, {
        method,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || `Failed to ${isEdit ? "update" : "create"} product.`);
        setIsSavingProduct(false);
        return;
      }

      setSuccess(`Product "${data.name}" ${isEdit ? "updated" : "created"} successfully!`);
      setIsAddProductModalOpen(false);
      setEditingProduct(null);
      await fetchProducts(searchQuery);
    } catch (err) {
      setError("Product Service connection failed.");
    } finally {
      setIsSavingProduct(false);
    }
  };

  const handleDeleteProduct = async (prod) => {
    if (!isAdmin) {
      setError("Permission denied: Admin role required to delete products.");
      return;
    }

    const confirmed = window.confirm(`Are you sure you want to delete product "${prod.name}"?`);
    if (!confirmed) return;

    setError("");
    setSuccess("");

    try {
      const res = await fetch(`${GATEWAY_URL}/products/${prod.id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(data.detail || "Cannot delete product.");
        return;
      }

      setSuccess(`Product "${prod.name}" deleted successfully.`);
      await fetchProducts(searchQuery);
    } catch (err) {
      setError("Failed to delete product.");
    }
  };

  // ---------------------------------------------------------------------
  // 5. Order Operations (Purchase & Lifecycle)
  // ---------------------------------------------------------------------

  const handlePlaceOrder = async (e) => {
    e.preventDefault();
    if (isPurchasing) return;

    setError("");
    setSuccess("");
    setIsPurchasing(true);

    try {
      const res = await fetch(`${GATEWAY_URL}/orders`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          product_id: parseInt(selectedProductId),
          quantity: parseInt(quantity),
          user_id: user.id,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        if (res.status === 401) {
          handleSessionExpired(data.detail || "Access token is invalid or expired. Please log in again.");
        } else {
          setError(data.detail || "Failed to place order.");
        }
        setIsPurchasing(false);
        return;
      }

      setSuccess(`Order #${data.id} placed successfully! Total cost: ₹${data.total_price}`);
      await fetchProducts(searchQuery);
      await fetchOrders(token, user);
    } catch (err) {
      setError("Transaction gateway offline.");
    } finally {
      setIsPurchasing(false);
    }
  };

  const handleCancelOrder = async (orderId) => {
    const confirmed = window.confirm(`Are you sure you want to cancel Order #${orderId}? Stock will be restored.`);
    if (!confirmed) return;

    setError("");
    setSuccess("");

    try {
      const res = await fetch(`${GATEWAY_URL}/orders/${orderId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ status: "CANCELLED" }),
      });

      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || "Failed to cancel order.");
        return;
      }

      setSuccess(`Order #${orderId} was cancelled. Inventory restored.`);
      await fetchProducts(searchQuery);
      await fetchOrders(token, user);
      if (detailedOrder && detailedOrder.id === orderId) {
        fetchOrderDetails(orderId);
      }
    } catch (err) {
      setError("Failed to cancel order.");
    }
  };

  const handleDeleteOrder = async (orderId) => {
    const confirmed = window.confirm(`Are you sure you want to delete Order #${orderId} record permanently?`);
    if (!confirmed) return;

    setError("");
    setSuccess("");

    try {
      const res = await fetch(`${GATEWAY_URL}/orders/${orderId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(data.detail || "Failed to delete order.");
        return;
      }

      setSuccess(`Order #${orderId} deleted successfully.`);
      if (detailedOrder && detailedOrder.id === orderId) {
        setDetailedOrder(null);
      }
      await fetchProducts(searchQuery);
      await fetchOrders(token, user);
    } catch (err) {
      setError("Failed to delete order.");
    }
  };

  // ---------------------------------------------------------------------
  // 6. JSX Render View
  // ---------------------------------------------------------------------
  return (
    <div>
      {/* Top Header / User Bar */}
      <div className="user-bar">
        <h2>🛍️ Marketplace Microservices</h2>
        {user ? (
          <div className="action-btn-group">
            <span>
              Welcome, <strong>{user.name}</strong> ({user.email})
              <span className={`role-badge ${user.role || "customer"}`}>
                {(user.role || "customer").toUpperCase()}
              </span>
            </span>
            {isAdmin && (
              <button className="secondary sm" onClick={fetchUsersList} disabled={isLoadingUsers}>
                {isLoadingUsers ? "Loading..." : "👥 Users Directory"}
              </button>
            )}
            <button className="secondary sm" onClick={() => setIsProfileModalOpen(true)}>
              ⚙️ Profile
            </button>
            <button className="secondary sm" onClick={handleLogout}>
              Log Out
            </button>
          </div>
        ) : (
          <span>Please log in to browse and make purchases.</span>
        )}
      </div>

      {/* Global Alerts */}
      {error && <div className="alert-error">{error}</div>}
      {success && <div className="alert-success">{success}</div>}

      {/* Auth Screen (Login / Register Switch) */}
      {!user && (
        <div className="card" style={{ maxWidth: "450px", margin: "2rem auto" }}>
          {!isRegisterMode ? (
            <form onSubmit={handleLogin}>
              <h3>Sign In</h3>
              <div className="form-group">
                <label>Email Address</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="e.g. alice@example.com"
                  required
                />
              </div>
              <button type="submit" style={{ width: "100%" }}>
                Login
              </button>

              <div
                style={{
                  marginTop: "1.25rem",
                  padding: "0.85rem",
                  background: "#f8fafc",
                  border: "1px solid #e2e8f0",
                  borderRadius: "8px",
                  fontSize: "0.82rem",
                  lineHeight: "1.5",
                  color: "#334155",
                }}
              >
                <div style={{ fontWeight: "700", color: "#0d9488", marginBottom: "0.35rem" }}>
                  🔑 Quick Demo Accounts:
                </div>
                <div>• <strong>Admin:</strong> <code>alice@gmail.com</code> (Full Product CRUD)</div>
                <div>• <strong>Customer:</strong> <code>bob@gmail.com</code> (Purchase Only)</div>
              </div>

              <p style={{ textAlign: "center", marginTop: "1rem", fontSize: "0.85rem", color: "#64748b" }}>
                Don't have an account?{" "}
                <a href="#" onClick={() => setIsRegisterMode(true)} style={{ color: "#0d9488", fontWeight: "600" }}>
                  Register here
                </a>
              </p>
            </form>
          ) : (
            <form onSubmit={handleRegister}>
              <h3>Register New Account</h3>
              <div className="form-group">
                <label>Full Name</label>
                <input
                  type="text"
                  value={regName}
                  onChange={(e) => setRegName(e.target.value)}
                  placeholder="e.g. Alice Johnson"
                  required
                />
              </div>
              <div className="form-group">
                <label>Email Address</label>
                <input
                  type="email"
                  value={regEmail}
                  onChange={(e) => setRegEmail(e.target.value)}
                  placeholder="e.g. alice@example.com"
                  required
                />
              </div>
              <div className="form-group">
                <label>Select Role</label>
                <select value={regRole} onChange={(e) => setRegRole(e.target.value)}>
                  <option value="customer">Customer (Can Browse & Purchase Only)</option>
                  <option value="admin">Admin (Full Product CRUD & Inventory Control)</option>
                </select>
              </div>
              <button type="submit" style={{ width: "100%" }}>
                Sign Up
              </button>
              <p style={{ textAlign: "center", marginTop: "1rem", fontSize: "0.85rem", color: "#64748b" }}>
                Already registered?{" "}
                <a href="#" onClick={() => setIsRegisterMode(false)} style={{ color: "#0d9488", fontWeight: "600" }}>
                  Login here
                </a>
              </p>
            </form>
          )}
        </div>
      )}

      {/* Main Dashboard (Protected View) */}
      {user && (
        <div className="dashboard-grid">
          {/* Left Column: Product Catalog & Placement */}
          <div>
            <div className="card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
                <h3 style={{ margin: 0 }}>
                  📦 Products Inventory Catalog {isAdmin && <span className="role-badge admin">ADMIN MODE</span>}
                </h3>
                {/* Admin-only: Add Product Button */}
                {isAdmin && (
                  <button className="sm" onClick={openAddProductModal}>
                    ➕ Add New Product
                  </button>
                )}
              </div>

              {/* Product Search Bar */}
              <form onSubmit={handleSearchSubmit} className="search-container">
                <input
                  type="text"
                  placeholder="Search products by name..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{ flex: 1 }}
                />
                <button type="submit" className="sm">Search</button>
                {searchQuery && (
                  <button type="button" className="secondary sm" onClick={handleClearSearch}>
                    Clear
                  </button>
                )}
              </form>

              {products.length === 0 ? (
                <p style={{ color: "#64748b", fontSize: "0.9rem" }}>No products found.</p>
              ) : (
                <ul className="item-list">
                  {products.map((prod) => (
                    <li key={prod.id}>
                      <div>
                        <strong style={{ color: "#0f172a" }}>{prod.name}</strong>
                        <div style={{ fontSize: "0.85rem", color: "#0d9488", fontWeight: "600" }}>Unit Price: ₹{prod.price}</div>
                        <div>
                          {prod.stock > 0 ? (
                            <span style={{ color: "#16a34a", fontSize: "0.85rem", fontWeight: "600" }}>In Stock: {prod.stock}</span>
                          ) : (
                            <span style={{ color: "#dc2626", fontSize: "0.85rem", fontWeight: "600" }}>Out of Stock</span>
                          )}
                        </div>
                      </div>

                      {/* Admin-only: Edit and Delete Buttons */}
                      {isAdmin && (
                        <div className="action-btn-group">
                          <button className="secondary sm" onClick={() => openEditProductModal(prod)}>
                            ✏️ Edit
                          </button>
                          <button className="secondary-danger sm" onClick={() => handleDeleteProduct(prod)}>
                            🗑️ Delete
                          </button>
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Place Order Card (Available to Customer for Purchasing) */}
            <div className="card">
              <h3>🛒 Place a New Purchase Order</h3>
              <form onSubmit={handlePlaceOrder}>
                <div style={{ display: "flex", gap: "1rem", alignItems: "flex-end" }}>
                  <div className="form-group" style={{ flex: 2 }}>
                    <label>Select Product</label>
                    <select
                      value={selectedProductId}
                      onChange={(e) => setSelectedProductId(e.target.value)}
                    >
                      {products.map((prod) => (
                        <option key={prod.id} value={prod.id} disabled={prod.stock === 0}>
                          {prod.name} (₹{prod.price}) {prod.stock === 0 ? "- Out of stock" : ""}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group" style={{ flex: 1 }}>
                    <label>Quantity</label>
                    <input
                      type="number"
                      min="1"
                      value={quantity}
                      onChange={(e) => setQuantity(parseInt(e.target.value) || 1)}
                      required
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={
                      isPurchasing ||
                      !selectedProductId ||
                      products.find((p) => p.id === parseInt(selectedProductId))?.stock === 0
                    }
                    style={{ height: "48px", padding: "0 2rem" }}
                  >
                    {isPurchasing ? "Processing..." : "Purchase"}
                  </button>
                </div>
              </form>
            </div>
          </div>

          {/* Right Column: Order History & Details */}
          <div>
            <div className="card">
              <h3>
                📜 {isAdmin ? "All Platform Orders (Admin View)" : "My Order History (Customer View)"}
              </h3>
              {orders.length === 0 ? (
                <p style={{ color: "#64748b", fontSize: "0.9rem" }}>No orders placed yet.</p>
              ) : (
                <ul className="item-list">
                  {orders.map((ord) => {
                    const statusClass =
                      ord.status?.toLowerCase() === "cancelled"
                        ? "cancelled"
                        : ord.status?.toLowerCase() === "pending"
                        ? "pending"
                        : "completed";
                    return (
                      <li key={ord.id} style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                        <div
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                            width: "100%",
                            cursor: "pointer",
                          }}
                          onClick={() => fetchOrderDetails(ord.id)}
                        >
                          <div>
                            <strong style={{ color: "#0f172a" }}>Order #{ord.id}</strong> (User #{ord.user_id} | Product #{ord.product_id})
                            <div style={{ fontSize: "0.8rem", color: "#64748b" }}>
                              Qty: {ord.quantity} | Total: ₹{ord.total_price}
                            </div>
                          </div>
                          <span className={`status-badge ${statusClass}`}>{ord.status}</span>
                        </div>
                        <div className="action-btn-group" style={{ alignSelf: "flex-end" }}>
                          {ord.status?.toUpperCase() !== "CANCELLED" && (
                            <button
                              className="secondary sm"
                              style={{ borderColor: "#fde68a", color: "#b45309", background: "#fef3c7" }}
                              onClick={() => handleCancelOrder(ord.id)}
                            >
                              Cancel
                            </button>
                          )}
                          {isAdmin && (
                            <button
                              className="secondary-danger sm"
                              onClick={() => handleDeleteOrder(ord.id)}
                            >
                              Delete
                            </button>
                          )}
                        </div>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>

            {/* Aggregated Federated Details Card */}
            {detailedOrder && (
              <div className="card" style={{ borderColor: "#0d9488", boxShadow: "0 10px 25px -5px rgba(13, 148, 136, 0.15)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <h3 style={{ margin: 0, color: "#0f172a" }}>🔍 Order #{detailedOrder.id} Details</h3>
                  <button className="secondary sm" onClick={() => setDetailedOrder(null)}>
                    ✕ Close
                  </button>
                </div>
                <div style={{ fontSize: "0.9rem", display: "grid", gap: "0.5rem", marginTop: "1rem" }}>
                  <div>
                    <span style={{ color: "#0d9488", fontWeight: "bold" }}>Status:</span>{" "}
                    <span
                      className={`status-badge ${
                        detailedOrder.status?.toLowerCase() === "cancelled"
                          ? "cancelled"
                          : detailedOrder.status?.toLowerCase() === "pending"
                          ? "pending"
                          : "completed"
                      }`}
                    >
                      {detailedOrder.status}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: "#0d9488", fontWeight: "bold" }}>Quantity Ordered:</span>{" "}
                    {detailedOrder.quantity}
                  </div>
                  <div>
                    <span style={{ color: "#0d9488", fontWeight: "bold" }}>Total Cost:</span> ₹
                    {detailedOrder.total_price}
                  </div>

                  <hr style={{ border: "none", borderTop: "1px solid #e2e8f0", margin: "0.5rem 0" }} />

                  {/* Customer Details */}
                  {detailedOrder.user_details ? (
                    <div>
                      <strong style={{ color: "#0f172a" }}>👤 Customer Profile Details:</strong>
                      <div style={{ paddingLeft: "0.5rem", marginTop: "0.25rem", color: "#334155" }}>
                        Name: {detailedOrder.user_details.name} <br />
                        Email: {detailedOrder.user_details.email}
                      </div>
                    </div>
                  ) : (
                    <div style={{ color: "#dc2626" }}>Failed to retrieve customer profiles.</div>
                  )}

                  {/* Product Details */}
                  {detailedOrder.product_details ? (
                    <div style={{ marginTop: "0.5rem" }}>
                      <strong style={{ color: "#0f172a" }}>📦 Product Catalog Details:</strong>
                      <div style={{ paddingLeft: "0.5rem", marginTop: "0.25rem", color: "#334155" }}>
                        Product: {detailedOrder.product_details.name} <br />
                        Catalog Price: ₹{detailedOrder.product_details.price}
                      </div>
                    </div>
                  ) : (
                    <div style={{ color: "#dc2626" }}>Failed to retrieve product details.</div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* User Profile Modal (User CRUD - Edit Profile / Delete Account) */}
      {isProfileModalOpen && (
        <div className="modal-backdrop" onClick={() => setIsProfileModalOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>⚙️ Manage Account Profile</h3>
            <form onSubmit={handleUpdateProfile}>
              <div className="form-group">
                <label>User ID</label>
                <input type="text" value={user?.id || ""} disabled style={{ opacity: 0.6 }} />
              </div>
              <div className="form-group">
                <label>Assigned Role</label>
                <input type="text" value={(user?.role || "customer").toUpperCase()} disabled style={{ opacity: 0.6 }} />
              </div>
              <div className="form-group">
                <label>Full Name</label>
                <input
                  type="text"
                  value={profileName}
                  onChange={(e) => setProfileName(e.target.value)}
                  required
                />
              </div>
              <div className="form-group">
                <label>Email Address</label>
                <input
                  type="email"
                  value={profileEmail}
                  onChange={(e) => setProfileEmail(e.target.value)}
                  required
                />
              </div>
              <div className="action-btn-group" style={{ marginTop: "1.5rem", justifyContent: "space-between" }}>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <button type="submit" disabled={isSavingProfile}>
                    {isSavingProfile ? "Saving..." : "Save Changes"}
                  </button>
                  <button type="button" className="secondary" onClick={() => setIsProfileModalOpen(false)}>
                    Cancel
                  </button>
                </div>
                <button type="button" className="danger sm" onClick={handleDeleteAccount}>
                  Delete Account
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Product Modal (Product CRUD - Create - ADMIN ONLY) */}
      {isAddProductModalOpen && isAdmin && (
        <div className="modal-backdrop" onClick={() => setIsAddProductModalOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>➕ Add New Product (Admin)</h3>
            <form onSubmit={handleSaveProduct}>
              <div className="form-group">
                <label>Product Name</label>
                <input
                  type="text"
                  placeholder="e.g. Wireless Mouse"
                  value={productForm.name}
                  onChange={(e) => setProductForm({ ...productForm, name: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>Price (₹)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  placeholder="e.g. 799.00"
                  value={productForm.price}
                  onChange={(e) => setProductForm({ ...productForm, price: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>Initial Stock Quantity</label>
                <input
                  type="number"
                  min="0"
                  placeholder="e.g. 25"
                  value={productForm.stock}
                  onChange={(e) => setProductForm({ ...productForm, stock: e.target.value })}
                  required
                />
              </div>
              <div className="action-btn-group" style={{ marginTop: "1.5rem" }}>
                <button type="submit" disabled={isSavingProduct}>
                  {isSavingProduct ? "Creating..." : "Create Product"}
                </button>
                <button type="button" className="secondary" onClick={() => setIsAddProductModalOpen(false)}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Product Modal (Product CRUD - Update - ADMIN ONLY) */}
      {editingProduct && isAdmin && (
        <div className="modal-backdrop" onClick={() => setEditingProduct(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>✏️ Edit Product #{editingProduct.id} (Admin)</h3>
            <form onSubmit={handleSaveProduct}>
              <div className="form-group">
                <label>Product Name</label>
                <input
                  type="text"
                  value={productForm.name}
                  onChange={(e) => setProductForm({ ...productForm, name: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>Price (₹)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={productForm.price}
                  onChange={(e) => setProductForm({ ...productForm, price: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>Stock Quantity (Reduce / Restock)</label>
                <input
                  type="number"
                  min="0"
                  value={productForm.stock}
                  onChange={(e) => setProductForm({ ...productForm, stock: e.target.value })}
                  required
                />
              </div>
              <div className="action-btn-group" style={{ marginTop: "1.5rem" }}>
                <button type="submit" disabled={isSavingProduct}>
                  {isSavingProduct ? "Saving..." : "Save Changes"}
                </button>
                <button type="button" className="secondary" onClick={() => setEditingProduct(null)}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      {/* Admin Users Directory Modal (Shows Role Column) */}
      {isUsersModalOpen && isAdmin && (
        <div className="modal-backdrop" onClick={() => setIsUsersModalOpen(false)}>
          <div className="modal-content" style={{ maxWidth: "750px" }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ margin: 0 }}>👥 Registered Users Directory</h3>
              <button className="secondary sm" onClick={() => setIsUsersModalOpen(false)}>
                ✕ Close
              </button>
            </div>
            <p style={{ color: "#64748b", fontSize: "0.85rem", marginTop: "0.5rem" }}>
              Live accounts stored in MySQL <code>users_db.users</code> table showing assigned roles.
            </p>
            <div style={{ overflowX: "auto", maxHeight: "400px" }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Full Name</th>
                    <th>Email Address</th>
                    <th>Assigned Role</th>
                  </tr>
                </thead>
                <tbody>
                  {usersList.map((u) => (
                    <tr key={u.id}>
                      <td>#{u.id}</td>
                      <td><strong>{u.name}</strong></td>
                      <td>{u.email}</td>
                      <td>
                        <span className={`role-badge ${u.role || "customer"}`}>
                          {(u.role || "customer").toUpperCase()}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
