import { useState, useEffect, type FormEvent } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router";
import { Shield, KeyRound } from "lucide-react";
import { loginApi } from "../api/auth";
import {
  fetchEnabledProviders,
  initiateSSOLogin,
} from "../api/identity";
import type { IdentityProviderPublic } from "../api/identity";
import { useAuthStore } from "../stores/authStore";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";

export function LoginPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const setToken = useAuthStore((s) => s.setToken);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const [ssoProviders, setSsoProviders] = useState<IdentityProviderPublic[]>(
    [],
  );
  const [ssoLoading, setSsoLoading] = useState<string | null>(null);

  // Handle SSO token from URL (redirect back from IdP)
  useEffect(() => {
    const ssoToken = searchParams.get("sso_token");
    if (ssoToken) {
      // Clear URL params immediately
      setSearchParams({}, { replace: true });
      // Store token and navigate
      setToken(ssoToken);
      useAuthStore.getState().loadProfile().then(() => {
        navigate("/inbox", { replace: true });
      });
    }
  }, [searchParams, setSearchParams, setToken, navigate]);

  // Fetch enabled SSO providers on mount
  useEffect(() => {
    fetchEnabledProviders()
      .then((providers) => setSsoProviders(providers))
      .catch(() => {
        // Graceful degradation -- show only local login if fetch fails
        setSsoProviders([]);
      });
  }, []);

  // If already authenticated (and no sso_token being processed), redirect
  if (isAuthenticated && !searchParams.get("sso_token")) {
    return <Navigate to="/inbox" replace />;
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const token = await loginApi(username, password);
      setToken(token);
      await useAuthStore.getState().loadProfile();
      navigate("/inbox");
    } catch {
      setError("Invalid username or password.");
    } finally {
      setLoading(false);
    }
  };

  const handleSSOLogin = async (provider: IdentityProviderPublic) => {
    setSsoLoading(provider.id);
    setError(null);
    try {
      const result = await initiateSSOLogin(provider.id);
      // Store PKCE code_verifier for OIDC if present
      if (result.code_verifier) {
        sessionStorage.setItem("sso_code_verifier", result.code_verifier);
      }
      // Redirect to identity provider
      window.location.href = result.redirect_url;
    } catch {
      setError(`Failed to initiate SSO login with ${provider.name}.`);
      setSsoLoading(null);
    }
  };

  // Filter out LDAP providers (they use local login after sync)
  const ssoButtonProviders = ssoProviders.filter(
    (p) => p.provider_type === "saml" || p.provider_type === "oidc",
  );

  const providerIcon = (type: string) => {
    if (type === "saml") return <Shield className="h-4 w-4 mr-2" />;
    return <KeyRound className="h-4 w-4 mr-2" />;
  };

  return (
    <div className="min-h-screen flex items-start justify-center pt-24 bg-background">
      <Card className="w-full max-w-[400px] mx-auto">
        <CardHeader className="text-center">
          <CardTitle className="text-xl font-semibold">
            Workflow Designer
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <label htmlFor="username" className="text-sm font-medium">
                Username
              </label>
              <Input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter your username"
                required
                autoFocus
              />
            </div>
            <div className="flex flex-col gap-2">
              <label htmlFor="password" className="text-sm font-medium">
                Password
              </label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                required
              />
            </div>

            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}

            <Button type="submit" disabled={loading} className="w-full">
              {loading ? "Signing in..." : "Sign In"}
            </Button>
          </form>

          {/* SSO Buttons */}
          {ssoButtonProviders.length > 0 && (
            <div className="mt-6">
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-card px-2 text-muted-foreground">
                    Or sign in with
                  </span>
                </div>
              </div>
              <div className="mt-4 flex flex-col gap-2">
                {ssoButtonProviders.map((provider) => (
                  <Button
                    key={provider.id}
                    type="button"
                    variant="outline"
                    className="w-full"
                    disabled={ssoLoading === provider.id}
                    onClick={() => handleSSOLogin(provider)}
                  >
                    {providerIcon(provider.provider_type)}
                    {ssoLoading === provider.id
                      ? "Redirecting..."
                      : `Sign in with ${provider.name}`}
                  </Button>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
