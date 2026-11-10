/**
 * Dhee Stores - API Service Layer
 * Centralized API calls to the API Gateway (http://localhost:8010)
 */

const GATEWAY_URL = "http://localhost:8010";

let sessionExpiredHandler = null;

export function setSessionExpiredHandler(handler) {
  sessionExpiredHandler = handler;
}

function checkExpiredSession(res, url) {
  if (res.status === 401) {
    // Only trigger session expired if this is NOT a login/register attempt
    if (!url.includes("/login") && !url.includes("/register") && !url.includes("/verify-credentials")) {
      if (typeof sessionExpiredHandler === "function") {
        sessionExpiredHandler();
      }
    }
  }
}

// --- Products API ---
export async function getProducts(query = "") {
  const url = query.trim()
    ? `${GATEWAY_URL}/products?q=${encodeURIComponent(query.trim())}`
    : `${GATEWAY_URL}/products`;
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to fetch products.");
  }
  return res.json();
}

export async function createProduct(payload, token) {
  const url = `${GATEWAY_URL}/products`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    checkExpiredSession(res, url);
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to create product.");
  }
  return res.json();
}

export async function updateProduct(productId, payload, token) {
  const url = `${GATEWAY_URL}/products/${productId}`;
  const res = await fetch(url, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    checkExpiredSession(res, url);
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to update product.");
  }
  return res.json();
}

export async function deleteProduct(productId, token) {
  const url = `${GATEWAY_URL}/products/${productId}`;
  const res = await fetch(url, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    checkExpiredSession(res, url);
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to delete product.");
  }
  return res.json();
}

export async function toggleBlockProduct(productId, token) {
  const url = `${GATEWAY_URL}/products/${productId}/toggle-block`;
  const res = await fetch(url, {
    method: "PUT",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    checkExpiredSession(res, url);
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to update product block status.");
  }
  return res.json();
}

// --- Auth & Users API ---
export async function loginUser(email, password) {
  const url = `${GATEWAY_URL}/auth/login`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Invalid email or password.");
  }
  return res.json();
}

export async function registerUser(payload) {
  const url = `${GATEWAY_URL}/auth/register`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Registration failed.");
  }
  return res.json();
}

export async function updateProfile(userId, payload, token) {
  const url = `${GATEWAY_URL}/users/${userId}`;
  const res = await fetch(url, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    checkExpiredSession(res, url);
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to update profile.");
  }
  return res.json();
}

export async function deleteAccount(userId, token) {
  const url = `${GATEWAY_URL}/users/${userId}`;
  const res = await fetch(url, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    checkExpiredSession(res, url);
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to delete account.");
  }
  return res.json();
}

export async function getAllUsers(token) {
  const url = `${GATEWAY_URL}/users`;
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    checkExpiredSession(res, url);
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to fetch users.");
  }
  return res.json();
}

export async function toggleBlockUser(userId, token) {
  const url = `${GATEWAY_URL}/users/${userId}/toggle-block`;
  const res = await fetch(url, {
    method: "PUT",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    checkExpiredSession(res, url);
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to update user block status.");
  }
  return res.json();
}

// --- Orders API ---
export async function getOrders(token, user) {
  const url = user?.role === "admin"
    ? `${GATEWAY_URL}/orders`
    : `${GATEWAY_URL}/orders?user_id=${user?.id || ""}`;
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    checkExpiredSession(res, url);
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to fetch orders.");
  }
  return res.json();
}

export async function deleteOrder(orderId, token) {
  const url = `${GATEWAY_URL}/orders/${orderId}`;
  const res = await fetch(url, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    checkExpiredSession(res, url);
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to delete order.");
  }
  return res.json();
}

// --- Payment & Checkout API ---

export async function getPaymentConfig() {
  const res = await fetch(`${GATEWAY_URL}/orders/payment/config`);
  if (!res.ok) {
    return { razorpay_key_id: "", is_configured: false };
  }
  return res.json();
}

export async function createRazorpayOrder(amount, token) {
  const url = `${GATEWAY_URL}/orders/payment/razorpay/create-order`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ amount }),
  });
  if (!res.ok) {
    checkExpiredSession(res, url);
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to create Razorpay payment order.");
  }
  return res.json();
}

export async function verifyRazorpayPayment(payload, token) {
  const url = `${GATEWAY_URL}/orders/payment/razorpay/verify`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    checkExpiredSession(res, url);
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Payment verification failed.");
  }
  return res.json();
}

export async function checkoutCart(payload, token) {
  const url = `${GATEWAY_URL}/orders/checkout`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    checkExpiredSession(res, url);
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Cart checkout failed.");
  }
  return res.json();
}
