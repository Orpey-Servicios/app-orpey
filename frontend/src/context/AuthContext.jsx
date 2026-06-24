import { createContext, useContext, useState, useEffect } from 'react';
import { iniciarSesion as apiLogin, verificarToken } from '../api/orpey-api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    if (token) {
      verificarToken(token)
        .then(data => {
          setUsuario(data);
          localStorage.setItem('token', token);
        })
        .catch(() => {
          setToken(null);
          setUsuario(null);
          localStorage.removeItem('token');
        })
        .finally(() => setCargando(false));
    } else {
      setCargando(false);
    }
  }, []);

  const login = async (username, password) => {
    const data = await apiLogin(username, password);
    setToken(data.access_token);
    setUsuario(data.usuario);
    localStorage.setItem('token', data.access_token);
    return data;
  };

  const logout = () => {
    setToken(null);
    setUsuario(null);
    localStorage.removeItem('token');
  };

  return (
    <AuthContext.Provider value={{ usuario, token, login, logout, cargando }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth debe usarse dentro de AuthProvider');
  }
  return context;
}

export default AuthContext;
