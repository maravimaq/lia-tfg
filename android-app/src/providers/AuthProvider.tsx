import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { storage } from "@/src/lib/storage";
import { authService } from "@/src/services/auth";
import { userService } from "@/src/services/user";
import { LoginPayload, RegisterPayload } from "@/src/types/auth";
import { UserResponse } from "@/src/types/user";

type AuthContextType = {
  user: UserResponse | null;
  token: string | null;
  loading: boolean;
  signIn: (payload: LoginPayload) => Promise<void>;
  signUp: (payload: RegisterPayload) => Promise<void>;
  signOut: () => Promise<void>;
  refreshProfile: () => Promise<void>;
  setUser: React.Dispatch<React.SetStateAction<UserResponse | null>>;
};

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshProfile = async () => {
    const profile = await userService.getMe();
    setUser(profile);
  };

  const bootstrap = async () => {
    try {
      const storedToken = await storage.getToken();

      if (!storedToken) {
        setLoading(false);
        return;
      }

      setToken(storedToken);
      await refreshProfile();
    } catch (error) {
      console.log("Bootstrap auth error:", error);
      await storage.removeToken();
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    bootstrap();
  }, []);

  const signIn = async (payload: LoginPayload) => {
    const result = await authService.login(payload);

    await storage.setToken(result.access_token);
    setToken(result.access_token);

    await refreshProfile();
  };

  const signUp = async (payload: RegisterPayload) => {
    await authService.register(payload);

    await signIn({
      email: payload.email,
      contrasena: payload.contrasena,
    });
  };

  const signOut = async () => {
    const currentToken = token;

    await storage.removeToken();
    setToken(null);
    setUser(null);

    if (currentToken) {
      try {
        await authService.logout();
      } catch (error) {
        console.log("Logout warning:", error);
      }
    }
  };

  const value = useMemo(
    () => ({
      user,
      token,
      loading,
      signIn,
      signUp,
      signOut,
      refreshProfile,
      setUser,
    }),
    [user, token, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuthContext() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuthContext debe usarse dentro de AuthProvider");
  }

  return context;
}