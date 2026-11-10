import { formatCurrency, formatNumber } from "../utils/format";

/**
 * eCommerce Product Card component
 * - Correctly fits images with aspect-ratio preservation (object-fit: contain)
 * - NO favorite/heart icons
 * - Title, Stock status, Price
 * - Default button: "🛒 Add Product"
 * - When added: Inline stepper with [-] {quantity} [+] inside the card
 * - Admin Edit & Delete actions
 */
export default function ProductCard({
  product,
  isAdmin,
  onAddToCart,
  onUpdateQuantity,
  cartQuantity = 0,
  onEdit,
  onToggleBlock,
}) {
  const isOutOfStock = product.stock <= 0;

  return (
    <div className={`product-card ${cartQuantity > 0 ? "in-cart-card" : ""} ${product.is_blocked ? "product-blocked" : ""}`}>
      {/* Centered Product Image Box (Correctly fit images, NO favorite icon) */}
      <div className="product-card-image-box">
        {product.image_url ? (
          <img
            src={product.image_url}
            alt={product.name}
            className="product-card-img"
            onError={(e) => {
              e.target.style.display = "none";
              if (e.target.nextSibling) {
                e.target.nextSibling.style.display = "flex";
              }
            }}
          />
        ) : null}
        <div
          className="product-card-placeholder"
          style={{ display: product.image_url ? "none" : "flex" }}
        >
          📦
        </div>
      </div>

      {/* Product Information Body */}
      <div className="product-card-body">
        <h4 className="product-card-title" title={product.name}>
          {product.name}
        </h4>

        {/* Stock Status Badge (1 or 0 in DB) */}
        <div className="product-card-stock">
          {product.is_blocked ? (
            <span className="stock-badge blocked">🚫 Blocked</span>
          ) : product.stock > 0 ? (
            <span className="stock-badge in-stock">● In Stock: {formatNumber(product.stock)}</span>
          ) : (
            <span className="stock-badge out-stock">✕ Out of Stock</span>
          )}
        </div>

        {/* Unit Price */}
        <div className="product-card-price">
          ₹{formatCurrency(product.price)}
        </div>

        {/* In-Card Action Button / Stepper (Customers only; Admins oversee catalog & dashboard) */}
        {!isAdmin ? (
          product.is_blocked ? (
            <button type="button" className="product-card-cart-btn blocked" disabled>
              🚫 Item Blocked
            </button>
          ) : isOutOfStock ? (
            <button type="button" className="product-card-cart-btn" disabled>
              ✕ Out of Stock
            </button>
          ) : cartQuantity === 0 ? (
            <button
              type="button"
              className="product-card-cart-btn"
              onClick={() => onAddToCart(product)}
            >
              🛒 Add to Cart
            </button>
          ) : (
            <div className="product-card-qty-stepper">
              <button
                type="button"
                className="stepper-action-btn minus"
                onClick={() => onUpdateQuantity(product.id, cartQuantity - 1)}
                title="Decrease quantity"
              >
                −
              </button>
              <span className="stepper-display-count">
                {cartQuantity} in cart
              </span>
              <button
                type="button"
                className="stepper-action-btn plus"
                disabled={cartQuantity >= product.stock}
                onClick={() => onUpdateQuantity(product.id, cartQuantity + 1)}
                title={cartQuantity >= product.stock ? "Max stock reached" : "Increase quantity"}
              >
                +
              </button>
            </div>
          )
        ) : null}

        {/* Admin Controls: Edit & Block/Unblock Toggle */}
        {isAdmin && (
          <div className="product-card-admin-actions">
            <button
              type="button"
              className="secondary sm"
              onClick={() => onEdit(product)}
              title="Edit product details"
            >
              ✏️ Edit
            </button>
            <button
              type="button"
              className={product.is_blocked ? "btn-unblock sm" : "btn-block sm"}
              onClick={() => onToggleBlock(product)}
              title={product.is_blocked ? "Unblock this product" : "Block this product"}
            >
              {product.is_blocked ? "🟢 Unblock" : "🚫 Block"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
