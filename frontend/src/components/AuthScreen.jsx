import React, { useState } from "react";
import { useFormik } from "formik";
import * as Yup from "yup";

const LoginValidationSchema = Yup.object({
  email: Yup.string()
    .trim()
    .email("Please enter a valid email address")
    .required("Email address is required"),
  password: Yup.string()
    .min(6, "Password must be at least 6 characters")
    .required("Password is required"),
});

const RegisterValidationSchema = Yup.object({
  name: Yup.string().trim().min(2, "Name must be at least 2 characters").required("Full name is required"),
  email: Yup.string().trim().email("Please enter a valid email address").required("Email address is required"),
  password: Yup.string().min(6, "Password must be at least 6 characters").required("Password is required"),
  role: Yup.string().oneOf(["customer", "admin"], "Invalid role").required("Role is required"),
  profile_image: Yup.string().trim().url("Please enter a valid image URL (http/https)").nullable(),
});

/**
 * Authentication Screen for Dhee Stores
 * Requires both Email Address and Password for secure login and registration.
 */
export default function AuthScreen({ onLogin, onRegister, error, success, onClearMessages }) {
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [showLoginPassword, setShowLoginPassword] = useState(false);
  const [showRegisterPassword, setShowRegisterPassword] = useState(false);

  const loginFormik = useFormik({
    initialValues: { email: "", password: "" },
    validationSchema: LoginValidationSchema,
    onSubmit: (values) => {
      onLogin(values.email.trim(), values.password);
    },
  });

  const registerFormik = useFormik({
    initialValues: { name: "", email: "", password: "", role: "customer", profile_image: "" },
    validationSchema: RegisterValidationSchema,
    onSubmit: (values) => {
      onRegister({
        name: values.name.trim(),
        email: values.email.trim(),
        password: values.password,
        role: values.role,
        profile_image: values.profile_image ? values.profile_image.trim() : null,
      });
    },
  });

  const handleLoginFieldChange = (e) => {
    if (error || success) onClearMessages();
    loginFormik.handleChange(e);
  };

  const handleRegisterFieldChange = (e) => {
    if (error || success) onClearMessages();
    registerFormik.handleChange(e);
  };

  const toggleMode = () => {
    setIsRegisterMode((prev) => !prev);
    onClearMessages();
    loginFormik.resetForm();
    registerFormik.resetForm();
  };

  return (
    <div className="auth-container">
      <div className="card auth-card">
        {/* Brand Header */}
        <div className="auth-brand-header">
          <img src="/logo.png" alt="Dhee Stores Logo" className="auth-logo" />
          <h2 className="auth-brand-title">Dhee Stores</h2>
          <p className="auth-brand-subtitle">
            {isRegisterMode ? "Create your new customer account" : "Sign in to explore our catalog"}
          </p>
        </div>

        {/* Global Notifications inside Auth Card with Close Button */}
        {error && (
          <div className="alert-error" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span>⚠️ {error}</span>
            <button
              type="button"
              className="alert-dismiss-btn"
              onClick={onClearMessages}
              title="Dismiss error message"
            >
              ✕
            </button>
          </div>
        )}
        {success && (
          <div className="alert-success" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span>✅ {success}</span>
            <button
              type="button"
              className="alert-dismiss-btn"
              onClick={onClearMessages}
              title="Dismiss notification"
            >
              ✕
            </button>
          </div>
        )}

        {/* Login Form */}
        {!isRegisterMode ? (
          <form onSubmit={loginFormik.handleSubmit}>
            <div className="form-group">
              <label>Email Address *</label>
              <input
                name="email"
                type="email"
                placeholder="Enter your registered email"
                value={loginFormik.values.email}
                onChange={handleLoginFieldChange}
                onBlur={loginFormik.handleBlur}
                className={loginFormik.touched.email && loginFormik.errors.email ? "input-error" : ""}
              />
              {loginFormik.touched.email && loginFormik.errors.email && (
                <div className="form-error">{loginFormik.errors.email}</div>
              )}
            </div>

            <div className="form-group">
              <label>Password *</label>
              <div className="password-input-wrapper">
                <input
                  name="password"
                  type={showLoginPassword ? "text" : "password"}
                  placeholder="Enter your password"
                  value={loginFormik.values.password}
                  onChange={handleLoginFieldChange}
                  onBlur={loginFormik.handleBlur}
                  className={loginFormik.touched.password && loginFormik.errors.password ? "input-error" : ""}
                />
                <button
                  type="button"
                  className="password-toggle-btn"
                  onClick={() => setShowLoginPassword((prev) => !prev)}
                  title={showLoginPassword ? "Hide password" : "Show password"}
                  aria-label="Toggle password visibility"
                >
                  {showLoginPassword ? "🙈" : "👁️"}
                </button>
              </div>
              {loginFormik.touched.password && loginFormik.errors.password && (
                <div className="form-error">{loginFormik.errors.password}</div>
              )}
            </div>

            <button type="submit" style={{ width: "100%", marginTop: "0.5rem" }} disabled={!loginFormik.isValid}>
              Sign In
            </button>

            <div className="auth-switch-prompt">
              New to Dhee Stores?{" "}
              <button
                type="button"
                className="auth-switch-link"
                onClick={toggleMode}
              >
                Create an Account
              </button>
            </div>
          </form>
        ) : (
          /* Register Form */
          <form onSubmit={registerFormik.handleSubmit}>
            <div className="form-group">
              <label>Full Name *</label>
              <input
                name="name"
                type="text"
                placeholder="e.g. User Name"
                value={registerFormik.values.name}
                onChange={handleRegisterFieldChange}
                onBlur={registerFormik.handleBlur}
                className={registerFormik.touched.name && registerFormik.errors.name ? "input-error" : ""}
              />
              {registerFormik.touched.name && registerFormik.errors.name && (
                <div className="form-error">{registerFormik.errors.name}</div>
              )}
            </div>

            <div className="form-group">
              <label>Email Address *</label>
              <input
                name="email"
                type="email"
                placeholder="e.g. user@example.com"
                value={registerFormik.values.email}
                onChange={handleRegisterFieldChange}
                onBlur={registerFormik.handleBlur}
                className={registerFormik.touched.email && registerFormik.errors.email ? "input-error" : ""}
              />
              {registerFormik.touched.email && registerFormik.errors.email && (
                <div className="form-error">{registerFormik.errors.email}</div>
              )}
            </div>

            <div className="form-group">
              <label>Password (min 6 characters) *</label>
              <div className="password-input-wrapper">
                <input
                  name="password"
                  type={showRegisterPassword ? "text" : "password"}
                  placeholder="Create a strong password"
                  value={registerFormik.values.password}
                  onChange={handleRegisterFieldChange}
                  onBlur={registerFormik.handleBlur}
                  className={registerFormik.touched.password && registerFormik.errors.password ? "input-error" : ""}
                />
                <button
                  type="button"
                  className="password-toggle-btn"
                  onClick={() => setShowRegisterPassword((prev) => !prev)}
                  title={showRegisterPassword ? "Hide password" : "Show password"}
                  aria-label="Toggle password visibility"
                >
                  {showRegisterPassword ? "🙈" : "👁️"}
                </button>
              </div>
              {registerFormik.touched.password && registerFormik.errors.password && (
                <div className="form-error">{registerFormik.errors.password}</div>
              )}
            </div>

            <div className="form-group">
              <label>Profile Image URL (Optional)</label>
              <input
                name="profile_image"
                type="url"
                placeholder="https://example.com/avatar.jpg"
                value={registerFormik.values.profile_image}
                onChange={handleRegisterFieldChange}
                onBlur={registerFormik.handleBlur}
                className={registerFormik.touched.profile_image && registerFormik.errors.profile_image ? "input-error" : ""}
              />
              {registerFormik.touched.profile_image && registerFormik.errors.profile_image && (
                <div className="form-error">{registerFormik.errors.profile_image}</div>
              )}
            </div>

            <div className="form-group">
              <label>Role</label>
              <select
                name="role"
                value={registerFormik.values.role}
                onChange={registerFormik.handleChange}
              >
                <option value="customer">Customer (Catalog & Purchases)</option>
                <option value="admin">Admin (Manage Inventory & Users)</option>
              </select>
            </div>

            <button type="submit" style={{ width: "100%", marginTop: "0.5rem" }} disabled={!registerFormik.isValid}>
              Register
            </button>

            <div className="auth-switch-prompt">
              Already have an account?{" "}
              <button
                type="button"
                className="auth-switch-link"
                onClick={toggleMode}
              >
                Sign In
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
