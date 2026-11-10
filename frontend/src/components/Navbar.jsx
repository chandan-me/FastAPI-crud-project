import React, { useState, useRef, useEffect } from "react";
import { formatNumber } from "../utils/format";

/**
 * Sticky Top Navigation Bar for "Dhee Stores"
 * Features:
 * - Brand logo & "Dhee Stores" name (navigates to Products)
 * - Sticky positioning with backdrop-blur
 * - Centered search bar
 * - Dedicated navigation tabs: "Products", "My Orders", "Cart"
 * - Profile avatar with dropdown (Account Settings, Users Directory, Logout)
 */
export default function Navbar({
  user,
  activePage,
  onNavigate,
  cartCount,
  ordersCount,
  searchQuery,
  onSearchChange,
  onSearchSubmit,
  onClearSearch,
  onOpenProfile,
  onOpenUsers,
  onLogout,
}) {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const userInitial = user?.name ? user.name.charAt(0).toUpperCase() : "U";
  const isAdmin = user?.role === "admin";

  const handleBrandClick = () => {
    onClearSearch();
    onNavigate("products");
  };

  const handleFormSearch = (e) => {
    e.preventDefault();
    onNavigate("products");
    onSearchSubmit(e);
  };

  return (
    <header className="navbar-sticky">
      <div className="navbar-container">
        {/* Brand Logo & Name */}
        <div className="navbar-brand" onClick={handleBrandClick}>
          <img src="/logo.png" alt="Dhee Stores Logo" className="navbar-logo" />
          <span className="navbar-brand-name">Dhee Stores</span>
        </div>

        {/* Search Bar in Navbar */}
        <form className="navbar-search" onSubmit={handleFormSearch}>
          <div className="search-input-wrapper">
            <span className="search-icon">🔍</span>
            <input
              type="text"
              placeholder="Search products by title..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="navbar-search-input"
            />
            {searchQuery && (
              <button
                type="button"
                className="search-clear-btn"
                onClick={onClearSearch}
                title="Clear Search"
              >
                ✕
              </button>
            )}
          </div>
          <button type="submit" className="navbar-search-btn">
            Search
          </button>
        </form>

        {/* Right Navigation Actions */}
        <div className="navbar-actions">
          {/* Admin Dashboard Tab (Admin only) */}
          {isAdmin && (
            <button
              type="button"
              className={`navbar-nav-btn ${activePage === "dashboard" ? "nav-btn-active" : ""}`}
              onClick={() => onNavigate("dashboard")}
              title="Admin Sales & Analytics Dashboard"
            >
              <span className="nav-btn-icon">📊</span>
              <span className="nav-btn-text">Dashboard</span>
            </button>
          )}

          {/* Products Catalog Tab */}
          <button
            type="button"
            className={`navbar-nav-btn ${activePage === "products" ? "nav-btn-active" : ""}`}
            onClick={() => onNavigate("products")}
            title="Browse Products Catalog"
          >
            <span className="nav-btn-icon">🛍️</span>
            <span className="nav-btn-text">Products</span>
          </button>

          {/* Orders Tab */}
          <button
            type="button"
            className={`navbar-nav-btn ${activePage === "orders" ? "nav-btn-active" : ""}`}
            onClick={() => onNavigate("orders")}
            title={isAdmin ? "View All Platform Orders" : "View My Order History"}
          >
            <span className="nav-btn-icon">📦</span>
            <span className="nav-btn-text">{isAdmin ? "Platform Orders" : "My Orders"}</span>
            {ordersCount > 0 && (
              <span className="nav-badge orders-badge">{formatNumber(ordersCount)}</span>
            )}
          </button>

          {/* Shopping Cart Tab (Customers only; Admins manage catalog & dashboard) */}
          {!isAdmin && (
            <button
              type="button"
              className={`navbar-nav-btn cart-btn-highlight ${activePage === "cart" ? "nav-btn-active" : ""}`}
              onClick={() => onNavigate("cart")}
              title="View Shopping Cart"
            >
              <span className="nav-btn-icon">🛒</span>
              <span className="nav-btn-text">Cart</span>
              {cartCount > 0 && (
                <span className="nav-badge cart-badge">{formatNumber(cartCount)}</span>
              )}
            </button>
          )}

          {/* User Profile Avatar & Dropdown */}
          <div className="navbar-profile-wrapper" ref={dropdownRef}>
            <button
              type="button"
              className="navbar-avatar-btn"
              onClick={() => setIsDropdownOpen((prev) => !prev)}
              aria-label="User Profile Menu"
            >
              <span className="avatar-circle">
                {user?.profile_image ? (
                  <img
                    src={user.profile_image}
                    alt={user.name}
                    style={{ width: "100%", height: "100%", objectFit: "cover", borderRadius: "50%" }}
                    onError={(e) => {
                      e.target.style.display = "none";
                      if (e.target.nextSibling) e.target.nextSibling.style.display = "inline";
                    }}
                  />
                ) : null}
                <span style={{ display: user?.profile_image ? "none" : "inline" }}>{userInitial}</span>
              </span>
              <span className="avatar-name">{user?.name?.split(" ")[0]}</span>
              <span className="dropdown-caret">▾</span>
            </button>

            {isDropdownOpen && (
              <div className="navbar-dropdown-menu">
                {/* User Info Header */}
                <div className="dropdown-user-header">
                  <div className="dropdown-user-name">{user?.name}</div>
                  <div className="dropdown-user-email">{user?.email}</div>
                  <span className={`role-badge ${user?.role}`}>{user?.role}</span>
                </div>

                <div className="dropdown-divider" />

                {/* Sub-sections: Account */}
                <button
                  type="button"
                  className="dropdown-item"
                  onClick={() => {
                    setIsDropdownOpen(false);
                    onOpenProfile();
                  }}
                >
                  <span className="dropdown-item-icon">⚙️</span>
                  <span>Account Settings</span>
                </button>

                {/* Admin User Directory */}
                {isAdmin && (
                  <button
                    type="button"
                    className="dropdown-item"
                    onClick={() => {
                      setIsDropdownOpen(false);
                      onOpenUsers();
                    }}
                  >
                    <span className="dropdown-item-icon">👥</span>
                    <span>Users Directory</span>
                  </button>
                )}

                <div className="dropdown-divider" />

                {/* Sub-sections: Logout */}
                <button
                  type="button"
                  className="dropdown-item logout"
                  onClick={() => {
                    setIsDropdownOpen(false);
                    onLogout();
                  }}
                >
                  <span className="dropdown-item-icon">🚪</span>
                  <span>Logout</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
