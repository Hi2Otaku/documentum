import { Link, Outlet, useNavigate } from "react-router";
import { useAuthStore } from "../../stores/authStore";
import { Button } from "../ui/button";

export function AppShell() {
  const navigate = useNavigate();
  const logout = useAuthStore((s) => s.logout);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Top nav bar - 48px height */}
      <header className="h-12 border-b bg-background flex items-center px-4 shrink-0">
        {/* Left: App name */}
        <span className="text-lg font-semibold">Workflow Designer</span>

        {/* Center: Templates nav link */}
        <nav className="flex-1 flex justify-center">
          <Link
            to="/templates"
            className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            Templates
          </Link>
        </nav>

        {/* Right: Logout button */}
        <Button variant="ghost" size="sm" onClick={handleLogout}>
          Logout
        </Button>
      </header>

      {/* Page content */}
      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  );
}
