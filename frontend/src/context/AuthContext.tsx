import React, { createContext, useContext, useState } from 'react';

export type UserRole = 'Admin' | 'Viewer';

export interface User {
  username: string;
  role: UserRole;
}

interface AuthContextType {
  user: User | null;
  login: (username: string, role: UserRole) => void;
  logout: () => void;
  isAdmin: boolean;
  isViewer: boolean;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('discovery_auth_user');
    return saved ? JSON.parse(saved) : null;
  });

  const login = (username: string, role: UserRole) => {
    const newUser = { username, role };
    setUser(newUser);
    localStorage.setItem('discovery_auth_user', JSON.stringify(newUser));
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('discovery_auth_user');
  };

  const isAdmin = user?.role === 'Admin';
  const isViewer = user?.role === 'Viewer';
  const isAuthenticated = !!user;

  return (
    <AuthContext.Provider value={{ user, login, logout, isAdmin, isViewer, isAuthenticated }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
