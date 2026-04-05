/**
 * Importal — Shared layout Alpine.js component
 */
function layoutApp(pageName) {
  return {
    page: pageName,
    user: null,
    sidebarOpen: false,
    async init() {
      const me = await API.get('/api/me');
      if (me) this.user = me;
    },
    nav: [
      { key:'dashboard',  label:'Inicio',       icon:'🏠', href:'/dashboard' },
      { key:'cargas',     label:'Mis cargas',   icon:'📦', href:'/dashboard/cargas' },
      { key:'pagos',      label:'Pagos',        icon:'💳', href:'/dashboard/pagos' },
      { key:'tracking',   label:'Tracking',     icon:'🗺️', href:'/dashboard/tracking' },
      { key:'perfil',     label:'Mi perfil',    icon:'👤', href:'/dashboard/perfil' },
    ],
    logout() { window.location.href = '/logout'; }
  }
}
