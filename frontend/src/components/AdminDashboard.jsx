import React, { useMemo } from "react";
import { formatCurrency, formatNumber } from "../utils/format";

/**
 * Modern SVG Pie Chart Generator
 * Calculates SVG arc paths for each slice based on proportional values.
 */
function SvgPieChart({ data, size = 260 }) {
  const center = size / 2;
  const radius = size / 2 - 16;
  const total = data.reduce((sum, item) => sum + item.value, 0);

  if (total <= 0) {
    return (
      <div style={{ textAlign: "center", padding: "2rem", color: "#64748b" }}>
        <span style={{ fontSize: "2rem" }}>🥧</span>
        <p style={{ margin: "0.5rem 0 0 0", fontSize: "0.88rem" }}>No sales recorded yet</p>
      </div>
    );
  }

  let cumulativeAngle = 0;

  const slices = data.map((item, idx) => {
    const sliceAngle = (item.value / total) * 360;
    const startAngle = cumulativeAngle;
    const endAngle = cumulativeAngle + sliceAngle;
    cumulativeAngle += sliceAngle;

    const startRad = (startAngle - 90) * (Math.PI / 180);
    const endRad = (endAngle - 90) * (Math.PI / 180);

    const x1 = center + radius * Math.cos(startRad);
    const y1 = center + radius * Math.sin(startRad);
    const x2 = center + radius * Math.cos(endRad);
    const y2 = center + radius * Math.sin(endRad);

    const largeArcFlag = sliceAngle > 180 ? 1 : 0;

    // Handle single full slice (360 degrees)
    const pathData =
      sliceAngle >= 359.9
        ? `M ${center} ${center - radius} A ${radius} ${radius} 0 1 1 ${center - 0.001} ${center - radius} Z`
        : `M ${center} ${center} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArcFlag} 1 ${x2} ${y2} Z`;

    return {
      ...item,
      pathData,
      percentage: ((item.value / total) * 100).toFixed(1),
    };
  });

  return (
    <div className="pie-chart-container">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="pie-chart-svg">
        <defs>
          <filter id="pie-shadow" x="-10%" y="-10%" width="120%" height="120%">
            <feDropShadow dx="0" dy="2" stdDeviation="3" floodOpacity="0.12" />
          </filter>
        </defs>
        {slices.map((slice, i) => (
          <path
            key={i}
            d={slice.pathData}
            fill={slice.color}
            filter="url(#pie-shadow)"
            className="pie-slice"
          >
            <title>{`${slice.label}: ₹${formatCurrency(slice.value)} (${slice.percentage}%)`}</title>
          </path>
        ))}
        {/* Inner Donut Circle for Modern Finish */}
        <circle cx={center} cy={center} r={radius * 0.45} fill="#ffffff" />
        <text
          x={center}
          y={center - 4}
          textAnchor="middle"
          fontSize="11"
          fontWeight="600"
          fill="#64748b"
        >
          TOTAL
        </text>
        <text
          x={center}
          y={center + 14}
          textAnchor="middle"
          fontSize="13"
          fontWeight="800"
          fill="#0f172a"
        >
          ₹{formatNumber(Math.round(total))}
        </text>
      </svg>
    </div>
  );
}

// Slice Color Palette
const PALETTE = [
  "#f97316", // Orange
  "#0ea5e9", // Sky
  "#10b981", // Emerald
  "#8b5cf6", // Violet
  "#f43f5e", // Rose
  "#eab308", // Yellow
  "#06b6d4", // Cyan
  "#ec4899", // Pink
  "#6366f1", // Indigo
  "#84cc16", // Lime
];

/**
 * Dedicated Admin Analytics Dashboard
 * Features:
 * - Key metric summary cards (Total Revenue, Orders, Inventory Cost, Users)
 * - Interactive SVG Pie Chart of Sales & Revenue by Product
 * - Inventory & Stock Valuation breakdown
 * - Quick shortcuts to Add Product and View Users Directory
 */
