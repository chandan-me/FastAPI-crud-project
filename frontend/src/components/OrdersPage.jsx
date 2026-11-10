import React, { useMemo } from "react";
import { formatCurrency, formatNumber } from "../utils/format";

/**
 * Dedicated "My Orders" / "Platform Orders" Page
 * Automatically bundles all items purchased in the same checkout session
 * into ONE clean, unified Order Card with itemized product breakdowns.
 */
export default function OrdersPage({
  orders = [],
  products = [],
  isAdmin,
  onNavigateToProducts,
  onDeleteOrderRecord,
}) {
  // Group orders by checkout session (order_group_id / payment_id / individual order)
  const groupedOrders = useMemo(() => {
    const groups = new Map();

    orders.forEach((order) => {
      // Grouping key: order_group_id -> payment_id -> individual order ID
      const groupKey =
        order.order_group_id ||
        (order.payment_id && order.payment_id.trim() ? order.payment_id.trim() : null) ||
        `ORD-${order.id}`;

      if (!groups.has(groupKey)) {
        groups.set(groupKey, {
          groupKey,
          userId: order.user_id,
          status: order.status || "COMPLETED",
          paymentMethod: order.payment_method || "COD",
          paymentId: order.payment_id || null,
          items: [],
          totalAmount: 0,
          totalQuantity: 0,
          orderIds: [],
        });
      }

      const grp = groups.get(groupKey);
      grp.items.push(order);
      grp.totalAmount += Number(order.total_price || 0);
      grp.totalQuantity += Number(order.quantity || 1);
      grp.orderIds.push(order.id);
    });

    return Array.from(groups.values());
  }, [orders]);

  return (
    <div className="orders-page-container">
      {/* Page Header */}
      <div className="page-header-row">
        <div>
          <button
            type="button"
            className="secondary sm back-link-btn"
            onClick={onNavigateToProducts}
          >
            ← Back to Products
          </button>
          <h2 style={{ margin: "0.5rem 0 0 0" }}>
            {isAdmin ? "📦 Platform Orders Directory" : "📦 My Orders"}
          </h2>
          <p style={{ margin: "0.25rem 0 0 0", color: "#64748b", fontSize: "0.9rem" }}>
            {isAdmin
              ? "All customer transactions recorded across the distributed microservices."
              : "Review your purchase history, fulfillment status, and order details."}
          </p>
        </div>
      </div>

      {/* Main Content Area */}
      {groupedOrders.length === 0 ? (
        <div className="card empty-page-card">
          <span style={{ fontSize: "3.5rem" }}>📭</span>
          <h3>No orders found</h3>
          <p style={{ color: "#64748b", maxWidth: "400px", margin: "0 auto 1.5rem auto" }}>
            You haven't placed any orders yet. Discover items in our store and complete a purchase!
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
        <div className="orders-page-list">
          {groupedOrders.map((group) => {
            const hasMultipleItems = group.items.length > 1;
            const minId = Math.min(...group.orderIds);
            const maxId = Math.max(...group.orderIds);
            const orderTitle = hasMultipleItems ? `Order #${minId} - #${maxId}` : `Order #${group.orderIds[0]}`;

            return (
              <div key={group.groupKey} className="card order-bundle-card">
                {/* 1. Order Card Header */}
                <div className="order-bundle-header">
                  <div className="order-bundle-header-left">
                    <span className="order-id-badge">{orderTitle}</span>
                    {hasMultipleItems && (
                      <span className="order-bundle-badge">
                        🛍️ {group.items.length} Items in Order
                      </span>
                    )}
                    {isAdmin && (
                      <span className="order-customer-tag">
                        Customer ID: #{group.userId}
                      </span>
                    )}
                  </div>

                  <div className="order-bundle-header-right">
                    <span className={`status-badge ${group.status.toLowerCase()}`}>
                      {group.status}
                    </span>
                    {(group.paymentMethod || "").toUpperCase() === "RAZORPAY" ? (
                      <span className="order-payment-pill razorpay">
                        ⚡ Razorpay {group.paymentId ? `(#${group.paymentId.slice(-8)})` : ""}
                      </span>
                    ) : (
                      <span className="order-payment-pill cod">
                        💵 Cash on Delivery (COD)
                      </span>
                    )}
                  </div>
                </div>

                {/* 2. Order Itemized Products List */}
                <div className="order-bundle-items-list">
                  {group.items.map((item) => {
                    const prod = products.find((p) => p.id === item.product_id);
                    const prodName = prod ? prod.name : `Product #${item.product_id}`;
                    const prodImage = prod?.image_url;
                    const unitPrice = Number(item.total_price) / item.quantity;

                    return (
                      <div key={item.id} className="order-bundle-item-row">
                        {/* Thumbnail */}
                        <div className="order-item-thumb">
                          {prodImage ? (
                            <img
                              src={prodImage}
                              alt={prodName}
                              onError={(e) => {
                                e.target.style.display = "none";
                                if (e.target.nextSibling) {
                                  e.target.nextSibling.style.display = "flex";
                                }
                              }}
                            />
                          ) : null}
                          <span
                            className="order-thumb-placeholder"
                            style={{ display: prodImage ? "none" : "flex", fontSize: "1.4rem" }}
                          >
                            📦
                          </span>
                        </div>

                        {/* Title & Product Info */}
                        <div className="order-item-info">
                          <h4 className="order-item-title">{prodName}</h4>
                          <div className="order-item-meta">
                            <span>Product ID: #{item.product_id}</span>
                            <span className="meta-dot">•</span>
                            <span>Unit Price: ₹{formatCurrency(unitPrice)}</span>
                          </div>
                        </div>

                        {/* Quantity */}
                        <div className="order-item-qty">
                          <span className="qty-pill">
                            {formatNumber(item.quantity)} unit{item.quantity > 1 ? "s" : ""}
                          </span>
                        </div>

                        {/* Line Subtotal */}
                        <div className="order-item-subtotal">
                          ₹{formatCurrency(item.total_price)}
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* 3. Order Card Footer & Totals */}
                <div className="order-bundle-footer">
                  <div className="order-bundle-footer-left">
                    <span className="order-fulfillment-badge">
                      ✅ {group.status === "COMPLETED" ? "Completed & Verified" : group.status}
                    </span>
                    <span className="order-total-units-text">
                      Total: <strong>{group.items.length} item{group.items.length > 1 ? "s" : ""}</strong> ({formatNumber(group.totalQuantity)} units)
                    </span>
                  </div>

                  <div className="order-bundle-footer-right">
                    <div className="order-grand-total">
                      <span className="total-label">Total Amount Paid:</span>
                      <span className="total-amount-val">
                        ₹{formatCurrency(group.totalAmount)}
                      </span>
                    </div>

                    {isAdmin && (
                      <button
                        type="button"
                        className="secondary-danger sm"
                        onClick={() => onDeleteOrderRecord(group.orderIds)}
                        title="Permanently delete this order record from database"
                      >
                        🗑️ Delete Record
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
