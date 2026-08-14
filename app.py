import os
from flask import Flask, request, redirect, session, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import create_engine, text

app=Flask(__name__)
app.secret_key=os.getenv("SECRET_KEY","CAMBIAR-ESTA-CLAVE")
url=os.getenv("DATABASE_URL","sqlite:///bigconta.db")
if url.startswith("postgres://"): url=url.replace("postgres://","postgresql://",1)
engine=create_engine(url,pool_pre_ping=True)

with engine.begin() as db:
    db.execute(text("""CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT, username VARCHAR(80) UNIQUE NOT NULL,
    full_name VARCHAR(150) NOT NULL, password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(30) NOT NULL DEFAULT 'empleado', active BOOLEAN NOT NULL DEFAULT TRUE)"""))
    if not db.execute(text("SELECT id FROM users WHERE username='admin'")).first():
        db.execute(text("""INSERT INTO users(username,full_name,password_hash,role,active)
        VALUES(:u,:n,:p,'admin',TRUE)"""),
        {"u":"admin","n":"Administrador BIGCONTA","p":generate_password_hash("Admin123!")})

STYLE="""<style>*{box-sizing:border-box}body{margin:0;font-family:Arial;background:#f4f6f8;color:#17202a}
.top{background:#111827;color:#fff;padding:16px 24px;display:flex;justify-content:space-between}
.wrap{display:flex;min-height:calc(100vh - 58px)}nav{width:235px;background:#1f2937;padding:16px}
nav a{display:block;color:#e5e7eb;text-decoration:none;padding:10px;border-radius:7px;margin:3px 0}
nav a:hover{background:#374151}main{padding:28px;flex:1}.card{background:#fff;border-radius:12px;padding:22px;margin-bottom:18px;box-shadow:0 2px 10px #0001}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px}.kpi{font-size:28px;font-weight:bold}
input,select{display:block;width:100%;max-width:430px;padding:11px;margin:8px 0;border:1px solid #d1d5db;border-radius:7px}
button{background:#111827;color:#fff;border:0;border-radius:7px;padding:11px 16px;cursor:pointer}
.login{max-width:430px;margin:80px auto}table{width:100%;border-collapse:collapse}td,th{padding:10px;border-bottom:1px solid #ddd;text-align:left}</style>"""

def shell(content):
    if "user_id" not in session: return redirect("/login")
    admin='<a href="/usuarios">🔐 Usuarios</a>' if session.get("role")=="admin" else ""
    nav=f"""<a href="/">📊 Dashboard</a><a href="/modulo/contabilidad">📚 Contabilidad</a>
<a href="/modulo/ventas">🧾 Ventas</a><a href="/modulo/compras">🛒 Compras</a>
<a href="/modulo/cxc">💰 CxC</a><a href="/modulo/cxp">💳 CxP</a><a href="/modulo/inventario">📦 Inventario</a>
<a href="/modulo/bancos">🏦 Caja y Bancos</a><a href="/modulo/impuestos">🇪🇨 IVA / Retenciones</a>
<a href="/modulo/nomina">👥 Nómina</a><a href="/modulo/reportes">📈 Reportes</a>{admin}"""
    return render_template_string("""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>BIGCONTA</title>"""+STYLE+"""</head>
<body><div class="top"><b>BIGCONTA</b><span>{{name}} | <a style="color:white" href="/logout">Salir</a></span></div>
<div class="wrap"><nav>"""+nav+"""</nav><main>"""+content+"""</main></div></body></html>""",name=session.get("full_name",""))

FORM="""<form method="post"><input name="username" placeholder="Usuario" required>
<input name="password" type="password" placeholder="Contraseña" required><button>Ingresar</button></form>
<p><small>Acceso inicial: admin / Admin123!</small></p>"""

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        with engine.begin() as db:
            u=db.execute(text("SELECT * FROM users WHERE username=:u AND active=TRUE"),
                         {"u":request.form["username"].strip()}).mappings().first()
        if u and check_password_hash(u["password_hash"],request.form["password"]):
            session.update(user_id=u["id"],full_name=u["full_name"],role=u["role"])
            return redirect("/")
        return render_template_string("<main class='login'><div class='card'><h1>BIGCONTA</h1><p>Usuario o contraseña incorrectos.</p>"+FORM+"</div></main>"+STYLE)
    return render_template_string("<main class='login'><div class='card'><h1>BIGCONTA</h1><p>Sistema Integral de Gestión Contable y Empresarial</p>"+FORM+"</div></main>"+STYLE)

@app.route("/logout")
def logout(): session.clear(); return redirect("/login")

@app.route("/")
def home():
    return shell("""<h1>Dashboard</h1><p>Bienvenido a BIGCONTA.</p><div class="grid">
<div class="card">Ingresos<div class="kpi">$0.00</div></div><div class="card">Gastos<div class="kpi">$0.00</div></div>
<div class="card">CxC<div class="kpi">$0.00</div></div><div class="card">CxP<div class="kpi">$0.00</div></div></div>
<div class="card"><h2>BIGCONTA V1</h2><p>Base funcional: autenticación, usuarios, roles y navegación.</p></div>""")

@app.route("/modulo/<name>")
def modulo(name):
    titles={"contabilidad":"Contabilidad","ventas":"Ventas y Facturación","compras":"Compras",
    "cxc":"Cuentas por Cobrar","cxp":"Cuentas por Pagar","inventario":"Inventario",
    "bancos":"Caja y Bancos","impuestos":"IVA y Retenciones","nomina":"Nómina","reportes":"Reportes"}
    return shell(f"<h1>{titles.get(name,'Módulo')}</h1><div class='card'><p>Módulo preparado para continuar su desarrollo.</p></div>")

@app.route("/usuarios",methods=["GET","POST"])
def usuarios():
    if "user_id" not in session or session.get("role")!="admin": return redirect("/")
    msg=""
    if request.method=="POST":
        try:
            with engine.begin() as db:
                db.execute(text("""INSERT INTO users(username,full_name,password_hash,role,active)
                VALUES(:u,:n,:p,:r,TRUE)"""),{"u":request.form["username"].strip(),"n":request.form["full_name"].strip(),
                "p":generate_password_hash(request.form["password"]),"r":request.form["role"]})
            msg="Usuario creado correctamente."
        except Exception: msg="No se pudo crear el usuario."
    with engine.begin() as db:
        rows=db.execute(text("SELECT username,full_name,role,active FROM users ORDER BY id DESC")).mappings().all()
    html="".join(f"<tr><td>{r['username']}</td><td>{r['full_name']}</td><td>{r['role']}</td><td>{r['active']}</td></tr>" for r in rows)
    return shell(f"""<h1>Usuarios y permisos</h1><div class="card"><p>{msg}</p>
<form method="post"><input name="username" placeholder="Usuario" required><input name="full_name" placeholder="Nombre completo" required>
<select name="role"><option value="empleado">Empleado</option><option value="admin">Administrador</option></select>
<input name="password" type="password" placeholder="Contraseña inicial" required><button>Crear</button></form></div>
<div class="card"><h3>Usuarios</h3><table><tr><th>Usuario</th><th>Nombre</th><th>Rol</th><th>Activo</th></tr>{html}</table></div>""")

if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.getenv("PORT","8000")))
