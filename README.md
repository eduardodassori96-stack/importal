# Pascalle Store — Plataforma Web v1.0

## Requisitos
- Python 3.8+
- PyJWT y bcrypt (pip install -r requirements.txt)

## Instalación y ejecución local

```bash
pip install -r requirements.txt
python3 server.py
```

Abre http://localhost:8000 en tu navegador.

**Admin por defecto:** admin@pascallestore.cl / admin123

## Estructura
```
pascalle-store/
├── server.py           ← Servidor web Python
├── database.py         ← Base de datos SQLite
├── auth_utils.py       ← Autenticación JWT + bcrypt
├── requirements.txt
├── data/               ← Base de datos SQLite (se crea automáticamente)
├── static/
│   ├── css/styles.css  ← Estilos compartidos
│   ├── js/             ← Scripts JS compartidos
│   └── uploads/        ← Archivos subidos
└── templates/          ← Páginas HTML
    ├── landing.html    ← Página pública
    ├── login.html
    ├── registro.html
    ├── dashboard.html  ← Portal cliente
    ├── cargas.html
    ├── pagos.html
    ├── tracking.html
    ├── perfil.html
    ├── admin.html      ← Panel admin
    ├── admin_cargas.html
    ├── admin_cobros.html
    ├── admin_clientes.html
    └── admin_conciliacion.html

## Deploy en Railway
1. Crea cuenta en railway.app
2. Nuevo proyecto → Deploy from GitHub
3. Agrega variable PORT=8000 (o Railway la configura sola)
4. Listo!
```
