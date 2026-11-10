/**
 * Admin Users Directory Modal
 * Displays all registered users with clean, modern horizontal row alignment.
 */
export default function UsersModal({
  isOpen,
  onClose,
  usersList,
  isLoading,
  onToggleBlockUser,
}) {
  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal-content users-directory-modal"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="modal-header">
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span style={{ fontSize: "1.5rem" }}>👥</span>
            <div>
              <h3 style={{ margin: 0 }}>Registered Users Directory</h3>
              <p style={{ margin: "0.2rem 0 0 0", color: "#64748b", fontSize: "0.85rem" }}>
                Active user accounts registered in MySQL <code>users_db.users</code>.
              </p>
            </div>
          </div>
          <button type="button" className="close-btn" onClick={onClose}>
            ✕
          </button>
        </div>

        {/* Modal Body / Users List */}
        <div className="users-directory-body">
          {isLoading ? (
            <div style={{ textAlign: "center", padding: "2.5rem 1rem", color: "#64748b" }}>
              <span style={{ fontSize: "2rem" }}>⏳</span>
              <p style={{ marginTop: "0.5rem" }}>Loading registered users...</p>
            </div>
          ) : usersList.length === 0 ? (
            <div style={{ textAlign: "center", padding: "2.5rem 1rem", color: "#64748b" }}>
              <p>No registered users found.</p>
            </div>
          ) : (
            <div className="users-list-wrapper">
              {usersList.map((u) => {
                const isAdmin = u.role === "admin";
                const userInitial = u.name ? u.name.charAt(0).toUpperCase() : "U";

                return (
                  <div key={u.id} className="user-directory-row">
                    {/* Left: User Avatar & Information */}
                    <div className="user-directory-left">
                      <div className={`user-row-avatar ${isAdmin ? "avatar-admin" : "avatar-customer"}`} style={{ overflow: "hidden" }}>
                        {u.profile_image ? (
                          <img
                            src={u.profile_image}
                            alt={u.name}
                            style={{ width: "100%", height: "100%", objectFit: "cover" }}
                            onError={(e) => {
                              e.target.style.display = "none";
                              if (e.target.nextSibling) e.target.nextSibling.style.display = "inline";
                            }}
                          />
                        ) : null}
                        <span style={{ display: u.profile_image ? "none" : "inline" }}>{userInitial}</span>
                      </div>

                      <div className="user-row-details">
                        <div className="user-row-name-line">
                          <strong className="user-row-name">{u.name}</strong>
                          <span className={`role-badge ${u.role}`}>{u.role}</span>
                        </div>
                        <div className="user-row-meta">
                          <span className="user-row-email">{u.email}</span>
                          <span className="meta-dot">•</span>
                          <span className="user-row-id">ID #{u.id}</span>
                        </div>
                      </div>
                    </div>

                    {/* Right: Actions / Block-Unblock Status (1 or 0 in DB) */}
                    <div className="user-directory-right" style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                      <span className={`block-status-badge ${u.is_blocked ? "blocked" : "active"}`}>
                        {u.is_blocked ? "🚫 Blocked" : "🟢 Active"}
                      </span>
                      {isAdmin ? (
                        <span className="admin-status-pill" title="Administrator account protected">
                          🛡️ System Admin
                        </span>
                      ) : (
                        <button
                          type="button"
                          className={u.is_blocked ? "btn-unblock sm" : "btn-block sm"}
                          onClick={() => onToggleBlockUser(u)}
                          title={u.is_blocked ? `Unblock user ${u.name}` : `Block user ${u.name}`}
                        >
                          {u.is_blocked ? "🟢 Unblock" : "🚫 Block"}
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="users-directory-footer">
          <span style={{ fontSize: "0.85rem", color: "#64748b" }}>
            Total Users: <strong>{usersList.length}</strong>
          </span>
          <button type="button" className="secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
