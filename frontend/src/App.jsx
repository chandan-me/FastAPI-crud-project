import React, { useState, useEffect } from "react";

// API Gateway base URL
const GATEWAY_URL = "http://localhost:8010";

function App() {
  // Authentication & Session States
  const [token, setToken] = useState(localStorage.getItem("token") || "");
  const [user, setUser] = useState(null);

  // Form input States
  const [email, setEmail] = useState("");
  const [regName, setRegName] = useState("");
  const [regEmail, setRegEmail] = useState("");
  const [isRegisterMode, setIsRegisterMode] = useState(false);

  // Data Catalog States
  const [products, setProducts] = useState([]);
  const [orders, setOrders] = useState([]);

  // Transaction States (Placing Order)
  const [selectedProductId, setSelectedProductId] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [detailedOrder, setDetailedOrder] = useState(null);
  const [isPurchasing, setIsPurchasing] = useState(false);

  // Alert Messaging States
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // ---------------------------------------------------------------------
  // 1. Lifecycle Effects
  // ---------------------------------------------------------------------
  useEffect(() => {
    // Always load the product list catalog immediately (it is public)
    fetchProducts();

    // If the token is stored, reload user session from localStorage
    const savedUser = localStorage.getItem("user");
    if (savedUser && token) {
      const parsedUser = JSON.parse(savedUser);
      setUser(parsedUser);
      fetchOrders(token, parsedUser.id);
    }
  }, []);

  // ---------------------------------------------------------------------
  // 2. REST API Fetch Calls
  // ---------------------------------------------------------------------

  // Fetch product list catalog (Public Route)
  const fetchProducts = async () => {
    try {
      const res = await fetch(`${GATEWAY_URL}/products`);
      if (res.ok) {
        const data = await res.json();
        setProducts(data);
        // Persist the current selectedProductId, only set default if empty or invalid
        setSelectedProductId((prev) => {
          if (prev && data.some((p) => p.id.toString() === prev)) {
            return prev;
          }
          return data.length > 0 ? data[0].id.toString() : "";
        });
      }
    } catch (err) {
      setError("Product Service is offline.");
    }
  };

  // Fetch placed orders history (Protected Route - Requires JWT & scoped to current user)
  const fetchOrders = async (authToken, currentUserId) => {
    try {
      const uid = currentUserId || user?.id;
      const url = uid ? `${GATEWAY_URL}/orders?user_id=${uid}` : `${GATEWAY_URL}/orders`;
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

  // Retrieve federated detailed info for a specific order (Protected Route)
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

  // ---------------------------------------------------------------------
  // 3. Form Handling (Auth Logic)
  // ---------------------------------------------------------------------

  // Process User Login
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

      // Store JWT token and user info inside browser storage
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("user", JSON.stringify(data.user));

      setToken(data.access_token);
      setUser(data.user);
      setSuccess(`Logged in successfully as ${data.user.name}!`);

      // Load historical orders list
      fetchOrders(data.access_token, data.user.id);
    } catch (err) {
      setError("API Gateway is offline.");
    }
  };

  // Process User Registration
  const handleRegister = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    try {
      const res = await fetch(`${GATEWAY_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: regName, email: regEmail }),
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
      setSuccess(`Account registered successfully as ${data.user.name}!`);
      setIsRegisterMode(false);
      fetchOrders(data.access_token, data.user.id);
    } catch (err) {
      setError("API Gateway registration failed.");
    }
  };

  // Clear expired/invalid session
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

  // Logout session
  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    setToken("");
    setUser(null);
    setOrders([]);
    setDetailedOrder(null);
    setError("");
    setSuccess("Logged out successfully.");
  };

  // ---------------------------------------------------------------------
  // 4. Transaction Handling (Place Order)
  // ---------------------------------------------------------------------
  const handlePlaceOrder = async (e) => {
    e.preventDefault();
    if (isPurchasing) return; // Prevent concurrent submissions

    setError("");
    setSuccess("");
    setIsPurchasing(true); // Enable loading state

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

      setSuccess(
        `Order #${data.id} placed successfully! Total cost: $${data.total_price}`,
      );

      // Await database updates before resetting the loading state
      await fetchProducts();
      await fetchOrders(token, user.id);
    } catch (err) {
      setError("Transaction gateway offline.");
    } finally {
      setIsPurchasing(false); // Reset loading state
    }
  };

  // ---------------------------------------------------------------------
  // 5. JSX Render View
  // ---------------------------------------------------------------------
  return (
    <div>
      <div className="user-bar">
        <h2>🛍️ Marketplace Demo</h2>
        {user ? (
          <div>
            <span>
              Welcome, <strong>{user.name}</strong> ({user.email}) |{" "}
            </span>
            <button className="secondary" onClick={handleLogout}>
              Log Out
            </button>
          </div>
        ) : (
          <span>Please log in to make purchases.</span>
        )}
      </div>

      {/* Messages Alerts */}
      {error && <div className="alert-error">{error}</div>}
      {success && <div className="alert-success">{success}</div>}

      {/* Auth Screen (Login / Register Switch) */}
      {!user && (
        <div
          className="card"
          style={{ maxWidth: "450px", margin: "2rem auto" }}
        >
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
              <p
                style={{
                  textAlign: "center",
                  marginTop: "1rem",
                  fontSize: "0.85rem",
                }}
              >
                Don't have an account?{" "}
                <a
                  href="#"
                  onClick={() => setIsRegisterMode(true)}
                  style={{ color: "#35a29f" }}
                >
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
              <button type="submit" style={{ width: "100%" }}>
                Sign Up
              </button>
              <p
                style={{
                  textAlign: "center",
                  marginTop: "1rem",
                  fontSize: "0.85rem",
                }}
              >
                Already registered?{" "}
                <a
                  href="#"
                  onClick={() => setIsRegisterMode(false)}
                  style={{ color: "#35a29f" }}
                >
                  Login here
                </a>
              </p>
            </form>
          )}
        </div>
      )}

      {/* Main App Grid View */}
      {user && (
        <div className="dashboard-grid">
          {/* Left Column: Products & Purchase Form */}
          <div>
            <div className="card">
              <h3>📦 Products Inventory Catalog</h3>
              <ul className="item-list">
                {products.map((prod) => (
                  <li key={prod.id}>
                    <div>
                      <strong>{prod.name}</strong>
                      <div style={{ fontSize: "0.85rem", color: "#35a29f" }}>
                        Unit Price: ₹{prod.price}
                      </div>
                    </div>
                    <div>
                      {prod.stock > 0 ? (
                        <span style={{ color: "#4cd137", fontSize: "0.85rem" }}>
                          In Stock: {prod.stock}
                        </span>
                      ) : (
                        <span style={{ color: "#ff7675", fontSize: "0.85rem" }}>
                          Out of Stock
                        </span>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </div>

            {/* Purchase Order Form */}
            <div className="card">
              <h3>🛒 Place a New Purchase Order</h3>
              <form onSubmit={handlePlaceOrder}>
                <div
                  style={{
                    display: "flex",
                    gap: "1rem",
                    alignItems: "flex-end",
                  }}
                >
                  <div className="form-group" style={{ flex: 2 }}>
                    <label>Select Product</label>
                    <select
                      value={selectedProductId}
                      onChange={(e) => setSelectedProductId(e.target.value)}
                    >
                      {products.map((prod) => (
                        <option
                          key={prod.id}
                          value={prod.id}
                          disabled={prod.stock === 0}
                        >
                          {prod.name} (₹{prod.price}){" "}
                          {prod.stock === 0 ? "- Out of stock" : ""}
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
                      onChange={(e) => setQuantity(parseInt(e.target.value))}
                      required
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={
                      isPurchasing ||
                      products.find((p) => p.id === parseInt(selectedProductId))
                        ?.stock === 0
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
              <h3>📜 Order Transaction History</h3>
              {orders.length === 0 ? (
                <p
                  style={{ color: "rgba(255,255,255,0.4)", fontSize: "0.9rem" }}
                >
                  No orders placed yet.
                </p>
              ) : (
                <ul className="item-list">
                  {orders.map((ord) => (
                    <li
                      key={ord.id}
                      style={{
                        cursor: "pointer",
                        transition: "background 0.2s",
                      }}
                      onClick={() => fetchOrderDetails(ord.id)}
                    >
                      <div>
                        <strong>Order #{ord.id}</strong>
                        <div style={{ fontSize: "0.8rem", opacity: 0.6 }}>
                          Total: ${ord.total_price}
                        </div>
                      </div>
                      <span className="status-badge completed">
                        {ord.status}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Federated Detailed Order View */}
            {detailedOrder && (
              <div className="card" style={{ borderColor: "#35a29f" }}>
                <h3>🔍 Aggregated Order #{detailedOrder.id} Details</h3>
                <div
                  style={{ fontSize: "0.9rem", display: "grid", gap: "0.5rem" }}
                >
                  <div>
                    <span style={{ color: "#35a29f", fontWeight: "bold" }}>
                      Status:
                    </span>{" "}
                    <span className="status-badge completed">
                      {detailedOrder.status}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: "#35a29f", fontWeight: "bold" }}>
                      Quantity Ordered:
                    </span>{" "}
                    {detailedOrder.quantity}
                  </div>
                  <div>
                    <span style={{ color: "#35a29f", fontWeight: "bold" }}>
                      Total Cost:
                    </span>{" "}
                    ${detailedOrder.total_price}
                  </div>

                  <hr
                    style={{
                      border: "none",
                      borderTop: "1px solid rgba(255,255,255,0.1)",
                      margin: "0.5rem 0",
                    }}
                  />

                  {/* Federated User Details */}
                  {detailedOrder.user_details ? (
                    <div>
                      <strong style={{ color: "#ffffff" }}>
                        👤 Customer Profile Details:
                      </strong>
                      <div
                        style={{ paddingLeft: "0.5rem", marginTop: "0.25rem" }}
                      >
                        Name: {detailedOrder.user_details.name} <br />
                        Email: {detailedOrder.user_details.email}
                      </div>
                    </div>
                  ) : (
                    <div style={{ color: "#ff7675" }}>
                      Failed to retrieve customer profiles.
                    </div>
                  )}

                  {/* Federated Product Details */}
                  {detailedOrder.product_details ? (
                    <div style={{ marginTop: "0.5rem" }}>
                      <strong style={{ color: "#ffffff" }}>
                        📦 Product Catalog Details:
                      </strong>
                      <div
                        style={{ paddingLeft: "0.5rem", marginTop: "0.25rem" }}
                      >
                        Product: {detailedOrder.product_details.name} <br />
                        Catalog Price: ${detailedOrder.product_details.price}
                      </div>
                    </div>
                  ) : (
                    <div style={{ color: "#ff7675" }}>
                      Failed to retrieve product details.
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
