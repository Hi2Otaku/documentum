import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Shield, Pencil, Trash2, PlugZap, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Switch } from "../components/ui/switch";
import { Badge } from "../components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import {
  fetchProviders,
  createProvider,
  updateProvider,
  deleteProvider,
  testLdapConnection,
  syncLdap,
} from "../api/identity";
import type {
  IdentityProvider,
  IdentityProviderCreate,
  IdentityProviderUpdate,
} from "../api/identity";

const TYPE_COLORS: Record<string, string> = {
  ldap: "bg-blue-100 text-blue-800",
  saml: "bg-purple-100 text-purple-800",
  oidc: "bg-green-100 text-green-800",
};

export function SSOSettingsPage() {
  const queryClient = useQueryClient();
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editingProvider, setEditingProvider] =
    useState<IdentityProvider | null>(null);

  const { data: providers = [], isLoading } = useQuery({
    queryKey: ["identity-providers"],
    queryFn: fetchProviders,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteProvider(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["identity-providers"] });
      toast.success("Provider deleted");
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_enabled }: { id: string; is_enabled: boolean }) =>
      updateProvider(id, { is_enabled }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["identity-providers"] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const testMutation = useMutation({
    mutationFn: (id: string) => testLdapConnection(id),
    onSuccess: (data) => {
      if (data.success) {
        toast.success(data.message || "LDAP connection successful");
      } else {
        toast.error(data.message || "LDAP connection failed");
      }
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const syncMutation = useMutation({
    mutationFn: (id: string) => syncLdap(id),
    onSuccess: (data) => {
      toast.success(
        data.message ||
          `Synced ${data.users_synced} users and ${data.groups_synced} groups`,
      );
    },
    onError: (err: Error) => toast.error(err.message),
  });

  function handleDelete(id: string, name: string) {
    if (window.confirm(`Delete identity provider "${name}"?`)) {
      deleteMutation.mutate(id);
    }
  }

  function handleSuccess() {
    queryClient.invalidateQueries({ queryKey: ["identity-providers"] });
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-muted-foreground" />
          <h1 className="text-lg font-semibold">SSO Settings</h1>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>Add Provider</Button>
      </div>

      {/* Providers Table */}
      {isLoading ? (
        <p className="text-muted-foreground text-sm">Loading providers...</p>
      ) : providers.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          No identity providers configured yet.
        </p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Enabled</TableHead>
              <TableHead>Created</TableHead>
              <TableHead className="w-48">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {providers.map((provider) => (
              <TableRow key={provider.id}>
                <TableCell className="font-medium">{provider.name}</TableCell>
                <TableCell>
                  <Badge
                    variant="secondary"
                    className={TYPE_COLORS[provider.provider_type] ?? ""}
                  >
                    {provider.provider_type.toUpperCase()}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Switch
                    checked={provider.is_enabled}
                    onCheckedChange={(checked) =>
                      toggleMutation.mutate({
                        id: provider.id,
                        is_enabled: checked,
                      })
                    }
                  />
                </TableCell>
                <TableCell>
                  {new Date(provider.created_at).toLocaleDateString()}
                </TableCell>
                <TableCell>
                  <div className="flex gap-1">
                    {provider.provider_type === "ldap" && (
                      <>
                        <Button
                          variant="ghost"
                          size="icon"
                          title="Test Connection"
                          disabled={testMutation.isPending}
                          onClick={() => testMutation.mutate(provider.id)}
                        >
                          <PlugZap className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          title="Sync Now"
                          disabled={syncMutation.isPending}
                          onClick={() => syncMutation.mutate(provider.id)}
                        >
                          <RefreshCw className="h-4 w-4" />
                        </Button>
                      </>
                    )}
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setEditingProvider(provider)}
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() =>
                        handleDelete(provider.id, provider.name)
                      }
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {/* Create Dialog */}
      <ProviderDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
        onSuccess={handleSuccess}
        mode="create"
      />

      {/* Edit Dialog */}
      {editingProvider && (
        <ProviderDialog
          open={editingProvider !== null}
          onOpenChange={(open) => {
            if (!open) setEditingProvider(null);
          }}
          onSuccess={() => {
            handleSuccess();
            setEditingProvider(null);
          }}
          mode="edit"
          provider={editingProvider}
        />
      )}
    </div>
  );
}

// --- Shared Create/Edit Dialog ---

interface ProviderDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  mode: "create" | "edit";
  provider?: IdentityProvider;
}

type ProviderType = "ldap" | "saml" | "oidc";

function ProviderDialog({
  open,
  onOpenChange,
  onSuccess,
  mode,
  provider,
}: ProviderDialogProps) {
  const [name, setName] = useState(provider?.name ?? "");
  const [providerType, setProviderType] = useState<ProviderType>(
    provider?.provider_type ?? "ldap",
  );
  const [error, setError] = useState<string | null>(null);

  // LDAP config
  const [serverUrl, setServerUrl] = useState(
    (provider?.config?.server_url as string) ?? "",
  );
  const [bindDn, setBindDn] = useState(
    (provider?.config?.bind_dn as string) ?? "",
  );
  const [bindPassword, setBindPassword] = useState("");
  const [baseDn, setBaseDn] = useState(
    (provider?.config?.base_dn as string) ?? "",
  );
  const [userSearchFilter, setUserSearchFilter] = useState(
    (provider?.config?.user_search_filter as string) ?? "(objectClass=person)",
  );
  const [groupSearchFilter, setGroupSearchFilter] = useState(
    (provider?.config?.group_search_filter as string) ??
      "(objectClass=groupOfNames)",
  );
  const [syncInterval, setSyncInterval] = useState(
    String(provider?.config?.sync_interval_minutes ?? 60),
  );

  // SAML config
  const [idpMetadataUrl, setIdpMetadataUrl] = useState(
    (provider?.config?.idp_metadata_url as string) ?? "",
  );
  const [idpEntityId, setIdpEntityId] = useState(
    (provider?.config?.idp_entity_id as string) ?? "",
  );
  const [spEntityId, setSpEntityId] = useState(
    (provider?.config?.sp_entity_id as string) ?? "",
  );
  const [spAcsUrl, setSpAcsUrl] = useState(
    (provider?.config?.sp_acs_url as string) ?? "",
  );

  // OIDC config
  const [issuerUrl, setIssuerUrl] = useState(
    (provider?.config?.issuer_url as string) ?? "",
  );
  const [clientId, setClientId] = useState(
    (provider?.config?.client_id as string) ?? "",
  );
  const [clientSecret, setClientSecret] = useState("");
  const [redirectUri, setRedirectUri] = useState(
    (provider?.config?.redirect_uri as string) ?? "",
  );
  const [scopes, setScopes] = useState(
    (provider?.config?.scopes as string) ?? "openid,profile,email",
  );

  const createMutation = useMutation({
    mutationFn: (data: IdentityProviderCreate) => createProvider(data),
    onSuccess: () => {
      onSuccess();
      onOpenChange(false);
      toast.success("Provider created");
    },
    onError: (err: Error) => setError(err.message),
  });

  const updateMutation = useMutation({
    mutationFn: (data: IdentityProviderUpdate) =>
      updateProvider(provider!.id, data),
    onSuccess: () => {
      onSuccess();
      onOpenChange(false);
      toast.success("Provider updated");
    },
    onError: (err: Error) => setError(err.message),
  });

  function buildConfig(): Record<string, unknown> {
    if (providerType === "ldap") {
      const cfg: Record<string, unknown> = {
        server_url: serverUrl,
        bind_dn: bindDn,
        base_dn: baseDn,
        user_search_filter: userSearchFilter,
        group_search_filter: groupSearchFilter,
        sync_interval_minutes: parseInt(syncInterval, 10) || 60,
      };
      if (bindPassword) cfg.bind_password = bindPassword;
      return cfg;
    }
    if (providerType === "saml") {
      return {
        idp_metadata_url: idpMetadataUrl,
        idp_entity_id: idpEntityId,
        sp_entity_id: spEntityId,
        sp_acs_url: spAcsUrl,
      };
    }
    // oidc
    const cfg: Record<string, unknown> = {
      issuer_url: issuerUrl,
      client_id: clientId,
      redirect_uri: redirectUri,
      scopes,
    };
    if (clientSecret) cfg.client_secret = clientSecret;
    return cfg;
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError("Name is required.");
      return;
    }

    const config = buildConfig();

    if (mode === "create") {
      createMutation.mutate({
        name: name.trim(),
        provider_type: providerType,
        config,
        is_enabled: false,
      });
    } else {
      updateMutation.mutate({
        name: name.trim(),
        config,
      });
    }
  }

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {mode === "create"
              ? "Add Identity Provider"
              : "Edit Identity Provider"}
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="provider-name">Name</Label>
            <Input
              id="provider-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Corporate LDAP"
            />
          </div>

          <div>
            <Label htmlFor="provider-type">Type</Label>
            <Select
              value={providerType}
              onValueChange={(v) => setProviderType(v as ProviderType)}
              disabled={mode === "edit"}
            >
              <SelectTrigger id="provider-type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ldap">LDAP</SelectItem>
                <SelectItem value="saml">SAML</SelectItem>
                <SelectItem value="oidc">OIDC</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* LDAP Config Fields */}
          {providerType === "ldap" && (
            <>
              <div>
                <Label htmlFor="ldap-server">Server URL</Label>
                <Input
                  id="ldap-server"
                  value={serverUrl}
                  onChange={(e) => setServerUrl(e.target.value)}
                  placeholder="ldap://ldap.example.com:389"
                />
              </div>
              <div>
                <Label htmlFor="ldap-bind-dn">Bind DN</Label>
                <Input
                  id="ldap-bind-dn"
                  value={bindDn}
                  onChange={(e) => setBindDn(e.target.value)}
                  placeholder="cn=admin,dc=example,dc=com"
                />
              </div>
              <div>
                <Label htmlFor="ldap-bind-password">
                  Bind Password{" "}
                  {mode === "edit" && (
                    <span className="text-muted-foreground font-normal">
                      (leave blank to keep current)
                    </span>
                  )}
                </Label>
                <Input
                  id="ldap-bind-password"
                  type="password"
                  value={bindPassword}
                  onChange={(e) => setBindPassword(e.target.value)}
                  placeholder={mode === "edit" ? "********" : ""}
                />
              </div>
              <div>
                <Label htmlFor="ldap-base-dn">Base DN</Label>
                <Input
                  id="ldap-base-dn"
                  value={baseDn}
                  onChange={(e) => setBaseDn(e.target.value)}
                  placeholder="dc=example,dc=com"
                />
              </div>
              <div>
                <Label htmlFor="ldap-user-filter">User Search Filter</Label>
                <Input
                  id="ldap-user-filter"
                  value={userSearchFilter}
                  onChange={(e) => setUserSearchFilter(e.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="ldap-group-filter">Group Search Filter</Label>
                <Input
                  id="ldap-group-filter"
                  value={groupSearchFilter}
                  onChange={(e) => setGroupSearchFilter(e.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="ldap-sync-interval">
                  Sync Interval (minutes)
                </Label>
                <Input
                  id="ldap-sync-interval"
                  type="number"
                  min={1}
                  value={syncInterval}
                  onChange={(e) => setSyncInterval(e.target.value)}
                />
              </div>
            </>
          )}

          {/* SAML Config Fields */}
          {providerType === "saml" && (
            <>
              <div>
                <Label htmlFor="saml-metadata-url">IdP Metadata URL</Label>
                <Input
                  id="saml-metadata-url"
                  value={idpMetadataUrl}
                  onChange={(e) => setIdpMetadataUrl(e.target.value)}
                  placeholder="https://idp.example.com/metadata"
                />
              </div>
              <div>
                <Label htmlFor="saml-idp-entity">IdP Entity ID</Label>
                <Input
                  id="saml-idp-entity"
                  value={idpEntityId}
                  onChange={(e) => setIdpEntityId(e.target.value)}
                  placeholder="https://idp.example.com"
                />
              </div>
              <div>
                <Label htmlFor="saml-sp-entity">SP Entity ID</Label>
                <Input
                  id="saml-sp-entity"
                  value={spEntityId}
                  onChange={(e) => setSpEntityId(e.target.value)}
                  placeholder="https://myapp.example.com"
                />
              </div>
              <div>
                <Label htmlFor="saml-acs-url">SP ACS URL</Label>
                <Input
                  id="saml-acs-url"
                  value={spAcsUrl}
                  onChange={(e) => setSpAcsUrl(e.target.value)}
                  placeholder="https://myapp.example.com/api/v1/identity/sso/saml/acs"
                />
              </div>
            </>
          )}

          {/* OIDC Config Fields */}
          {providerType === "oidc" && (
            <>
              <div>
                <Label htmlFor="oidc-issuer">Issuer URL</Label>
                <Input
                  id="oidc-issuer"
                  value={issuerUrl}
                  onChange={(e) => setIssuerUrl(e.target.value)}
                  placeholder="https://accounts.google.com"
                />
              </div>
              <div>
                <Label htmlFor="oidc-client-id">Client ID</Label>
                <Input
                  id="oidc-client-id"
                  value={clientId}
                  onChange={(e) => setClientId(e.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="oidc-client-secret">
                  Client Secret{" "}
                  {mode === "edit" && (
                    <span className="text-muted-foreground font-normal">
                      (leave blank to keep current)
                    </span>
                  )}
                </Label>
                <Input
                  id="oidc-client-secret"
                  type="password"
                  value={clientSecret}
                  onChange={(e) => setClientSecret(e.target.value)}
                  placeholder={mode === "edit" ? "********" : ""}
                />
              </div>
              <div>
                <Label htmlFor="oidc-redirect-uri">Redirect URI</Label>
                <Input
                  id="oidc-redirect-uri"
                  value={redirectUri}
                  onChange={(e) => setRedirectUri(e.target.value)}
                  placeholder="https://myapp.example.com/api/v1/identity/sso/oidc/callback"
                />
              </div>
              <div>
                <Label htmlFor="oidc-scopes">Scopes (comma-separated)</Label>
                <Input
                  id="oidc-scopes"
                  value={scopes}
                  onChange={(e) => setScopes(e.target.value)}
                  placeholder="openid,profile,email"
                />
              </div>
            </>
          )}

          {error && <p className="text-sm text-destructive">{error}</p>}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending
                ? "Saving..."
                : mode === "create"
                  ? "Create"
                  : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
