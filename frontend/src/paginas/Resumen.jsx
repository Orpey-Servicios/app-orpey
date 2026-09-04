import { useState, useEffect, useMemo } from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line
} from 'recharts';
import { 
  PieChart as PieChartIcon, Activity, DollarSign, Wrench, Wallet, Calendar, Filter, TrendingUp
} from 'lucide-react';
import { obtenerOrdenes } from '../api/orpey-api';
import { 
  startOfMonth, endOfMonth, startOfWeek, endOfWeek, 
  startOfYear, endOfYear, isWithinInterval, parseISO, format 
} from 'date-fns';
import { es } from 'date-fns/locale';
import './Resumen.css';

const COLORES = ['#3B82F6', '#8B5CF6', '#F59E0B', '#10B981', '#EF4444', '#06B6D4', '#EC4899'];

const PERIODOS = [
  { valor: 'mes_actual', etiqueta: 'Este Mes' },
  { valor: 'semana_actual', etiqueta: 'Esta Semana' },
  { valor: 'anio_actual', etiqueta: 'Este Año' },
  { valor: 'todo', etiqueta: 'Historico Completo' }
];

export default function Resumen() {
  const [ordenes, setOrdenes] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [periodo, setPeriodo] = useState('todo');
  const [estadoCSS, setEstadoCSS] = useState({ dark: false });

  useEffect(() => {
    // Detectar si está en modo oscuro para los colores de los charts
    const observer = new MutationObserver(() => {
      setEstadoCSS({ dark: document.body.classList.contains('dark-theme') });
    });
    observer.observe(document.body, { attributes: true, attributeFilter: ['class'] });
    setEstadoCSS({ dark: document.body.classList.contains('dark-theme') });
    
    cargarDatos();
    return () => observer.disconnect();
  }, []);

  async function cargarDatos() {
    try {
      setCargando(true);
      const data = await obtenerOrdenes();
      setOrdenes(data);
    } catch (err) {
      console.error(err);
    } finally {
      setCargando(false);
    }
  }

  // Filtrar órdenes según periodo seleccionado
  const ordenesFiltradas = useMemo(() => {
    const ahora = new Date();
    let inicio, fin;

    switch (periodo) {
      case 'mes_actual':
        inicio = startOfMonth(ahora);
        fin = endOfMonth(ahora);
        break;
      case 'semana_actual':
        inicio = startOfWeek(ahora, { weekStartsOn: 1 });
        fin = endOfWeek(ahora, { weekStartsOn: 1 });
        break;
      case 'anio_actual':
        inicio = startOfYear(ahora);
        fin = endOfYear(ahora);
        break;
      default:
        return ordenes; // Todo el histórico
    }

    return ordenes.filter(o => {
      const fecha = parseISO(o.fecha_ingreso);
      return isWithinInterval(fecha, { start: inicio, end: fin });
    });
  }, [ordenes, periodo]);

  // CALCULO DE MÉTRICAS GLOBALES
  const metricas = useMemo(() => {
    let ingresosTotales = 0;
    let abonosTotales = 0;
    let porCobrar = 0;
    let ordenesExitosas = 0;
    let ordenesCanceladas = 0;

    ordenesFiltradas.forEach(o => {
      if (o.estado === 'cancelada') {
        ordenesCanceladas++;
        return; // No sumar finanzas de canceladas
      }
      
      const total = Number(o.total_orden) || 0;
      const abono = Number(o.abono) || 0;
      
      if (['terminada', 'entregada'].includes(o.estado)) {
        ingresosTotales += total;
        ordenesExitosas++;
      } else {
        abonosTotales += abono;
        porCobrar += (total - abono);
      }
    });

    return { ingresosTotales, abonosTotales, porCobrar, ordenesExitosas, ordenesCanceladas, totalOrdenes: ordenesFiltradas.length };
  }, [ordenesFiltradas]);

  // DATOS PARA GRAFICOS
  const datosEquipos = useMemo(() => {
    const conteo = {};
    ordenesFiltradas.forEach(o => {
      if (o.estado === 'cancelada') return;
      (o.equipos || []).forEach(eq => {
        const tipo = eq.tipo_equipo || 'otro';
        conteo[tipo] = (conteo[tipo] || 0) + 1;
      });
    });
    return Object.entries(conteo).map(([name, value]) => ({ name: name.toUpperCase(), value })).sort((a,b) => b.value - a.value);
  }, [ordenesFiltradas]);

  const datosFinancierosDias = useMemo(() => {
    const agrupado = {};
    ordenesFiltradas.forEach(o => {
      if (o.estado === 'cancelada') return;
      const dia = format(parseISO(o.fecha_ingreso), 'dd MMM', { locale: es });
      if (!agrupado[dia]) agrupado[dia] = { dia, Ingresos: 0, Abonos: 0 };
      
      const total = Number(o.total_orden) || 0;
      const abono = Number(o.abono) || 0;
      
      if (['terminada', 'entregada'].includes(o.estado)) {
        agrupado[dia].Ingresos += total;
      } else {
        agrupado[dia].Abonos += abono;
      }
    });
    return Object.values(agrupado).sort((a, b) => a.dia.localeCompare(b.dia));
  }, [ordenesFiltradas]);

  const datosFinancierosMeses = useMemo(() => {
    const agrupado = {};
    ordenesFiltradas.forEach(o => {
      if (o.estado === 'cancelada') return;
      const key = format(parseISO(o.fecha_ingreso), 'yyyy-MM');
      const mesLabel = format(parseISO(o.fecha_ingreso), 'MMM yyyy', { locale: es });
      
      if (!agrupado[key]) agrupado[key] = { key, mes: mesLabel.toUpperCase(), Ingresos: 0 };
      
      const total = Number(o.total_orden) || 0;
      if (['terminada', 'entregada'].includes(o.estado)) {
        agrupado[key].Ingresos += total;
      }
    });
    
    return Object.values(agrupado).sort((a, b) => a.key.localeCompare(b.key));
  }, [ordenesFiltradas]);

  const datosMarcas = useMemo(() => {
    const conteo = {};
    ordenesFiltradas.forEach(o => {
      if (o.estado === 'cancelada') return;
      (o.equipos || []).forEach(eq => {
        if (!eq.marca) return;
        const m = eq.marca.toUpperCase();
        conteo[m] = (conteo[m] || 0) + 1;
      });
    });
    return Object.entries(conteo)
      .map(([name, value]) => ({ name, value }))
      .sort((a,b) => b.value - a.value)
      .slice(0, 5); // Top 5
  }, [ordenesFiltradas]);

  const colorTexto = estadoCSS.dark ? '#E5E7EB' : '#374151';
  const colorLinea = estadoCSS.dark ? '#374151' : '#E5E7EB';

  if (cargando) return <div className="dashboard__cargando"><div className="spinner"/></div>;

  return (
    <div className="resumen-pagina animar-entrada">
      <div className="resumen-header">
        <h2><PieChartIcon size={24} /> Reportes Financieros y Estadísticas</h2>
        <div className="resumen-filtros">
          <label style={{ fontSize: '13px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Calendar size={16} /> Periodo:
          </label>
          <select 
            className="campo-texto" 
            value={periodo} 
            onChange={e => setPeriodo(e.target.value)}
            style={{ minWidth: '150px' }}
          >
            {PERIODOS.map(p => <option key={p.valor} value={p.valor}>{p.etiqueta}</option>)}
          </select>
        </div>
      </div>

      {/* TARJETAS KPI */}
      <div className="resumen-grid">
        <div className="resumen-tarjeta">
          <div className="resumen-tarjeta__icono" style={{ background: '#ECFEFF', color: '#06B6D4' }}><DollarSign size={24} /></div>
          <div className="resumen-tarjeta__info">
            <span className="resumen-tarjeta__valor">${metricas.ingresosTotales.toFixed(2)}</span>
            <span className="resumen-tarjeta__titulo">Facturación Trabajos Terminados</span>
          </div>
        </div>
        <div className="resumen-tarjeta">
          <div className="resumen-tarjeta__icono" style={{ background: '#F0FDF4', color: '#22C55E' }}><Wallet size={24} /></div>
          <div className="resumen-tarjeta__info">
            <span className="resumen-tarjeta__valor">${metricas.abonosTotales.toFixed(2)}</span>
            <span className="resumen-tarjeta__titulo">Abonos Recaudados (Pendientes)</span>
          </div>
        </div>
        <div className="resumen-tarjeta">
          <div className="resumen-tarjeta__icono" style={{ background: '#FFF7ED', color: '#F97316' }}><Activity size={24} /></div>
          <div className="resumen-tarjeta__info">
            <span className="resumen-tarjeta__valor">${metricas.porCobrar.toFixed(2)}</span>
            <span className="resumen-tarjeta__titulo">Saldo por Cobrar Estimado</span>
          </div>
        </div>
        <div className="resumen-tarjeta">
          <div className="resumen-tarjeta__icono" style={{ background: '#EFF6FF', color: '#3B82F6' }}><Wrench size={24} /></div>
          <div className="resumen-tarjeta__info">
            <span className="resumen-tarjeta__valor">{metricas.totalOrdenes}</span>
            <span className="resumen-tarjeta__titulo">Órdenes Atendidas</span>
          </div>
        </div>
      </div>

      {/* GRAFICOS */}
      <div className="resumen-charts">
        
        {/* GRÁFICO MENSUAL DE CRECIMIENTO */}
        <div className="chart-container" style={{ gridColumn: '1 / -1' }}>
          <h3><TrendingUp size={18} /> Crecimiento de Facturación por Mes</h3>
          <div className="chart-wrapper">
            {datosFinancierosMeses.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={datosFinancierosMeses}>
                  <CartesianGrid strokeDasharray="3 3" stroke={colorLinea} vertical={false} />
                  <XAxis dataKey="mes" stroke={colorTexto} fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis stroke={colorTexto} fontSize={12} tickLine={false} axisLine={false} tickFormatter={v => `$${v}`} />
                  <RechartsTooltip 
                    cursor={{fill: 'var(--color-primario-sutil)'}}
                    contentStyle={{ background: 'var(--fondo-principal)', border: '1px solid var(--borde-color)', borderRadius: '8px' }}
                    itemStyle={{ color: 'var(--color-oscuro)' }}
                  />
                  <Bar dataKey="Ingresos" fill="#3B82F6" radius={[4, 4, 0, 0]} barSize={40}>
                    {datosFinancierosMeses.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORES[index % COLORES.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : <p style={{textAlign: 'center', color: 'var(--texto-secundario)', paddingTop: '100px'}}>No hay datos para este periodo</p>}
          </div>
        </div>

        <div className="chart-container">
          <h3><TrendingUp size={18} /> Flujo de Ingresos Diarios</h3>
          <div className="chart-wrapper">
            {datosFinancierosDias.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={datosFinancierosDias}>
                  <CartesianGrid strokeDasharray="3 3" stroke={colorLinea} vertical={false} />
                  <XAxis dataKey="dia" stroke={colorTexto} fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis stroke={colorTexto} fontSize={12} tickLine={false} axisLine={false} tickFormatter={v => `$${v}`} />
                  <RechartsTooltip 
                    contentStyle={{ background: 'var(--fondo-principal)', border: '1px solid var(--borde-color)', borderRadius: '8px' }}
                    itemStyle={{ color: 'var(--color-oscuro)' }}
                  />
                  <Legend />
                  <Line type="monotone" dataKey="Ingresos" stroke="#06B6D4" strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                  <Line type="monotone" dataKey="Abonos" stroke="#22C55E" strokeWidth={3} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : <p style={{textAlign: 'center', color: 'var(--texto-secundario)', paddingTop: '100px'}}>No hay datos para este periodo</p>}
          </div>
        </div>

        <div className="chart-container">
          <h3><PieChartIcon size={18} /> Equipos Atendidos</h3>
          <div className="chart-wrapper">
            {datosEquipos.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={datosEquipos}
                    cx="50%" cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={5}
                    dataKey="value"
                    label={({name, percent}) => `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    {datosEquipos.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORES[index % COLORES.length]} />
                    ))}
                  </Pie>
                  <RechartsTooltip 
                    contentStyle={{ background: 'var(--fondo-principal)', border: '1px solid var(--borde-color)', borderRadius: '8px' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : <p style={{textAlign: 'center', color: 'var(--texto-secundario)', paddingTop: '100px'}}>No hay datos</p>}
          </div>
        </div>

        <div className="chart-container">
          <h3><Activity size={18} /> Top 5 Marcas Atendidas</h3>
          <div className="chart-wrapper">
            {datosMarcas.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={datosMarcas} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={colorLinea} horizontal={true} vertical={false} />
                  <XAxis type="number" stroke={colorTexto} fontSize={12} hide />
                  <YAxis dataKey="name" type="category" stroke={colorTexto} fontSize={12} axisLine={false} tickLine={false} width={80} />
                  <RechartsTooltip 
                    cursor={{fill: 'var(--color-primario-sutil)'}}
                    contentStyle={{ background: 'var(--fondo-principal)', border: '1px solid var(--borde-color)', borderRadius: '8px' }}
                  />
                  <Bar dataKey="value" fill="#8B5CF6" radius={[0, 4, 4, 0]}>
                    {datosMarcas.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORES[(index + 2) % COLORES.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : <p style={{textAlign: 'center', color: 'var(--texto-secundario)', paddingTop: '100px'}}>No hay datos</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