export default function AdminDashboard({
  orders = [],
  products = [],
  usersList = [],
  onOpenAddProduct,
  onOpenUsers,
  onNavigateToCatalog,
}) {
  // 1. Calculate Financials & Sales Metrics
  const totalSalesRevenue = useMemo(() => {
    return orders
      .filter((o) => (o.status || "").toUpperCase() !== "CANCELLED")
      .reduce((sum, o) => sum + Number(o.total_price || 0), 0);
  }, [orders]);

  const totalOrdersCount = orders.length;

  const totalInventoryStock = useMemo(() => {
    return products.reduce((sum, p) => sum + (p.stock || 0), 0);
  }, [products]);

  const totalInventoryValue = useMemo(() => {
    return products.reduce((sum, p) => sum + Number(p.price || 0) * (p.stock || 0), 0);
  }, [products]);

  const totalUsersCount = usersList.length;
  const adminUsersCount = usersList.filter((u) => u.role === "admin").length;
  const customerUsersCount = usersList.filter((u) => u.role === "customer").length;

  // 2. Aggregate Sales by Product for Pie Chart
  const salesByProduct = useMemo(() => {
    const map = {};
    orders
      .filter((o) => (o.status || "").toUpperCase() !== "CANCELLED")
      .forEach((o) => {
        const prod = products.find((p) => p.id === o.product_id);
        const name = prod ? prod.name : `Product #${o.product_id}`;
        if (!map[name]) {
          map[name] = { revenue: 0, units: 0 };
        }
        map[name].revenue += Number(o.total_price || 0);
        map[name].units += o.quantity || 1;
      });

    return Object.entries(map).map(([name, stats], idx) => ({
      label: name,
      value: stats.revenue,
      units: stats.units,
      color: PALETTE[idx % PALETTE.length],
    }));
  }, [orders, products]);

  return (
    <div className="admin-dashboard-container">
      {/* Dashboard Top Header */}
      <div className="page-header-row admin-dashboard-header">
        <div>
          <span className="admin-panel-badge">🛡️ System Administrator</span>
          <h2 style={{ margin: "0.35rem 0 0 0" }}>📊 Sales & Business Analytics Dashboard</h2>
          <p style={{ margin: "0.25rem 0 0 0", color: "#64748b", fontSize: "0.9rem" }}>
            Real-time platform sales, total revenue, inventory cost valuation, and registered users.
          </p>
        </div>

        <div style={{ display: "flex", gap: "0.65rem", flexWrap: "wrap" }}>
          <button type="button" className="sm" onClick={onOpenAddProduct}>
            ➕ Add Product
          </button>
          <button type="button" className="secondary sm" onClick={onOpenUsers}>
            👥 User Directory ({totalUsersCount})
          </button>
          <button type="button" className="secondary sm" onClick={onNavigateToCatalog}>
            🛍️ Manage Catalog
          </button>
        </div>
      </div>

      {/* Metric Summary Cards Grid */}
      <div className="dashboard-metrics-grid">
        {/* Metric 1: Total Revenue */}
        <div className="card metric-card revenue-card">
          <div className="metric-icon-wrap revenue-icon">💰</div>
          <div className="metric-data">
            <span className="metric-label">Total Platform Sales</span>
            <h3 className="metric-value">₹{formatCurrency(totalSalesRevenue)}</h3>
            <span className="metric-subtext">Across {formatNumber(totalOrdersCount)} completed orders</span>
          </div>
        </div>

        {/* Metric 2: Total Orders */}
        <div className="card metric-card orders-metric-card">
          <div className="metric-icon-wrap orders-icon">📦</div>
          <div className="metric-data">
            <span className="metric-label">Total Orders Placed</span>
            <h3 className="metric-value">{formatNumber(totalOrdersCount)}</h3>
            <span className="metric-subtext">Avg: ₹{formatCurrency(totalOrdersCount > 0 ? (totalSalesRevenue / totalOrdersCount) : 0)}/order</span>
          </div>
        </div>

        {/* Metric 3: Total Inventory Valuation */}
        <div className="card metric-card stock-card">
          <div className="metric-icon-wrap stock-icon">🏬</div>
          <div className="metric-data">
            <span className="metric-label">Inventory Retail Value</span>
            <h3 className="metric-value">₹{formatCurrency(totalInventoryValue)}</h3>
            <span className="metric-subtext">{formatNumber(totalInventoryStock)} total units in catalog</span>
          </div>
        </div>

        {/* Metric 4: Registered Users */}
        <div className="card metric-card users-metric-card" onClick={onOpenUsers} style={{ cursor: "pointer" }}>
          <div className="metric-icon-wrap users-icon">👥</div>
          <div className="metric-data">
            <span className="metric-label">Registered Accounts</span>
            <h3 className="metric-value">{formatNumber(totalUsersCount)}</h3>
            <span className="metric-subtext">
              {formatNumber(customerUsersCount)} Customers • {formatNumber(adminUsersCount)} Admins
            </span>
          </div>
        </div>
      </div>

      {/* Main Analytics Section: Pie Chart & Breakdown */}
      <div className="dashboard-analytics-layout">
        {/* Left Column: Pie Chart of Sales by Product */}
        <div className="card pie-chart-card">
          <div className="chart-card-header">
            <div>
              <h3 style={{ margin: 0 }}>🥧 Sales Distribution by Product</h3>
              <p style={{ margin: "0.2rem 0 0 0", color: "#64748b", fontSize: "0.85rem" }}>
                Total sales share generated by each product catalog item.
              </p>
            </div>
          </div>

          <div className="pie-chart-body">
            <SvgPieChart data={salesByProduct} size={250} />

            {/* Product Sales Legend & List */}
            <div className="pie-legend-list">
              {salesByProduct.length === 0 ? (
                <div style={{ textAlign: "center", color: "#64748b", padding: "1rem" }}>
                  No orders placed yet.
                </div>
              ) : (
                salesByProduct.map((item, idx) => {
                  const sharePct = totalSalesRevenue > 0
                    ? ((item.value / totalSalesRevenue) * 100).toFixed(1)
                    : "0.0";
                  return (
                    <div key={idx} className="legend-row">
                      <div className="legend-left">
                        <span className="legend-dot" style={{ backgroundColor: item.color }} />
                        <span className="legend-title" title={item.label}>{item.label}</span>
                      </div>
                      <div className="legend-right">
                        <span className="legend-units">{formatNumber(item.units)} sold</span>
                        <strong className="legend-amount">₹{formatCurrency(item.value)}</strong>
                        <span className="legend-pct">({sharePct}%)</span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Inventory & Cost Overview */}
        <div className="card inventory-summary-card">
          <div className="chart-card-header">
            <div>
              <h3 style={{ margin: 0 }}>🏷️ Catalog Stock & Cost Status</h3>
              <p style={{ margin: "0.2rem 0 0 0", color: "#64748b", fontSize: "0.85rem" }}>
                Total items ({formatNumber(products.length)} products), unit availability, and pricing.
              </p>
            </div>
          </div>

          <div className="inventory-table-wrapper">
            <table className="dashboard-table">
              <thead>
                <tr>
                  <th style={{ minWidth: "130px", textAlign: "left" }}>Product</th>
                  <th style={{ minWidth: "95px", width: "95px", textAlign: "center" }}>Status</th>
                  <th style={{ minWidth: "85px", textAlign: "right" }}>Price</th>
                  <th style={{ minWidth: "85px", textAlign: "center" }}>Stock</th>
                  <th style={{ minWidth: "115px", textAlign: "right" }}>Total Valuation</th>
                </tr>
              </thead>
              <tbody>
                {products.map((p) => {
                  const lineValue = Number(p.price) * p.stock;
                  const isLow = p.stock <= 10;
                  return (
                    <tr key={p.id}>
                      <td style={{ fontWeight: 600, textAlign: "left" }}>{p.name}</td>
                      <td style={{ textAlign: "center" }}>
                        <span className={`block-status-badge ${p.is_blocked ? "blocked" : "active"}`}>
                          {p.is_blocked ? "🚫 Blocked" : "🟢 Active"}
                        </span>
                      </td>
                      <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                        ₹{formatCurrency(p.price)}
                      </td>
                      <td style={{ textAlign: "center" }}>
                        <span className={`stock-badge ${isLow ? "out-stock" : "in-stock"}`}>
                          {formatNumber(p.stock)} units
                        </span>
                      </td>
                      <td style={{ fontWeight: 700, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                        ₹{formatCurrency(lineValue)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

