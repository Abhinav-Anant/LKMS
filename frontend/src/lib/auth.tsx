import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { api, tokens } from "./api";
import type { Me } from "./types";

export interface TokenPair {
  access: string;
  refresh: string;
  user: Me;
}

interface AuthState {
  user: Me | null;
  loading: boolean;
  signIn: (username: string, password: string) => Promise<Me>;
  /** Parent sign-in: store the tokens returned by /auth/parent/verify-code/. */
  acceptTokens: (data: TokenPair) => Me;
  /** Re-read the signed-in user, e.g. after changing the password. */
  reload: () => Promise<void>;
  signOut: () => Promise<void>;
  can: (capability: string) => boolean;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    tokens.onSignedOut(() => setUser(null));
    if (!tokens.hasRefresh()) {
      setLoading(false);
      return;
    }
    api
      .refreshAccess()
      .then((ok) => (ok ? api.get<Me>("/auth/me/") : null))
      .then((me) => setUser(me))
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  const signIn = useCallback(async (username: string, password: string) => {
    const data = await api.post<TokenPair>(
      "/auth/login/",
      { username, password },
      { auth: false },
    );
    tokens.set(data.access, data.refresh);
    setUser(data.user);
    return data.user;
  }, []);

  const acceptTokens = useCallback((data: TokenPair) => {
    tokens.set(data.access, data.refresh);
    setUser(data.user);
    return data.user;
  }, []);

  const reload = useCallback(async () => {
    setUser(await api.get<Me>("/auth/me/"));
  }, []);

  const signOut = useCallback(async () => {
    const refresh = tokens.refresh();
    try {
      if (refresh) await api.post("/auth/logout/", { refresh });
    } finally {
      tokens.clear();
      setUser(null);
    }
  }, []);

  const value = useMemo<AuthState>(
    () => ({ user, loading, signIn, acceptTokens, reload, signOut, can: (c) => Boolean(user?.capabilities.includes(c)) }),
    [user, loading, signIn, acceptTokens, reload, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
