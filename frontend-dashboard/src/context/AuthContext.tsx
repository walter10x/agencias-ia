import { createContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { login as apiLogin, register as apiRegister, fetchMe, type CurrentClientResponse, type RegisterData, type RegisterResponse } from "@/api/auth";

interface AuthContextType {
  user: CurrentClientResponse | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterData) => Promise<RegisterResponse>;
  logout: () => void;
}

// eslint-disable-next-line react-refresh/only-export-components
export const AuthContext = createContext<AuthContextType>({
  user: null,
  isLoading: true,
  isAuthenticated: false,
  login: async () => {},
  register: async () => ({ client_id: "", email: "", status: "", message: "" }),
  logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentClientResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  const isAuthenticated = user !== null;

  useEffect(() => {
    const token = localStorage.getItem("auth_token");
    const promise = token ? fetchMe().then(setUser) : Promise.resolve();
    promise
      .catch(() => {
        localStorage.removeItem("auth_token");
        setUser(null);
      })
      .finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await apiLogin(email, password);
    localStorage.setItem("auth_token", res.access_token);
    const profile = await fetchMe();
    setUser(profile);
  }, []);

  const registerFn = useCallback(async (data: RegisterData) => {
    return apiRegister(data);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("auth_token");
    setUser(null);
    navigate("/login");
  }, [navigate]);

  return (
    <AuthContext.Provider value={{ user, isLoading, isAuthenticated, login, register: registerFn, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
