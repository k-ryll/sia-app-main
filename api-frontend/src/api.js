const API_BASE = "http://72.60.194.243:3000"; // update with your VPS IP/domain

export async function login(username, password) {
  const formData = new URLSearchParams();
  formData.append("username", username);
  formData.append("password", password);

  const response = await fetch(`${API_BASE}/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: formData
  });

  if (!response.ok) throw new Error("Login failed");
  return response.json();
}

export async function getSecureData(token) {
  const response = await fetch(`${API_BASE}/secure-data`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!response.ok) throw new Error("Unauthorized");
  return response.json();
}
