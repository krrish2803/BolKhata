import React, { createContext, useContext, useState, useEffect } from 'react';

export interface User {
  id?: string;
  name: string;
  whatsAppNumber: string;
  shopName: string;
  shopType: string;
  workspaceId?: string;
  isDemo?: boolean;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  login: (whatsAppNumber: string, pin: string) => Promise<{ success: boolean; error?: string }>;
  signup: (userData: { name: string; whatsAppNumber: string; shopName: string; shopType: string; pin: string }) => Promise<{ success: boolean; error?: string }>;
  startDemoSession: () => Promise<{ success: boolean; error?: string }>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const AUTH_STORAGE_KEY = 'bolkhata_auth_user';

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    // Check active session with backend /api/auth/me or saved local user
    const checkActiveSession = async () => {
      try {
        const res = await fetch('/api/auth/me', { credentials: 'include' });
        if (res.ok) {
          const profile = await res.json();
          if (profile) {
            setUser(profile);
            localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(profile));
            return;
          }
        }
      } catch (err) {
        console.warn('Could not verify server session profile:', err);
      }

      const saved = localStorage.getItem(AUTH_STORAGE_KEY);
      if (saved) {
        try {
          setUser(JSON.parse(saved));
        } catch {
          localStorage.removeItem(AUTH_STORAGE_KEY);
        }
      }
    };

    checkActiveSession();
  }, []);

  const startDemoSession = async (): Promise<{ success: boolean; error?: string }> => {
    try {
      const res = await fetch('/api/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        return { success: false, error: err.detail || 'Failed to start demo workspace' };
      }
      const data = await res.json();
      const demoUser: User = {
        name: 'Demo Visitor',
        whatsAppNumber: '+91 9876543210',
        shopName: 'Demo Khata Store',
        shopType: 'Clothing & Garments',
        workspaceId: data.workspaceId,
        isDemo: true,
      };
      setUser(demoUser);
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(demoUser));
      return { success: true };
    } catch (e: any) {
      return { success: false, error: e.message || 'Error connecting to demo server' };
    }
  };

  const login = async (whatsAppNumber: string, pin: string): Promise<{ success: boolean; error?: string }> => {
    const cleanPhone = whatsAppNumber.replace(/\D/g, '');
    if (cleanPhone.length < 10) {
      return { success: false, error: 'Please enter a valid 10-digit WhatsApp number' };
    }
    if (!pin || pin.length < 4) {
      return { success: false, error: 'Please enter your 4-digit PIN' };
    }

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ phone: cleanPhone.slice(-10), pin }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        return { success: false, error: err.detail || 'Sign-in failed. Please verify credentials.' };
      }

      const loggedUser = await res.json();
      setUser(loggedUser);
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(loggedUser));
      return { success: true };
    } catch (e: any) {
      return { success: false, error: e.message || 'Error connecting to auth service' };
    }
  };

  const signup = async (userData: {
    name: string;
    whatsAppNumber: string;
    shopName: string;
    shopType: string;
    pin: string;
  }): Promise<{ success: boolean; error?: string }> => {
    const cleanPhone = userData.whatsAppNumber.replace(/\D/g, '');
    if (!userData.name.trim()) {
      return { success: false, error: 'Please enter your name' };
    }
    if (cleanPhone.length < 10) {
      return { success: false, error: 'Please enter a valid 10-digit WhatsApp number for sending receipts' };
    }
    if (!userData.shopName.trim()) {
      return { success: false, error: 'Please enter your shop or business name' };
    }
    if (!userData.pin || userData.pin.length !== 4) {
      return { success: false, error: 'Please enter a 4-digit PIN' };
    }

    try {
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          name: userData.name.trim(),
          phone: cleanPhone.slice(-10),
          shopName: userData.shopName.trim(),
          shopType: userData.shopType || 'Kirana / General Store',
          pin: userData.pin,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        return { success: false, error: err.detail || 'Failed to create account.' };
      }

      const newUser = await res.json();
      setUser(newUser);
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(newUser));
      return { success: true };
    } catch (e: any) {
      return { success: false, error: e.message || 'Error connecting to registration service' };
    }
  };

  const logout = async () => {
    try {
      await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
    } catch {}
    setUser(null);
    localStorage.removeItem(AUTH_STORAGE_KEY);
  };

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, login, signup, startDemoSession, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

