/**
 * Importal — Admin layout Alpine.js component
 */
function adminLayout(pageName) {
  return {
    page: pageName,
    user: null,
    sidebarOpen: false,
    async init() {
      if (!sessionStorage.getItem('auth_token')) { window.location.href = '/login'; return; }
      const me = await API.get('/api/me');
      if (me) this.user = me;
    },
    nav: [
      { key:'admin',         label:'Dashboard',    icon:'📊', href:'/admin' },
      { key:'admin_cargas',  label:'Cargas',       icon:'📦', href:'/admin/cargas' },
      { key:'admin_cobros',  label:'Cobros',       icon:'🧾', href:'/admin/cobros' },
      { key:'admin_clientes',label:'Clientes',     icon:'👥', href:'/admin/clientes' },
      { key:'admin_concil',  label:'Conciliación', icon:'🏦', href:'/admin/conciliacion' },
    ],
    logout() { window.location.href = '/logout'; }
  }
}
