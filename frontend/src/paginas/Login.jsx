import { useState } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import { LogIn, AlertCircle, Eye, EyeOff } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import './Login.css';

export default function Login() {
  const { login, usuario } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: '', password: '' });
  const [error, setError] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [verPassword, setVerPassword] = useState(false);

  if (usuario) {
    return <Navigate to="/" replace />;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.username.trim() || !form.password.trim()) {
      setError('Todos los campos son obligatorios');
      return;
    }
    try {
      setCargando(true);
      setError(null);
      await login(form.username.trim(), form.password);
      navigate('/', { replace: true });
    } catch (err) {
      setError(err.message || 'Error al iniciar sesión');
    } finally {
      setCargando(false);
    }
  }

  return (
    <div className="login-pagina">
      <div className="login-tarjeta">
        <div className="login-tarjeta__logo">
          <img src={localStorage.getItem('orpey_custom_logo') || "/logo-orpey.png"} alt="Orpey Servicios" />
        </div>
        <h1 className="login-tarjeta__titulo">Iniciar Sesión</h1>
        <p className="login-tarjeta__subtitulo">Ingresa tus credenciales para acceder</p>

        {error && (
          <div className="login-error">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="campo-grupo">
            <label className="campo-label">Usuario</label>
            <input
              type="text"
              className="campo-texto"
              placeholder="Tu nombre de usuario"
              value={form.username}
              onChange={e => setForm(p => ({ ...p, username: e.target.value }))}
              autoFocus
              autoComplete="username"
            />
          </div>
          <div className="campo-grupo">
            <label className="campo-label">Contraseña</label>
            <div style={{ position: 'relative' }}>
              <input
                type={verPassword ? 'text' : 'password'}
                className="campo-texto"
                placeholder="Tu contraseña"
                value={form.password}
                onChange={e => setForm(p => ({ ...p, password: e.target.value }))}
                autoComplete="current-password"
                style={{ paddingRight: 40 }}
              />
              <button
                type="button"
                onClick={() => setVerPassword(!verPassword)}
                style={{
                  position: 'absolute', right: 10, top: '50%',
                  transform: 'translateY(-50%)', color: 'var(--texto-terciario)',
                  display: 'flex', padding: 4
                }}
              >
                {verPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>
          <button
            type="submit"
            className="boton-primario login-tarjeta__boton"
            disabled={cargando}
          >
            {cargando ? (
              <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} /> Ingresando...
              </span>
            ) : (
              <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <LogIn size={18} /> Iniciar Sesión
              </span>
            )}
          </button>
        </form>

        <div className="login-tarjeta__footer">
          <strong>Orpey Servicios</strong> &mdash; Sistema de Gestión
        </div>
      </div>
    </div>
  );
}
