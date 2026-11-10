import React, { useState } from "react";
import { formatCurrency, formatNumber } from "../utils/format";

/**
 * Dedicated Shopping Cart Page (No popups / modals)
 * Supports Cash on Delivery (COD) and Razorpay payment options.
 */
export default function CartPage({
  cartItems,
  onUpdateQuantity,
  onRemoveItem,
  onClearCart,
  onCheckout,
  isCheckingOut,
  onNavigateToProducts,
  paymentConfig,
}) {
  const [paymentMethod, setPaymentMethod] = useState("COD"); // "COD" | "RAZORPAY"

  const totalItemsCount = cartItems.reduce((acc, item) => acc + item.quantity, 0);
  const totalPrice = cartItems.reduce(
    (acc, item) => acc + item.product.price * item.quantity,
    0
  );

  return (
    <div className="cart-page-container">
      {/* Page Header */}
      <div className="page-header-row">
        <div>
          <button
            type="button"
            className="secondary sm back-link-btn"
            onClick={onNavigateToProducts}
          >
            ← Continue Shopping
          </button>
          <h2 style={{ margin: "0.5rem 0 0 0" }}>🛒 Shopping Cart</h2>
          <p style={{ margin: "0.25rem 0 0 0", color: "#64748b", fontSize: "0.9rem" }}>
            Review your selected products, choose a payment method, and proceed to checkout.
          </p>
        </div>

        {cartItems.length > 0 && (
          <button
            type="button"
            className="secondary sm"
            onClick={onClearCart}
            disabled={isCheckingOut}
          >
            Clear Cart
          </button>
        )}
      </div>

      {/* Main Content Area */}
      {cartItems.length === 0 ? (
        <div className="card empty-page-card">
          <span style={{ fontSize: "3.5rem" }}>🛍️</span>
          <h3>Your shopping cart is empty</h3>
          <p style={{ color: "#64748b", maxWidth: "400px", margin: "0 auto 1.5rem auto" }}>
            You haven't added any products to your cart yet. Explore our catalog and add items you like!
          </p>
          <button
            type="button"
            className="product-card-cart-btn"
            style={{ width: "auto", display: "inline-flex", padding: "0.75rem 1.75rem" }}
            onClick={onNavigateToProducts}
          >
            🛍️ Browse Products
          </button>
        </div>
      ) : (
        <div className="cart-page-layout">
          {/* Left Column: Cart Items List */}
          <div className="cart-items-column">
            <div className="card" style={{ padding: "1.25rem" }}>
              <div className="cart-items-list">
                {cartItems.map(({ product, quantity }) => {
                  const itemTotal = product.price * quantity;
                  return (
                    <div key={product.id} className="cart-page-item-row">
                      {/* Thumbnail */}
                      <div className="cart-page-item-thumb">
                        {product.image_url ? (
                          <img
                            src={product.image_url}
                            alt={product.name}
                            onError={(e) => { e.target.style.display = "none"; }}
                          />
                        ) : (
                          <span>📦</span>
                        )}
                      </div>

                      {/* Info */}
                      <div className="cart-page-item-info">
                        <h4 className="cart-page-item-title">{product.name}</h4>
                        <div className="cart-page-item-price">₹{formatCurrency(product.price)} each</div>
                        <div style={{ fontSize: "0.78rem", color: "#16a34a", marginTop: "0.2rem" }}>
                          In stock: {formatNumber(product.stock)}
                        </div>
                      </div>

                      {/* Inline Stepper [-] qty [+] */}
                      <div className="cart-qty-controls">
                        <button
                          type="button"
                          className="qty-btn"
                          onClick={() => onUpdateQuantity(product.id, quantity - 1)}
                          title="Reduce quantity"
                        >
                          −
                        </button>
                        <span className="qty-number">{formatNumber(quantity)}</span>
                        <button
                          type="button"
                          className="qty-btn"
                          disabled={quantity >= product.stock}
                          onClick={() => onUpdateQuantity(product.id, quantity + 1)}
                          title={quantity >= product.stock ? "Max stock reached" : "Increase quantity"}
                        >
                          +
                        </button>
                      </div>

                      {/* Total & Remove */}
                      <div className="cart-page-item-total">
                        ₹{formatCurrency(itemTotal)}
                      </div>

                      <button
                        type="button"
                        className="cart-remove-btn"
                        onClick={() => onUpdateQuantity(product.id, 0)}
                        title="Remove from cart"
                      >
                        🗑️
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Right Column: Order Summary & Checkout Card */}
          <div className="cart-summary-column">
            <div className="card cart-summary-card">
              <h3 style={{ margin: "0 0 1rem 0" }}>Order Summary</h3>

              <div className="summary-line">
                <span>Selected Items</span>
                <strong>{formatNumber(totalItemsCount)}</strong>
              </div>

              <div className="summary-line">
                <span>Estimated Taxes & Fees</span>
                <span>₹0.00</span>
              </div>

              <div className="summary-divider" />

              <div className="summary-line total-line">
                <span>Total Amount:</span>
                <span className="summary-total-price">₹{formatCurrency(totalPrice)}</span>
              </div>

              {/* Payment Method Selector */}
              <div className="payment-method-section">
                <label className="payment-method-title">💳 Payment Method</label>

                <div className="payment-options-list">
                  {/* Option 1: Cash on Delivery (COD) */}
                  <div
                    className={`payment-option-card ${paymentMethod === "COD" ? "selected" : ""}`}
                    onClick={() => setPaymentMethod("COD")}
                  >
                    <input
                      type="radio"
                      id="pay-cod"
                      name="payment_choice"
                      value="COD"
                      checked={paymentMethod === "COD"}
                      onChange={() => setPaymentMethod("COD")}
                    />
                    <div className="payment-option-body">
                      <div className="payment-option-head">
                        <span className="payment-icon">💵</span>
                        <strong className="payment-name">Cash on Delivery</strong>
                        <span className="payment-tag instant">COD</span>
                      </div>
                      <p className="payment-desc">
                        Pay in cash upon delivery directly at your doorstep.
                      </p>
                    </div>
                  </div>

                  {/* Option 2: Razorpay Online */}
                  <div
                    className={`payment-option-card ${paymentMethod === "RAZORPAY" ? "selected" : ""}`}
                    onClick={() => setPaymentMethod("RAZORPAY")}
                  >
                    <input
                      type="radio"
                      id="pay-razorpay"
                      name="payment_choice"
                      value="RAZORPAY"
                      checked={paymentMethod === "RAZORPAY"}
                      onChange={() => setPaymentMethod("RAZORPAY")}
                    />
                    <div className="payment-option-body">
                      <div className="payment-option-head">
                        <span className="payment-icon">⚡</span>
                        <strong className="payment-name">Razorpay</strong>
                        {paymentConfig?.is_configured ? (
                          <span className="payment-tag secure">Ready</span>
                        ) : (
                          <span className="payment-tag config-notice" title="Credentials loaded from .env">.env keys</span>
                        )}
                      </div>
                      <p className="payment-desc">
                        UPI (GPay / PhonePe / Paytm), Cards, Netbanking & Wallets.
                      </p>
                      {!paymentConfig?.is_configured && (
                        <div className="payment-env-hint">
                          ℹ️ Add <code>RAZORPAY_KEY_ID</code> in <code>.env</code>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Checkout Action Button */}
              <button
                type="button"
                className="cart-checkout-btn"
                style={{ width: "100%", marginTop: "1.25rem" }}
                disabled={isCheckingOut || cartItems.length === 0}
                onClick={() => onCheckout(paymentMethod)}
              >
                {isCheckingOut
                  ? "Processing Order..."
                  : paymentMethod === "COD"
                  ? `Confirm Order (Cash on Delivery) • ₹${formatCurrency(totalPrice)}`
                  : `Pay ₹${formatCurrency(totalPrice)} via Razorpay →`}
              </button>

              <div style={{ marginTop: "1rem", fontSize: "0.8rem", color: "#64748b", textAlign: "center" }}>
                🔒 Secure checkout with atomic inventory verification.
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
