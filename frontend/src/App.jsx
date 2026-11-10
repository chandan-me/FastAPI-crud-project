import React, { useState, useEffect } from "react";
import Navbar from "./components/Navbar";
import ProductCard from "./components/ProductCard";
import CartPage from "./components/CartPage";
import OrdersPage from "./components/OrdersPage";
import ProductModal from "./components/ProductModal";
import ProfileModal from "./components/ProfileModal";
import UsersModal from "./components/UsersModal";
import AdminDashboard from "./components/AdminDashboard";
import AuthScreen from "./components/AuthScreen";

import * as api from "./services/api";
import { formatNumber } from "./utils/format";

/**
 * Main Application Component - Dhee Stores
 * Coordinates global state, authentication, full-page navigation,
 * in-card product steppers, and distributed microservices operations.
 */
export default function App() {
  // Navigation State: "products" | "cart" | "orders"
  const [currentPage, setCurrentPage] = useState("products");

  // Session States
  const [token, setToken] = useState(localStorage.getItem("token") || "");
  const [user, setUser] = useState(null);

  // Product Catalog States
  const [products, setProducts] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [isProductModalOpen, setIsProductModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [isSavingProduct, setIsSavingProduct] = useState(false);

  // Shopping Cart State: [{ product, quantity }]
  const [cartItems, setCartItems] = useState([]);
  const [isCheckingOut, setIsCheckingOut] = useState(false);
  const [paymentConfig, setPaymentConfig] = useState(null);

  // Orders State
  const [orders, setOrders] = useState([]);

  // Profile & Admin Modals
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [usersList, setUsersList] = useState([]);
  const [isUsersModalOpen, setIsUsersModalOpen] = useState(false);
  const [isLoadingUsers, setIsLoadingUsers] = useState(false);

  // Global Alerts
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const isAdmin = user?.role === "admin";

  // ---------------------------------------------------------------------------
  // Lifecycle Effects
  // ---------------------------------------------------------------------------
  useEffect(() => {
    fetchProducts();
    fetchPaymentConfig();

    // Register automatic session expiration interceptor
    api.setSessionExpiredHandler(() => {
      handleSessionExpired();
    });

    const savedUser = localStorage.getItem("user");
    if (savedUser && token) {
      try {
        const parsed = JSON.parse(savedUser);
        setUser(parsed);
        fetchOrders(token, parsed);
        if (parsed.role === "admin") {
          setCurrentPage("dashboard");
          fetchUsersList(token);
        }
      } catch (err) {
        handleLogout();
      }
    }
  }, []);

  const fetchUsersList = async (authToken) => {
    try {
      const data = await api.getAllUsers(authToken || token);
      setUsersList(data);
    } catch (err) {
      // ignore
    }
  };

  const fetchPaymentConfig = async () => {
    try {
      const cfg = await api.getPaymentConfig();
      setPaymentConfig(cfg);
    } catch (err) {
      // ignore
    }
  };

  // ---------------------------------------------------------------------------
  // API Fetchers
  // ---------------------------------------------------------------------------
  const fetchProducts = async (query = "") => {
    try {
      const data = await api.getProducts(query);
      setProducts(data);
    } catch (err) {
      setError(err.message || "Failed to load products.");
    }
  };

  const fetchOrders = async (authToken, currentUser) => {
    try {
      const activeUser = currentUser || user;
      const data = await api.getOrders(authToken, activeUser);
      setOrders(data);
    } catch (err) {
      // Don't override main error if logged out
    }
  };

  // ---------------------------------------------------------------------------
  // Search Handlers (Located in Sticky Navbar)
  // ---------------------------------------------------------------------------
  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setCurrentPage("products");
    fetchProducts(searchQuery);
  };

  const handleClearSearch = () => {
    setSearchQuery("");
    fetchProducts("");
  };

  // ---------------------------------------------------------------------------
  // Authentication Handlers
  // ---------------------------------------------------------------------------
  const handleSessionExpired = () => {
    setToken("");
    setUser(null);
    setOrders([]);
    setCartItems([]);
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    setError("Your session has expired. Please sign in with your email and password.");
  };

  const handleLogin = async (email, password) => {
    setError("");
    setSuccess("");
    try {
      const data = await api.loginUser(email, password);
      setToken(data.access_token);
      setUser(data.user);
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("user", JSON.stringify(data.user));
      setSuccess(`Welcome back, ${data.user.name}!`);
      if (data.user.role === "admin") {
        setCurrentPage("dashboard");
        fetchUsersList(data.access_token);
      } else {
        setCurrentPage("products");
      }
      fetchOrders(data.access_token, data.user);
    } catch (err) {
      setError(err.message || "Invalid email or password.");
    }
  };

  const handleRegister = async (payload) => {
    setError("");
    setSuccess("");
    try {
      const data = await api.registerUser(payload);
      if (data && data.access_token) {
        setToken(data.access_token);
        setUser(data.user);
        localStorage.setItem("token", data.access_token);
        localStorage.setItem("user", JSON.stringify(data.user));
        setSuccess(`Welcome to Dhee Stores, ${data.user.name}!`);
        if (data.user.role === "admin") {
          setCurrentPage("dashboard");
          fetchUsersList(data.access_token);
        } else {
          setCurrentPage("products");
        }
        fetchOrders(data.access_token, data.user);
      } else {
        setSuccess("Account registered successfully! Logging you in...");
        await handleLogin(payload.email, payload.password);
      }
    } catch (err) {
      setError(err.message || "Registration failed.");
    }
  };

  const handleLogout = () => {
    setToken("");
    setUser(null);
    setOrders([]);
    setCartItems([]);
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    setCurrentPage("products");
    setError("");
    setSuccess("Logged out successfully.");
  };

  // ---------------------------------------------------------------------------
  // In-Card & Cart Quantity Management
  // ---------------------------------------------------------------------------

  // First-time "Add Product" click from card (Customer only)
  const handleAddToCart = (product) => {
    if (isAdmin) {
      setError("Administrator accounts manage catalog and dashboard; customer accounts place purchases.");
      return;
    }
    if (product.stock <= 0) return;

    setCartItems((prev) => {
      const existing = prev.find((item) => item.product.id === product.id);
      if (existing) {
        if (existing.quantity >= product.stock) {
          setError(`Cannot add more "${product.name}". Max stock reached.`);
          return prev;
        }
        return prev.map((item) =>
          item.product.id === product.id
            ? { ...item, quantity: item.quantity + 1 }
            : item
        );
      }
      return [...prev, { product, quantity: 1 }];
    });

    setSuccess(`Added "${product.name}" to cart.`);
  };

  // Stepper quantity update [-] qty [+] (Customer only)
  const handleUpdateQuantity = (productId, newQuantity) => {
    if (isAdmin) return;
    if (newQuantity <= 0) {
      setCartItems((prev) => prev.filter((item) => item.product.id !== productId));
      return;
    }

    setCartItems((prev) => {
      const existing = prev.find((item) => item.product.id === productId);
      if (existing) {
        if (newQuantity > existing.product.stock) {
          setError(`Cannot exceed available stock of ${existing.product.stock}.`);
          return prev;
        }
        return prev.map((item) =>
          item.product.id === productId ? { ...item, quantity: newQuantity } : item
        );
      } else {
        const prod = products.find((p) => p.id === productId);
        if (prod) {
          return [...prev, { product: prod, quantity: newQuantity }];
        }
        return prev;
      }
    });
  };

  const handleClearCart = () => {
    setCartItems([]);
  };

  // Multi-Item Checkout with COD or Razorpay
  const handleCheckout = async (paymentMethod = "COD") => {
    if (cartItems.length === 0 || isCheckingOut) return;
    setIsCheckingOut(true);
    setError("");
    setSuccess("");

    const totalAmount = cartItems.reduce(
      (acc, item) => acc + item.product.price * item.quantity,
      0
    );

    // -------------------------------------------------------------------------
    // Option 1: Cash on Delivery (COD) Flow
    // -------------------------------------------------------------------------
    if (paymentMethod === "COD") {
      try {
        const payload = {
          items: cartItems.map((i) => ({
            product_id: i.product.id,
            quantity: i.quantity,
          })),
          payment_method: "COD",
        };

        const placedOrders = await api.checkoutCart(payload, token);
        setSuccess(
          `Order confirmed with Cash on Delivery! ${placedOrders.length} item(s) placed successfully.`
        );
        setCartItems([]);
        await fetchOrders(token, user);
        await fetchProducts(searchQuery);
        setCurrentPage("orders");
      } catch (err) {
        setError(err.message || "Cash on Delivery checkout failed.");
      } finally {
        setIsCheckingOut(false);
      }
      return;
    }

    // -------------------------------------------------------------------------
    // Option 2: Razorpay Online Payment Flow
    // -------------------------------------------------------------------------
    if (paymentMethod === "RAZORPAY") {
      try {
        // Dynamically verify if keys are configured in backend .env
        const cfg = await api.getPaymentConfig();
        setPaymentConfig(cfg);

        if (!cfg || !cfg.is_configured || !cfg.razorpay_key_id) {
          setError(
            "Razorpay credentials are not yet configured in your .env file. Please add RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET to .env, or select Cash on Delivery (COD) to complete your order."
          );
          setIsCheckingOut(false);
          return;
        }

        // 1. Create official Razorpay Order via backend
        const rzpOrder = await api.createRazorpayOrder(totalAmount, token);

        // 2. Open standard Razorpay Checkout Modal
        if (!window.Razorpay) {
          throw new Error("Razorpay checkout SDK is not loaded. Please verify your connection.");
        }

        const options = {
          key: rzpOrder.key_id,
          amount: rzpOrder.amount,
          currency: rzpOrder.currency || "INR",
          name: "Dhee Stores",
          description: `Checkout for ${cartItems.length} item(s)`,
          image: "/logo.png",
          order_id: rzpOrder.razorpay_order_id,
          handler: async function (response) {
            try {
              setIsCheckingOut(true);
              const verifyPayload = {
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature,
                items: cartItems.map((i) => ({
                  product_id: i.product.id,
                  quantity: i.quantity,
                })),
              };

              const confirmed = await api.verifyRazorpayPayment(verifyPayload, token);
              setSuccess(
                `Payment verified! Order #${confirmed.map((o) => o.id).join(", #")} confirmed via Razorpay (Payment ID: ${response.razorpay_payment_id}).`
              );
              setCartItems([]);
              await fetchOrders(token, user);
              await fetchProducts(searchQuery);
              setCurrentPage("orders");
            } catch (vErr) {
              setError(vErr.message || "Payment verification failed.");
            } finally {
              setIsCheckingOut(false);
            }
          },
          prefill: {
            name: user?.name || "Customer",
            email: user?.email || "customer@example.com",
          },
          theme: {
            color: "#ea580c",
          },
          modal: {
            ondismiss: function () {
              setIsCheckingOut(false);
            },
          },
        };

        const rzpInstance = new window.Razorpay(options);
        rzpInstance.on("payment.failed", function (resp) {
          setIsCheckingOut(false);
          setError(`Razorpay Payment Failed: ${resp.error?.description || "Transaction declined"}`);
        });
        rzpInstance.open();
      } catch (err) {
        setIsCheckingOut(false);
        setError(err.message || "Failed to initiate Razorpay checkout.");
      }
    }
  };

  // ---------------------------------------------------------------------------
  // Orders Management Handlers (Cancel function removed)
  // ---------------------------------------------------------------------------
  const handleDeleteOrderRecord = async (orderIds) => {
    if (!isAdmin) return;
    const ids = Array.isArray(orderIds) ? orderIds : [orderIds];
    const confirmed = window.confirm(`Permanently delete Order #${ids.join(", #")} record(s)?`);
    if (!confirmed) return;

    try {
      for (const id of ids) {
        await api.deleteOrder(id, token);
      }
      setSuccess(`Order #${ids.join(", #")} record(s) deleted.`);
      fetchOrders(token, user);
      fetchProducts(searchQuery);
    } catch (err) {
      setError(err.message || "Failed to delete order.");
    }
  };

  // ---------------------------------------------------------------------------
  // Product CRUD Handlers (Admin)
  // ---------------------------------------------------------------------------
  const openAddProductModal = () => {
    setEditingProduct(null);
    setIsProductModalOpen(true);
  };

  const openEditProductModal = (prod) => {
    setEditingProduct(prod);
    setIsProductModalOpen(true);
  };

  const handleSaveProduct = async (payload) => {
    if (!isAdmin) return;
    setIsSavingProduct(true);
    setError("");
    setSuccess("");

    try {
      const isEdit = !!editingProduct;
      if (isEdit) {
        await api.updateProduct(editingProduct.id, payload, token);
        setSuccess(`Product "${payload.name}" updated successfully!`);
      } else {
        await api.createProduct(payload, token);
        setSuccess(`Product "${payload.name}" created successfully!`);
      }
      setIsProductModalOpen(false);
      setEditingProduct(null);
      await fetchProducts(searchQuery);
    } catch (err) {
      setError(err.message || "Failed to save product.");
    } finally {
      setIsSavingProduct(false);
    }
  };

  const handleToggleBlockProduct = async (prod) => {
    if (!isAdmin) return;
    const action = prod.is_blocked ? "unblock" : "block";
    const confirmed = window.confirm(`Are you sure you want to ${action} product "${prod.name}"?`);
    if (!confirmed) return;

    try {
      await api.toggleBlockProduct(prod.id, token);
      setSuccess(`Product "${prod.name}" ${action}ed successfully.`);
      await fetchProducts(searchQuery);
    } catch (err) {
      setError(err.message || `Failed to ${action} product.`);
    }
  };

  // ---------------------------------------------------------------------------
  // Profile & User Directory Handlers
  // ---------------------------------------------------------------------------
  const handleSaveProfile = async (payload) => {
    setIsSavingProfile(true);
    setError("");
    setSuccess("");

    try {
      const updated = await api.updateProfile(user.id, payload, token);
      setUser(updated);
      localStorage.setItem("user", JSON.stringify(updated));
      setSuccess("Profile updated successfully!");
      setIsProfileModalOpen(false);
    } catch (err) {
      setError(err.message || "Failed to update profile.");
    } finally {
      setIsSavingProfile(false);
    }
  };

  const handleOpenUsersDirectory = async () => {
    setIsUsersModalOpen(true);
    setIsLoadingUsers(true);
    try {
      const data = await api.getAllUsers(token);
      setUsersList(data);
    } catch (err) {
      setError(err.message || "Failed to load users directory.");
    } finally {
      setIsLoadingUsers(false);
    }
  };

  const handleToggleBlockUser = async (u) => {
    if (!isAdmin) return;
    if (u.id === user.id) {
      setError("You cannot block your own administrator account.");
      return;
    }
    const action = u.is_blocked ? "unblock" : "block";
    const confirmed = window.confirm(`Are you sure you want to ${action} user "${u.name}" (${u.email})?`);
    if (!confirmed) return;

    try {
      await api.toggleBlockUser(u.id, token);
      setSuccess(`User "${u.name}" ${action}ed successfully.`);
      const data = await api.getAllUsers(token);
      setUsersList(data);
    } catch (err) {
      setError(err.message || `Failed to ${action} user.`);
    }
  };

  // Total items currently in cart
  const totalCartCount = cartItems.reduce((acc, item) => acc + item.quantity, 0);

  // ---------------------------------------------------------------------------
  // Render Application
  // ---------------------------------------------------------------------------
  return (
    <div className="app-layout">
      {/* Sticky Top Navigation Bar with active page tab indicators */}
      {user && (
        <Navbar
          user={user}
          activePage={currentPage}
          onNavigate={setCurrentPage}
          cartCount={totalCartCount}
          ordersCount={orders.length}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          onSearchSubmit={handleSearchSubmit}
          onClearSearch={handleClearSearch}
          onOpenProfile={() => setIsProfileModalOpen(true)}
          onOpenUsers={handleOpenUsersDirectory}
          onLogout={handleLogout}
        />
      )}

      {/* Main Content Area */}
      <main className="main-content-container">
        {/* Global Notifications for Logged-In User Pages */}
        {user && error && (
          <div className="alert-error" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span>⚠️ {error}</span>
            <button
              type="button"
              className="alert-dismiss-btn"
              onClick={() => setError("")}
              title="Dismiss error"
            >
              ✕
            </button>
          </div>
        )}
        {user && success && (
          <div className="alert-success" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span>✅ {success}</span>
            <button
              type="button"
              className="alert-dismiss-btn"
              onClick={() => setSuccess("")}
              title="Dismiss notification"
            >
              ✕
            </button>
          </div>
        )}

        {/* Auth Screen (When Logged Out) */}
        {!user ? (
          <AuthScreen
            onLogin={handleLogin}
            onRegister={handleRegister}
            error={error}
            success={success}
            onClearMessages={() => {
              setError("");
              setSuccess("");
            }}
          />
        ) : currentPage === "dashboard" && isAdmin ? (
          /* Dedicated Admin Sales & Business Analytics Dashboard */
          <AdminDashboard
            orders={orders}
            products={products}
            usersList={usersList}
            onOpenAddProduct={openAddProductModal}
            onOpenUsers={handleOpenUsersDirectory}
            onNavigateToCatalog={() => setCurrentPage("products")}
          />
        ) : currentPage === "cart" && !isAdmin ? (
          /* Dedicated Shopping Cart Page (Customers only; Admins oversee dashboard) */
          <CartPage
            cartItems={cartItems}
            onUpdateQuantity={handleUpdateQuantity}
            onRemoveItem={(prodId) => handleUpdateQuantity(prodId, 0)}
            onClearCart={handleClearCart}
            onCheckout={handleCheckout}
            isCheckingOut={isCheckingOut}
            onNavigateToProducts={() => setCurrentPage("products")}
            paymentConfig={paymentConfig}
          />
        ) : currentPage === "orders" ? (
          /* Dedicated Platform Orders / Customer Orders Page */
          <OrdersPage
            orders={orders}
            products={products}
            isAdmin={isAdmin}
            onNavigateToProducts={() => setCurrentPage("products")}
            onDeleteOrderRecord={handleDeleteOrderRecord}
          />
        ) : (
          /* Dedicated Product Catalog Page */
          <div>
            {/* Catalog Header Bar */}
            <div className="catalog-header-bar">
              <div>
                <h2 style={{ margin: 0 }}>🛍️ Product Catalog</h2>
                <p style={{ margin: "0.25rem 0 0 0", color: "#64748b", fontSize: "0.9rem" }}>
                  {isAdmin
                    ? "Manage platform items, edit prices, update inventory stocks, and monitor catalog."
                    : "Add products directly from the cards with live quantity steppers."}
                </p>
              </div>

              <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
                {isAdmin && (
                  <>
                    <button type="button" className="sm" onClick={openAddProductModal}>
                      ➕ Add Product
                    </button>
                    <button
                      type="button"
                      className="secondary sm"
                      onClick={() => setCurrentPage("dashboard")}
                    >
                      📊 View Dashboard
                    </button>
                  </>
                )}
                {!isAdmin && totalCartCount > 0 && (
                  <button
                    type="button"
                    className="cart-checkout-btn sm"
                    onClick={() => setCurrentPage("cart")}
                  >
                    View Cart ({formatNumber(totalCartCount)}) →
                  </button>
                )}
              </div>
            </div>

            {/* Product Card Grid */}
            {products.length === 0 ? (
              <div className="card" style={{ textAlign: "center", padding: "3rem" }}>
                <span style={{ fontSize: "3rem" }}>📦</span>
                <h3>No products found</h3>
                <p style={{ color: "#64748b" }}>
                  {searchQuery ? `No results for "${searchQuery}".` : "The catalog is currently empty."}
                </p>
                {searchQuery && (
                  <button type="button" className="secondary sm" onClick={handleClearSearch}>
                    Clear Search
                  </button>
                )}
              </div>
            ) : (
              <div className="product-card-grid">
                {products.map((prod) => {
                  const cartItem = cartItems.find((i) => i.product.id === prod.id);
                  return (
                    <ProductCard
                      key={prod.id}
                      product={prod}
                      isAdmin={isAdmin}
                      onAddToCart={handleAddToCart}
                      onUpdateQuantity={handleUpdateQuantity}
                      cartQuantity={cartItem?.quantity || 0}
                      onEdit={openEditProductModal}
                      onToggleBlock={handleToggleBlockProduct}
                    />
                  );
                })}
              </div>
            )}
          </div>
        )}
      </main>

      {/* Admin / Account Modals */}
      <ProductModal
        isOpen={isProductModalOpen}
        onClose={() => setIsProductModalOpen(false)}
        editingProduct={editingProduct}
        onSave={handleSaveProduct}
        isSaving={isSavingProduct}
      />

      <ProfileModal
        isOpen={isProfileModalOpen}
        onClose={() => setIsProfileModalOpen(false)}
        currentUser={user}
        onSave={handleSaveProfile}
        isSaving={isSavingProfile}
      />

      <UsersModal
        isOpen={isUsersModalOpen}
        onClose={() => setIsUsersModalOpen(false)}
        usersList={usersList}
        isLoading={isLoadingUsers}
        onToggleBlockUser={handleToggleBlockUser}
      />
    </div>
  );
}
