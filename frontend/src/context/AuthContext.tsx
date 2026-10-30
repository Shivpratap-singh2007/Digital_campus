import React, { createContext, useContext, useState, useEffect } from 'react';
import { api, clearCsrfToken, fetchCsrfToken } from '../api/client';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: 'user' | 'handler' | 'admin';
  is_verified: boolean;
  is_handler: boolean;
  is_admin: boolean;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (fullName: string, email: string, password: string) => Promise<any>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const refreshUser = async () => {
    try {
      const data = await api.get('/api/auth/me');
      if (data.authenticated && data.user) {
        setUser(data.user);
      } else {
        setUser(null);
      }
    } catch (err) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshUser();
  }, []);

  const login = async (email: string, password: string): Promise<User> => {
    // Ensure fresh token bootstrap before sending credentials
    await fetchCsrfToken();
    const data = await api.post('/api/auth/login', { email, password });
    // Invalidate pre-auth token on successful login
    clearCsrfToken();
    setUser(data.user);
    return data.user;
  };

  const register = async (fullName: string, email: string, password: string): Promise<any> => {
    await fetchCsrfToken();
    const data = await api.post('/api/auth/register', {
      full_name: fullName,
      email,
      password,
    });
    return data;
  };

  const logout = async (): Promise<void> => {
    try {
      await api.post('/api/auth/logout');
    } finally {
      // Invalidate frontend token on session termination
      clearCsrfToken();
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

