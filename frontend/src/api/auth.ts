const BASE = "/api/v1/auth";

/**
 * Log in with username and password using OAuth2 form-data format.
 * Returns the access token string on success.
 */
export async function loginApi(
  username: string,
  password: string
): Promise<string> {
  const body = new URLSearchParams();
  body.append("username", username);
  body.append("password", password);

  const res = await fetch(`${BASE}/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: body.toString(),
  });

  if (!res.ok) {
    throw new Error("Invalid username or password.");
  }

  const data = await res.json();
  return data.access_token;
}
