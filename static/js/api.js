/**
 * Importal — API helper
 * Todas las peticiones API van por aquí
 */

const API = {
  _token() { return sessionStorage.getItem('auth_token') || ''; },
  _headers(extra) {
    const h = { ...(extra || {}) };
    const t = this._token();
    if (t) h['Authorization'] = 'Bearer ' + t;
    return h;
  },
  async get(path) {
    const res = await fetch(path, { credentials: 'include', headers: this._headers() });
    if (res.status === 401) { sessionStorage.clear(); window.location.href = '/login'; return null; }
    return res.json();
  },
  async post(path, data) {
    const res = await fetch(path, {
      method: 'POST',
      headers: this._headers({ 'Content-Type': 'application/json' }),
      credentials: 'include',
      body: JSON.stringify(data)
    });
    return { ok: res.ok, status: res.status, data: await res.json() };
  },
  fmt: {
    clp(n) { return '$' + Math.round(n || 0).toLocaleString('es-CL'); },
    date(s) { if (!s) return '—'; return new Date(s).toLocaleDateString('es-CL', { day:'2-digit', month:'short', year:'numeric' }); },
    datetime(s) { if (!s) return '—'; return new Date(s).toLocaleString('es-CL', { day:'2-digit', month:'short', hour:'2-digit', minute:'2-digit' }); },
    usd(n) { return 'US$' + (n || 0).toLocaleString('en-US', { minimumFractionDigits:2, maximumFractionDigits:2 }); },
    kg(n) { return (n || 0).toFixed(2) + ' kg'; },
    status: {
      PENDING: { label:'Pendiente', cls:'badge-pending' },
      PAID:    { label:'Pagado',    cls:'badge-paid' },
      OVERDUE: { label:'Vencido',   cls:'badge-overdue' },
      MORA_1:  { label:'Mora 5%',   cls:'badge-overdue' },
      MORA_2:  { label:'Mora 10%',  cls:'badge-overdue' },
      OPEN:    { label:'Abierta',   cls:'badge-open' },
      CLOSED:  { label:'Cerrada',   cls:'badge-closed' },
      IN_TRANSIT: { label:'En tránsito', cls:'badge-transit' },
      ORDERED: { label:'Ordenado',  cls:'badge-transit' },
      IN_WAREHOUSE_US: { label:'Bodega USA', cls:'badge-transit' },
      IN_FLIGHT: { label:'En vuelo', cls:'badge-transit' },
      IN_CUSTOMS: { label:'Aduana', cls:'badge-transit' },
      IN_WAREHOUSE_CL: { label:'Bodega Chile', cls:'badge-transit' },
      DELIVERED: { label:'Entregado', cls:'badge-paid' },
    }
  }
};
