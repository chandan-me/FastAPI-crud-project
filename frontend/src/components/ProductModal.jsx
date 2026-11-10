import { useFormik } from "formik";
import * as Yup from "yup";

const ProductValidationSchema = Yup.object({
  name: Yup.string()
    .trim()
    .min(2, "Product name must be at least 2 characters")
    .required("Product name is required"),
  price: Yup.number()
    .typeError("Price must be a valid number")
    .positive("Price must be greater than 0")
    .required("Price is required"),
  stock: Yup.number()
    .typeError("Stock must be an integer")
    .integer("Stock must be a whole number")
    .min(0, "Stock cannot be negative")
    .required("Stock is required"),
  image_url: Yup.string()
    .trim()
    .url("Must be a valid URL (e.g. https://images.google.com/...)")
    .nullable()
    .notRequired(),
});

/**
 * Product Modal (Add / Edit) with Formik + Yup validation and live image preview
 */
export default function ProductModal({
  isOpen,
  onClose,
  editingProduct,
  onSave,
  isSaving,
}) {
  const isEdit = !!editingProduct;

  const formik = useFormik({
    enableReinitialize: true,
    initialValues: {
      name: editingProduct?.name || "",
      price: editingProduct?.price ?? "",
      stock: editingProduct?.stock ?? "",
      image_url: editingProduct?.image_url || "",
    },
    validationSchema: ProductValidationSchema,
    onSubmit: (values) => {
      onSave({
        name: values.name.trim(),
        price: parseFloat(values.price),
        stock: parseInt(values.stock, 10),
        image_url: values.image_url ? values.image_url.trim() : null,
      });
    },
  });

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <h3 style={{ margin: 0 }}>{isEdit ? "✏️ Edit Product" : "➕ Add New Product"}</h3>
          <button type="button" className="close-btn" onClick={onClose}>
            ✕
          </button>
        </div>

        <form onSubmit={formik.handleSubmit}>
          {/* Product Name */}
          <div className="form-group">
            <label>Product Name *</label>
            <input
              name="name"
              type="text"
              placeholder="e.g. Smart Watch Series 5"
              value={formik.values.name}
              onChange={formik.handleChange}
              onBlur={formik.handleBlur}
              className={formik.touched.name && formik.errors.name ? "input-error" : ""}
            />
            {formik.touched.name && formik.errors.name && (
              <div className="form-error">{formik.errors.name}</div>
            )}
          </div>

          {/* Unit Price */}
          <div className="form-group">
            <label>Price (₹) *</label>
            <input
              name="price"
              type="number"
              step="0.01"
              placeholder="e.g. 89.99"
              value={formik.values.price}
              onChange={formik.handleChange}
              onBlur={formik.handleBlur}
              className={formik.touched.price && formik.errors.price ? "input-error" : ""}
            />
            {formik.touched.price && formik.errors.price && (
              <div className="form-error">{formik.errors.price}</div>
            )}
          </div>

          {/* Stock Count */}
          <div className="form-group">
            <label>Initial Stock Count *</label>
            <input
              name="stock"
              type="number"
              placeholder="e.g. 25"
              value={formik.values.stock}
              onChange={formik.handleChange}
              onBlur={formik.handleBlur}
              className={formik.touched.stock && formik.errors.stock ? "input-error" : ""}
            />
            {formik.touched.stock && formik.errors.stock && (
              <div className="form-error">{formik.errors.stock}</div>
            )}
          </div>

          {/* Image URL with live preview */}
          <div className="form-group">
            <label>Product Image URL (Optional)</label>
            <input
              name="image_url"
              type="url"
              placeholder="https://images.unsplash.com/photo-..."
              value={formik.values.image_url}
              onChange={formik.handleChange}
              onBlur={formik.handleBlur}
              className={formik.touched.image_url && formik.errors.image_url ? "input-error" : ""}
            />
            {formik.touched.image_url && formik.errors.image_url && (
              <div className="form-error">{formik.errors.image_url}</div>
            )}

            {/* Live Image Preview */}
            {formik.values.image_url && !formik.errors.image_url && (
              <div className="image-preview-container">
                <div style={{ fontSize: "0.75rem", color: "#64748b", marginBottom: "0.4rem" }}>
                  Live Image Preview:
                </div>
                <img
                  src={formik.values.image_url}
                  alt="Preview"
                  className="image-preview-img"
                  onError={(e) => { e.target.style.display = "none"; }}
                  onLoad={(e) => { e.target.style.display = "inline-block"; }}
                />
              </div>
            )}
          </div>

          {/* Modal Actions */}
          <div className="action-btn-group" style={{ marginTop: "1.5rem", justifyContent: "flex-end" }}>
            <button type="button" className="secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" disabled={isSaving || !formik.isValid}>
              {isSaving ? "Saving..." : isEdit ? "Save Changes" : "Create Product"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

