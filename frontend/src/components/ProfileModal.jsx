import { useFormik } from "formik";
import * as Yup from "yup";

const ProfileValidationSchema = Yup.object({
  name: Yup.string().trim().min(2, "Name must be at least 2 characters").required("Name is required"),
  email: Yup.string().trim().email("Please enter a valid email address").required("Email is required"),
  profile_image: Yup.string().trim().url("Please enter a valid image URL (http/https)").nullable(),
});

/**
 * Account Settings Modal with Profile Image support
 */
export default function ProfileModal({
  isOpen,
  onClose,
  currentUser,
  onSave,
  isSaving,
}) {
  const formik = useFormik({
    enableReinitialize: true,
    initialValues: {
      name: currentUser?.name || "",
      email: currentUser?.email || "",
      profile_image: currentUser?.profile_image || "",
    },
    validationSchema: ProfileValidationSchema,
    onSubmit: (values) => {
      onSave({
        name: values.name.trim(),
        email: values.email.trim(),
        profile_image: values.profile_image ? values.profile_image.trim() : null,
      });
    },
  });

  if (!isOpen) return null;

  const currentPreview = formik.values.profile_image?.trim() || currentUser?.profile_image;
  const initial = currentUser?.name ? currentUser.name.charAt(0).toUpperCase() : "U";

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "480px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <h3 style={{ margin: 0 }}>⚙️ Account Settings</h3>
          <button type="button" className="close-btn" onClick={onClose}>
            ✕
          </button>
        </div>

        {/* Profile Avatar Header Preview */}
        <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "1.25rem", padding: "0.85rem", background: "#f8fafc", borderRadius: "12px", border: "1px solid #e2e8f0" }}>
          <div style={{ width: "64px", height: "64px", minWidth: "64px", borderRadius: "50%", overflow: "hidden", background: "#0d9488", display: "flex", alignItems: "center", justifyContent: "center", color: "#ffffff", fontWeight: 700, fontSize: "1.5rem", border: "2px solid #cbd5e1" }}>
            {currentPreview ? (
              <img
                src={currentPreview}
                alt="Profile Preview"
                style={{ width: "100%", height: "100%", objectFit: "cover" }}
                onError={(e) => { e.target.style.display = "none"; }}
              />
            ) : (
              <span>{initial}</span>
            )}
          </div>
          <div>
            <strong style={{ fontSize: "1.05rem", color: "#0f172a" }}>{currentUser?.name}</strong>
            <p style={{ margin: "0.2rem 0 0 0", fontSize: "0.82rem", color: "#64748b" }}>
              Role: <span style={{ textTransform: "capitalize", fontWeight: 600 }}>{currentUser?.role}</span>
            </p>
          </div>
        </div>

        <form onSubmit={formik.handleSubmit}>
          <div className="form-group">
            <label>Full Name *</label>
            <input
              name="name"
              type="text"
              value={formik.values.name}
              onChange={formik.handleChange}
              onBlur={formik.handleBlur}
              className={formik.touched.name && formik.errors.name ? "input-error" : ""}
            />
            {formik.touched.name && formik.errors.name && (
              <div className="form-error">{formik.errors.name}</div>
            )}
          </div>

          <div className="form-group">
            <label>Email Address *</label>
            <input
              name="email"
              type="email"
              value={formik.values.email}
              onChange={formik.handleChange}
              onBlur={formik.handleBlur}
              className={formik.touched.email && formik.errors.email ? "input-error" : ""}
            />
            {formik.touched.email && formik.errors.email && (
              <div className="form-error">{formik.errors.email}</div>
            )}
          </div>

          <div className="form-group">
            <label>Profile Image URL</label>
            <input
              name="profile_image"
              type="url"
              placeholder="https://example.com/img.jpg"
              value={formik.values.profile_image}
              onChange={formik.handleChange}
              onBlur={formik.handleBlur}
              className={formik.touched.profile_image && formik.errors.profile_image ? "input-error" : ""}
            />
            {formik.touched.profile_image && formik.errors.profile_image && (
              <div className="form-error">{formik.errors.profile_image}</div>
            )}
            <small style={{ color: "#64748b", fontSize: "0.78rem", marginTop: "0.25rem", display: "block" }}>
              upload u image in url only             </small>
          </div>

          <div className="action-btn-group" style={{ marginTop: "1.5rem", display: "flex", gap: "0.75rem", justifyContent: "flex-end" }}>
            <button type="button" className="secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" disabled={isSaving || !formik.isValid}>
              {isSaving ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

