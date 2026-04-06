/** Shared 401 handler — clears expired token and redirects to login. */
export function handle401(): never {
  localStorage.removeItem("token");
  window.location.href = "/login";
  throw new Error("Session expired");
}
