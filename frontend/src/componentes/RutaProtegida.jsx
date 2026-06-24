import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function RutaProtegida({ children }) {
  const { usuario, cargando } = useAuth();

  if (cargando) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        height: '100vh', background: 'var(--fondo-principal)'
      }}>
        <div className="spinner" />
      </div>
    );
  }

  if (!usuario) {
    return <Navigate to="/login" replace />;
  }

  return children;
}
