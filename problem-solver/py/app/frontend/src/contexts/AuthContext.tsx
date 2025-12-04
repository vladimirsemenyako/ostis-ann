import React, { createContext, useContext, useState, useEffect } from 'react';

interface AuthContextType {
  isAuthenticated: boolean;
  tokens: TokenResponse | null;
  login: () => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [tokens, setTokens] = useState<TokenResponse | null>(() => {
    try {
      return JSON.parse(sessionStorage.getItem('kc_tokens') || 'null');
    } catch {
      return null;
    }
  });

  const isAuthenticated = !!tokens?.access_token;

  useEffect(() => {
    if (tokens?.access_token) {
    }
  }, [tokens]);

  const login = () => {
    startLogin();
  };

  const logout = () => {
    sessionStorage.removeItem('kc_tokens');
    setTokens(null);
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, tokens, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
}