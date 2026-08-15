import os
from datetime import datetime
from flask import Flask, request, redirect, session, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import create_engine, text

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "CAMBIAR-ESTA-CLAVE")

url = os.getenv("DATABASE_URL", "sqlite:///bigconta.db")
if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql://", 1)

engine = create_engine(url, pool_pre_ping=True)


# =========================================================
# BASE DE DATOS
# =========================================================

with engine.begin() as db:

    db.execute(text("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username VARCHAR(80) UNIQUE NOT NULL,
            full_name VARCHAR(150) NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(30) NOT NULL DEFAULT 'empleado',
            active BOOLEAN NOT NULL DEFAULT TRUE
        )
    """))

    db.execute(text("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY,
            name VARCHAR(150) NOT NULL,
            identification VARCHAR(30),
            email VARCHAR(150),
            phone VARCHAR(50),
            address VARCHAR(250)
        )
    """))

    db.execute(text("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY,
            invoice_number VARCHAR(50) UNIQUE NOT NULL,
            client_id INTEGER,
            invoice_date VARCHAR(20) NOT NULL,
            subtotal DECIMAL(12,2) NOT NULL DEFAULT 0,
            tax DECIMAL(12,2) NOT NULL DEFAULT 0,
            total DECIMAL(12,2) NOT NULL DEFAULT 0,
            status VARCHAR(30) NOT NULL DEFAULT 'Emitida'
        )
    """))

    db.execute(text("""
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY,
            invoice_id INTEGER NOT NULL,
            description VARCHAR(250) NOT NULL,
            quantity DECIMAL(12,2) NOT NULL,
            unit_price DECIMAL(12,2) NOT NULL,
            subtotal DECIMAL(12,2) NOT NULL
        )
    """))
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            code VARCHAR(50) UNIQUE NOT NULL,
            name VARCHAR(150) NOT NULL,
            category VARCHAR(100),
            unit VARCHAR(30) NOT NULL DEFAULT 'Unidad',
            purchase_price DECIMAL(12,2) NOT NULL DEFAULT 0,
            sale_price DECIMAL(12,2) NOT NULL DEFAULT 0,
            stock DECIMAL(12,2) NOT NULL DEFAULT 0,
            min_stock DECIMAL(12,2) NOT NULL DEFAULT 0,
            active BOOLEAN NOT NULL DEFAULT TRUE
        )
    """))
    if not db.execute(
        text("SELECT id FROM users WHERE username='admin'")
    ).first():

        db.execute(text("""
            INSERT INTO users
            (id, username, full_name, password_hash, role, active)
            VALUES
            (1, 'admin', 'Administrador BIGCONTA', :p, 'admin', TRUE)
        """), {
            "p": generate_password_hash("Admin123!")
        })


# =========================================================
# ESTILOS
# =========================================================

STYLE = """
<style>
*{box-sizing:border-box}

body{
    margin:0;
    font-family:Arial,sans-serif;
    background:#f4f6f8;
    color:#17202a
}

.top{
    background:#111827;
    color:white;
    padding:16px 24px;
    display:flex;
    justify-content:space-between;
    align-items:center
}

.top a{
    color:white
}

.wrap{
    display:flex;
    min-height:calc(100vh - 58px)
}

nav{
    width:235px;
    background:#1f2937;
    padding:16px
}

nav a{
    display:block;
    color:#e5e7eb;
    text-decoration:none;
    padding:10px;
    border-radius:7px;
    margin:3px 0
}

nav a:hover{
    background:#374151
}

main{
    padding:28px;
    flex:1
}

.card{
    background:white;
    border-radius:12px;
    padding:22px;
    margin-bottom:18px;
    box-shadow:0 2px 10px #0001
}

.grid{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
    gap:16px
}

.kpi{
    font-size:28px;
    font-weight:bold
}

input,select{
    display:block;
    width:100%;
    max-width:500px;
    padding:11px;
    margin:8px 0;
    border:1px solid #d1d5db;
    border-radius:7px
}

button{
    background:#111827;
    color:white;
    border:0;
    border-radius:7px;
    padding:11px 16px;
    cursor:pointer
}

button:hover{
    background:#374151
}

.btn{
    display:inline-block;
    background:#111827;
    color:white;
    padding:10px 15px;
    border-radius:7px;
    text-decoration:none
}

.login{
    max-width:430px;
    margin:80px auto
}

table{
    width:100%;
    border-collapse:collapse;
    background:white
}

td,th{
    padding:10px;
    border-bottom:1px solid #ddd;
    text-align:left
}

.success{
    background:#dcfce7;
    color:#166534;
    padding:12px;
    border-radius:7px;
    margin-bottom:15px
}

.warning{
    background:#fef3c7;
    color:#92400e;
    padding:12px;
    border-radius:7px;
    margin-bottom:15px
}

.total{
    font-size:24px;
    font-weight:bold;
    text-align:right
}
</style>
"""


# =========================================================
# DISEÑO GENERAL
# =========================================================

def shell(content):

    if "user_id" not in session:
        return redirect("/login")

    admin = ""

    if session.get("role") == "admin":
        admin = '<a href="/usuarios">🔐 Usuarios</a>'

    nav = f"""
    <a href="/">📊 Dashboard</a>
    <a href="/modulo/contabilidad">📚 Contabilidad</a>
    <a href="/ventas">🧾 Ventas</a>
    <a href="/modulo/compras">🛒 Compras</a>
    <a href="/modulo/cxc">💰 CxC</a>
    <a href="/modulo/cxp">💳 CxP</a>
    <a href="/modulo/inventario">📦 Inventario</a>
    <a href="/modulo/bancos">🏦 Caja y Bancos</a>
    <a href="/modulo/impuestos">🇪🇨 IVA / Retenciones</a>
    <a href="/modulo/nomina">👥 Nómina</a>
    <a href="/modulo/reportes">📈 Reportes</a>
    {admin}
    """

    return render_template_string(
        """
        <!doctype html>
        <html lang="es">
        <head>
        <meta charset="utf-8">
        <meta name="viewport"
              content="width=device-width,initial-scale=1">
        <title>BIGCONTA</title>
        """
        + STYLE +
        """
        </head>
        <body>

        <div class="top">
            <b>BIGCONTA</b>
            <span>
                {{name}} |
                <a href="/logout">Salir</a>
            </span>
        </div>

        <div class="wrap">

            <nav>
            """
        + nav +
        """
            </nav>

            <main>
            """
        + content +
        """
            </main>

        </div>
        </body>
        </html>
        """,
        name=session.get("full_name", "")
    )


# =========================================================
# LOGIN
# =========================================================

FORM = """
<form method="post">

<input
    name="username"
    placeholder="Usuario"
    required
>

<input
    name="password"
    type="password"
    placeholder="Contraseña"
    required
>

<button>Ingresar</button>

</form>

<p>
<small>
Acceso inicial: admin / Admin123!
</small>
</p>
"""


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        with engine.begin() as db:

            u = db.execute(
                text("""
                    SELECT *
                    FROM users
                    WHERE username=:u
                    AND active=TRUE
                """),
                {
                    "u": request.form["username"].strip()
                }
            ).mappings().first()

        if u and check_password_hash(
            u["password_hash"],
            request.form["password"]
        ):

            session.update(
                user_id=u["id"],
                full_name=u["full_name"],
                role=u["role"]
            )

            return redirect("/")

        return render_template_string(
            "<main class='login'>"
            "<div class='card'>"
            "<h1>BIGCONTA</h1>"
            "<p>Usuario o contraseña incorrectos.</p>"
            + FORM +
            "</div></main>" + STYLE
        )

    return render_template_string(
        "<main class='login'>"
        "<div class='card'>"
        "<h1>BIGCONTA</h1>"
        "<p>Sistema Integral de Gestión Contable y Empresarial</p>"
        + FORM +
        "</div></main>" + STYLE
    )


@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/")
def home():

    with engine.begin() as db:

        total_sales = db.execute(
            text("SELECT COALESCE(SUM(total),0) FROM invoices")
        ).scalar() or 0

        clients = db.execute(
            text("SELECT COUNT(*) FROM clients")
        ).scalar() or 0

        invoices = db.execute(
            text("SELECT COUNT(*) FROM invoices")
        ).scalar() or 0

    return shell(f"""

    <h1>Dashboard</h1>

    <p>Bienvenido a BIGCONTA.</p>

    <div class="grid">

        <div class="card">
            Ventas
            <div class="kpi">${float(total_sales):,.2f}</div>
        </div>

        <div class="card">
            Clientes
            <div class="kpi">{clients}</div>
        </div>

        <div class="card">
            Facturas
            <div class="kpi">{invoices}</div>
        </div>

        <div class="card">
            CxC
            <div class="kpi">$0.00</div>
        </div>

    </div>

    <div class="card">

        <h2>BIGCONTA V1</h2>

        <p>
        Sistema contable y empresarial en desarrollo.
        </p>

        <p>
        El módulo de Ventas y Facturación ya está habilitado.
        </p>

    </div>

    """)


# =========================================================
# VENTAS
# =========================================================

@app.route("/ventas")
def ventas():

    with engine.begin() as db:

        clients = db.execute(
            text("""
                SELECT *
                FROM clients
                ORDER BY name
            """)
        ).mappings().all()

        invoices = db.execute(
            text("""
                SELECT
                    invoices.*,
                    clients.name AS client_name
                FROM invoices
                LEFT JOIN clients
                    ON clients.id = invoices.client_id
                ORDER BY invoices.id DESC
            """)
        ).mappings().all()

    client_options = "".join(
        f"""
        <option value="{c['id']}">
            {c['name']}
        </option>
        """
        for c in clients
    )

    invoice_rows = ""

    for i in invoices:

        invoice_rows += f"""
        <tr>

            <td>{i['invoice_number']}</td>

            <td>{i['invoice_date']}</td>

            <td>{i['client_name'] or 'Consumidor final'}</td>

            <td>${float(i['total']):,.2f}</td>

            <td>{i['status']}</td>

            <td>
                <a class="btn"
                   href="/factura/{i['id']}">
                   Ver
                </a>
            </td>

        </tr>
        """

    return shell(f"""

    <h1>Ventas y Facturación</h1>

    <div class="grid">

        <div class="card">

            <h2>Registrar cliente</h2>

            <form method="post"
                  action="/clientes/nuevo">

                <input
                    name="name"
                    placeholder="Nombre / Razón social"
                    required
                >

                <input
                    name="identification"
                    placeholder="RUC / Cédula"
                >

                <input
                    name="email"
                    type="email"
                    placeholder="Correo electrónico"
                >

                <input
                    name="phone"
                    placeholder="Teléfono"
                >

                <input
                    name="address"
                    placeholder="Dirección"
                >

                <button>
                    Guardar cliente
                </button>

            </form>

        </div>


        <div class="card">

            <h2>Nueva factura</h2>

            <form method="post"
                  action="/factura/nueva">

                <input
                    name="invoice_number"
                    placeholder="Número de factura"
                    required
                >

                <select name="client_id">

                    <option value="">
                        Consumidor final
                    </option>

                    {client_options}

                </select>

                <input
                    name="description"
                    placeholder="Producto o servicio"
                    required
                >

                <input
                    name="quantity"
                    type="number"
                    step="0.01"
                    min="0.01"
                    value="1"
                    placeholder="Cantidad"
                    required
                >

                <input
                    name="unit_price"
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="Precio unitario"
                    required
                >

                <button>
                    Crear factura
                </button>

            </form>

        </div>

    </div>


    <div class="card">

        <h2>Facturas registradas</h2>

        <table>

            <tr>
                <th>Número</th>
                <th>Fecha</th>
                <th>Cliente</th>
                <th>Total</th>
                <th>Estado</th>
                <th>Acción</th>
            </tr>

            {invoice_rows}

        </table>

    </div>

    """)


# =========================================================
# CLIENTES
# =========================================================

@app.route("/clientes/nuevo", methods=["POST"])
def nuevo_cliente():

    if "user_id" not in session:
        return redirect("/login")

    with engine.begin() as db:

        next_id = (
            db.execute(
                text("SELECT COALESCE(MAX(id),0)+1 FROM clients")
            ).scalar()
            or 1
        )

        db.execute(
            text("""
                INSERT INTO clients
                (
                    id,
                    name,
                    identification,
                    email,
                    phone,
                    address
                )
                VALUES
                (
                    :id,
                    :name,
                    :identification,
                    :email,
                    :phone,
                    :address
                )
            """),
            {
                "id": next_id,
                "name": request.form["name"].strip(),
                "identification": request.form.get(
                    "identification", ""
                ).strip(),
                "email": request.form.get(
                    "email", ""
                ).strip(),
                "phone": request.form.get(
                    "phone", ""
                ).strip(),
                "address": request.form.get(
                    "address", ""
                ).strip()
            }
        )

    return redirect("/ventas")


# =========================================================
# CREAR FACTURA
# =========================================================

@app.route("/factura/nueva", methods=["POST"])
def nueva_factura():

    if "user_id" not in session:
        return redirect("/login")

    invoice_number = request.form["invoice_number"].strip()
    client_id = request.form.get("client_id") or None
    description = request.form["description"].strip()

    quantity = float(request.form["quantity"])
    unit_price = float(request.form["unit_price"])

    subtotal = round(quantity * unit_price, 2)

    # IVA 15% Ecuador
    tax = round(subtotal * 0.15, 2)

    total = round(subtotal + tax, 2)

    today = datetime.now().strftime("%Y-%m-%d")

    with engine.begin() as db:

        invoice_id = (
            db.execute(
                text(
                    "SELECT COALESCE(MAX(id),0)+1 FROM invoices"
                )
            ).scalar()
            or 1
        )

        db.execute(
            text("""
                INSERT INTO invoices
                (
                    id,
                    invoice_number,
                    client_id,
                    invoice_date,
                    subtotal,
                    tax,
                    total,
                    status
                )
                VALUES
                (
                    :id,
                    :number,
                    :client,
                    :date,
                    :subtotal,
                    :tax,
                    :total,
                    'Emitida'
                )
            """),
            {
                "id": invoice_id,
                "number": invoice_number,
                "client": client_id,
                "date": today,
                "subtotal": subtotal,
                "tax": tax,
                "total": total
            }
        )

        item_id = (
            db.execute(
                text(
                    "SELECT COALESCE(MAX(id),0)+1 "
                    "FROM invoice_items"
                )
            ).scalar()
            or 1
        )

        db.execute(
            text("""
                INSERT INTO invoice_items
                (
                    id,
                    invoice_id,
                    description,
                    quantity,
                    unit_price,
                    subtotal
                )
                VALUES
                (
                    :id,
                    :invoice,
                    :description,
                    :quantity,
                    :price,
                    :subtotal
                )
            """),
            {
                "id": item_id,
                "invoice": invoice_id,
                "description": description,
                "quantity": quantity,
                "price": unit_price,
                "subtotal": subtotal
            }
        )

    return redirect(f"/factura/{invoice_id}")


# =========================================================
# VER FACTURA
# =========================================================

@app.route("/factura/<int:invoice_id>")
def ver_factura(invoice_id):

    with engine.begin() as db:

        invoice = db.execute(
            text("""
                SELECT
                    invoices.*,
                    clients.name AS client_name,
                    clients.identification,
                    clients.email,
                    clients.phone,
                    clients.address
                FROM invoices
                LEFT JOIN clients
                    ON clients.id = invoices.client_id
                WHERE invoices.id=:id
            """),
            {"id": invoice_id}
        ).mappings().first()

        if not invoice:
            return redirect("/ventas")

        items = db.execute(
            text("""
                SELECT *
                FROM invoice_items
                WHERE invoice_id=:id
                ORDER BY id
            """),
            {"id": invoice_id}
        ).mappings().all()

    rows = ""

    for item in items:

        rows += f"""
        <tr>
            <td>{item['description']}</td>
            <td>{float(item['quantity']):,.2f}</td>
            <td>${float(item['unit_price']):,.2f}</td>
            <td>${float(item['subtotal']):,.2f}</td>
        </tr>
        """

    return shell(f"""

    <h1>Factura {invoice['invoice_number']}</h1>

    <div class="card">

        <h2>BIGCONTA</h2>

        <p>
        <b>Fecha:</b>
        {invoice['invoice_date']}
        </p>

        <p>
        <b>Cliente:</b>
        {invoice['client_name'] or 'Consumidor final'}
        </p>

        <p>
        <b>Identificación:</b>
        {invoice['identification'] or '-'}
        </p>

    </div>

    <div class="card">

        <table>

            <tr>
                <th>Descripción</th>
                <th>Cantidad</th>
                <th>Precio</th>
                <th>Subtotal</th>
            </tr>

            {rows}

        </table>

        <p class="total">
            Subtotal: ${float(invoice['subtotal']):,.2f}
        </p>

        <p class="total">
            IVA 15%: ${float(invoice['tax']):,.2f}
        </p>

        <p class="total">
            TOTAL: ${float(invoice['total']):,.2f}
        </p>

    </div>

    <a class="btn" href="/ventas">
        ← Volver a Ventas
    </a>

    """)


# =========================================================
# OTROS MÓDULOS
# =========================================================

@app.route("/modulo/<name>")
@app.route("/modulo/<name>/<path:option>")
def modulo(name, option=None):

    modules = {
        "contabilidad": {
            "titulo": "Contabilidad",
            "icono": "📚",
            "descripcion": "Gestión contable integral de la empresa.",
            "opciones": [
                "Plan de cuentas",
                "Asientos contables",
                "Libro diario",
                "Libro mayor",
                "Balance de comprobación"
            ]
        },

        "ventas": {
            "titulo": "Ventas y Facturación",
            "icono": "🧾",
            "descripcion": "Gestión de clientes, ventas y facturación.",
            "opciones": [
                "Nueva factura",
                "Clientes",
                "Facturas emitidas",
                "Notas de crédito",
                "Reporte de ventas"
            ]
        },

        "compras": {
            "titulo": "Compras",
            "icono": "🛒",
            "descripcion": "Control de compras y proveedores.",
            "opciones": [
                "Nueva compra",
                "Proveedores",
                "Compras registradas",
                "Notas de débito",
                "Reporte de compras"
            ]
        },

        "cxc": {
            "titulo": "Cuentas por Cobrar",
            "icono": "💰",
            "descripcion": "Control de cuentas pendientes de cobro.",
            "opciones": [
                "Clientes pendientes",
                "Registrar cobro",
                "Cartera vencida",
                "Estado de cuenta",
                "Reporte de CxC"
            ]
        },

        "cxp": {
            "titulo": "Cuentas por Pagar",
            "icono": "💳",
            "descripcion": "Control de obligaciones y pagos a proveedores.",
            "opciones": [
                "Proveedores pendientes",
                "Registrar pago",
                "Cuentas vencidas",
                "Estado de cuenta",
                "Reporte de CxP"
            ]
        },

        "inventario": {
            "titulo": "Inventario",
            "icono": "📦",
            "descripcion": "Control de productos, existencias y movimientos.",
            "opciones": [
                "Productos",
                "Entradas",
                "Salidas",
                "Ajustes de inventario",
                "Kardex"
            ]
        },

        "bancos": {
            "titulo": "Caja y Bancos",
            "icono": "🏦",
            "descripcion": "Control de caja, bancos y movimientos financieros.",
            "opciones": [
                "Cuentas bancarias",
                "Movimientos",
                "Ingresos",
                "Egresos",
                "Conciliación bancaria"
            ]
        },

        "impuestos": {
            "titulo": "IVA y Retenciones",
            "icono": "🇪🇨",
            "descripcion": "Gestión tributaria y control de impuestos.",
            "opciones": [
                "IVA ventas",
                "IVA compras",
                "Retenciones",
                "ATS",
                "Reportes tributarios"
            ]
        },

        "nomina": {
            "titulo": "Nómina",
            "icono": "👥",
            "descripcion": "Administración de empleados y procesos de nómina.",
            "opciones": [
                "Empleados",
                "Sueldos",
                "Roles de pago",
                "Aportes",
                "Reportes de nómina"
            ]
        },

        "reportes": {
            "titulo": "Reportes",
            "icono": "📈",
            "descripcion": "Reportes financieros y administrativos de BIGCONTA.",
            "opciones": [
                "Estado de resultados",
                "Balance general",
                "Flujo de efectivo",
                "Ventas",
                "Compras",
                "Inventario"
            ]
        }
    }

    modulo_actual = modules.get(name)

    if not modulo_actual:
        return redirect("/")

    # Si se seleccionó una opción, mostrarla
    if option:
        opcion_encontrada = None

        for item in modulo_actual["opciones"]:
            if item == option:
                opcion_encontrada = item
                break

        if not opcion_encontrada:
            return redirect(f"/modulo/{name}")

        return shell(
            f"""
            <h1>
                {modulo_actual["icono"]}
                {opcion_encontrada}
            </h1>

            <div class="card">

                <h2>{opcion_encontrada}</h2>

                <p>
                    Módulo de <strong>{modulo_actual["titulo"]}</strong>
                </p>

                <p>
                    Esta sección está activa y lista
                    para continuar con el desarrollo.
                </p>

                <a
                    class="btn"
                    href="/modulo/{name}"
                >
                    ← Volver a {modulo_actual["titulo"]}
                </a>

            </div>
            """
        )

    # Mostrar las opciones del módulo
    botones = ""

    for option_item in modulo_actual["opciones"]:
        botones += f"""
        <div class="card" style="
            margin:0;
            border:1px solid #e5e7eb;
            transition:0.2s;
        "
        onmouseover="this.style.transform='translateY(-3px)'"
        onmouseout="this.style.transform='translateY(0)'">

            <h3>{option_item}</h3>

            <p style="color:#6b7280;">
                Selecciona esta opción para ingresar.
            </p>

            <a
                href="/modulo/{name}/{option_item}"
                style="
                    display:inline-block;
                    padding:10px 18px;
                    background:#111827;
                    color:white;
                    text-decoration:none;
                    border-radius:6px;
                "
            >
                Abrir
            </a>

        </div>
        """

    return shell(
        f"""
        <h1>
            {modulo_actual["icono"]}
            {modulo_actual["titulo"]}
        </h1>

        <div class="card">

            <h2>Módulo activo</h2>

            <p>
                {modulo_actual["descripcion"]}
            </p>

            <p>
                <strong>BIGCONTA V1</strong> —
                módulo habilitado correctamente.
            </p>

        </div>

        <div class="grid">
            {botones}
        </div>
        """
    )
# =========================================================
# INVENTARIO - PRODUCTOS
# =========================================================

@app.route("/modulo/inventario/Productos", methods=["GET", "POST"])
def productos():

    if "user_id" not in session:
        return redirect("/login")

    msg = ""
    error = ""

    if request.method == "POST":

        accion = request.form.get("accion")

        try:

            with engine.begin() as db:

                # -----------------------------------------
                # CREAR PRODUCTO
                # -----------------------------------------
                if accion == "crear":

                    next_id = (
                        db.execute(
                            text(
                                "SELECT COALESCE(MAX(id),0)+1 "
                                "FROM products"
                            )
                        ).scalar()
                        or 1
                    )

                    db.execute(
                        text("""
                            INSERT INTO products
                            (
                                id,
                                code,
                                name,
                                category,
                                unit,
                                purchase_price,
                                sale_price,
                                stock,
                                min_stock,
                                active
                            )
                            VALUES
                            (
                                :id,
                                :code,
                                :name,
                                :category,
                                :unit,
                                :purchase_price,
                                :sale_price,
                                :stock,
                                :min_stock,
                                TRUE
                            )
                        """),
                        {
                            "id": next_id,
                            "code": request.form["code"].strip(),
                            "name": request.form["name"].strip(),
                            "category": request.form.get(
                                "category", ""
                            ).strip(),
                            "unit": request.form.get(
                                "unit", "Unidad"
                            ).strip(),
                            "purchase_price": float(
                                request.form.get(
                                    "purchase_price", 0
                                ) or 0
                            ),
                            "sale_price": float(
                                request.form.get(
                                    "sale_price", 0
                                ) or 0
                            ),
                            "stock": float(
                                request.form.get(
                                    "stock", 0
                                ) or 0
                            ),
                            "min_stock": float(
                                request.form.get(
                                    "min_stock", 0
                                ) or 0
                            )
                        }
                    )

                    return redirect(
                        "/modulo/inventario/Productos"
                    )


                # -----------------------------------------
                # DESACTIVAR PRODUCTO
                # -----------------------------------------
                elif accion == "desactivar":

                    product_id = int(
                        request.form["product_id"]
                    )

                    db.execute(
                        text("""
                            UPDATE products
                            SET active=FALSE
                            WHERE id=:id
                        """),
                        {
                            "id": product_id
                        }
                    )

                    return redirect(
                        "/modulo/inventario/Productos"
                    )

        except Exception as e:

            error = str(e)


    # ---------------------------------------------
    # PRODUCTOS ACTIVOS
    # ---------------------------------------------

    with engine.begin() as db:

        products = db.execute(
            text("""
                SELECT *
                FROM products
                WHERE active=TRUE
                ORDER BY name
            """)
        ).mappings().all()


    rows = ""

    for p in products:

        stock = float(p["stock"])
        min_stock = float(p["min_stock"])

        if stock <= min_stock:

            estado = """
            <span style="
                color:#dc2626;
                font-weight:bold;
            ">
                ⚠ Stock bajo
            </span>
            """

        else:

            estado = """
            <span style="
                color:#16a34a;
                font-weight:bold;
            ">
                ✓ Normal
            </span>
            """

        rows += f"""
        <tr>

            <td>
                {p["code"]}
            </td>

            <td>
                <strong>{p["name"]}</strong>
            </td>

            <td>
                {p["category"] or ""}
            </td>

            <td>
                {p["unit"]}
            </td>

            <td>
                ${float(p["purchase_price"]):,.2f}
            </td>

            <td>
                ${float(p["sale_price"]):,.2f}
            </td>

            <td>
                {stock:,.2f}
            </td>

            <td>
                {min_stock:,.2f}
            </td>

            <td>
                {estado}
            </td>

            <td>

                <a
                    class="btn"
                    href="/modulo/inventario/Productos/editar/{p["id"]}"
                >
                    ✏️ Editar
                </a>

                <form
                    method="post"
                    style="
                        display:inline;
                        margin-left:5px;
                    "
                    onsubmit="
                        return confirm(
                            '¿Deseas desactivar este producto?'
                        );
                    "
                >

                    <input
                        type="hidden"
                        name="accion"
                        value="desactivar"
                    >

                    <input
                        type="hidden"
                        name="product_id"
                        value="{p["id"]}"
                    >

                    <button
                        type="submit"
                        style="
                            background:#dc2626;
                        "
                    >
                        🗑️ Desactivar
                    </button>

                </form>

            </td>

        </tr>
        """


    mensaje_html = ""

    if msg:

        mensaje_html = f"""
        <div class="success">
            {msg}
        </div>
        """

    if error:

        mensaje_html = f"""
        <div class="warning">
            Error: {error}
        </div>
        """


    return shell(f"""

    <h1>📦 Productos</h1>


    <div class="card">

        <h2>Nuevo producto</h2>

        {mensaje_html}

        <form method="post">

            <input
                type="hidden"
                name="accion"
                value="crear"
            >

            <div class="grid">

                <div>

                    <label>Código</label>

                    <input
                        name="code"
                        placeholder="Código del producto"
                        required
                    >

                </div>


                <div>

                    <label>Nombre</label>

                    <input
                        name="name"
                        placeholder="Nombre del producto"
                        required
                    >

                </div>


                <div>

                    <label>Categoría</label>

                    <input
                        name="category"
                        placeholder="Categoría"
                    >

                </div>


                <div>

                    <label>Unidad</label>

                    <input
                        name="unit"
                        value="Unidad"
                        placeholder="Unidad"
                    >

                </div>


                <div>

                    <label>Precio de compra</label>

                    <input
                        name="purchase_price"
                        type="number"
                        step="0.01"
                        min="0"
                        value="0"
                    >

                </div>


                <div>

                    <label>Precio de venta</label>

                    <input
                        name="sale_price"
                        type="number"
                        step="0.01"
                        min="0"
                        value="0"
                    >

                </div>


                <div>

                    <label>Stock inicial</label>

                    <input
                        name="stock"
                        type="number"
                        step="0.01"
                        min="0"
                        value="0"
                    >

                </div>


                <div>

                    <label>Stock mínimo</label>

                    <input
                        name="min_stock"
                        type="number"
                        step="0.01"
                        min="0"
                        value="0"
                    >

                </div>

            </div>


            <br>

            <button type="submit">
                ➕ Guardar producto
            </button>

        </form>

    </div>


    <div class="card">

        <h2>Productos registrados</h2>

        <div style="
            overflow-x:auto;
        ">

            <table>

                <tr>

                    <th>Código</th>

                    <th>Producto</th>

                    <th>Categoría</th>

                    <th>Unidad</th>

                    <th>Compra</th>

                    <th>Venta</th>

                    <th>Stock</th>

                    <th>Mínimo</th>

                    <th>Estado</th>

                    <th>Acciones</th>

                </tr>

                {rows}

            </table>

        </div>

    </div>


    <div class="card">

        <a
            class="btn"
            href="/modulo/inventario"
        >
            ← Volver a Inventario
        </a>

    </div>

    """)



# =========================================================
# EDITAR PRODUCTO
# =========================================================

@app.route(
    "/modulo/inventario/Productos/editar/<int:product_id>",
    methods=["GET", "POST"]
)
def editar_producto(product_id):

    if "user_id" not in session:
        return redirect("/login")


    error = ""


    if request.method == "POST":

        try:

            with engine.begin() as db:

                db.execute(
                    text("""
                        UPDATE products
                        SET
                            code=:code,
                            name=:name,
                            category=:category,
                            unit=:unit,
                            purchase_price=:purchase_price,
                            sale_price=:sale_price,
                            stock=:stock,
                            min_stock=:min_stock
                        WHERE id=:id
                    """),
                    {
                        "id": product_id,

                        "code": request.form[
                            "code"
                        ].strip(),

                        "name": request.form[
                            "name"
                        ].strip(),

                        "category": request.form.get(
                            "category", ""
                        ).strip(),

                        "unit": request.form.get(
                            "unit", "Unidad"
                        ).strip(),

                        "purchase_price": float(
                            request.form.get(
                                "purchase_price", 0
                            ) or 0
                        ),

                        "sale_price": float(
                            request.form.get(
                                "sale_price", 0
                            ) or 0
                        ),

                        "stock": float(
                            request.form.get(
                                "stock", 0
                            ) or 0
                        ),

                        "min_stock": float(
                            request.form.get(
                                "min_stock", 0
                            ) or 0
                        )
                    }
                )

            return redirect(
                "/modulo/inventario/Productos"
            )


        except Exception as e:

            error = str(e)


    with engine.begin() as db:

        product = db.execute(
            text("""
                SELECT *
                FROM products
                WHERE id=:id
            """),
            {
                "id": product_id
            }
        ).mappings().first()


    if not product:

        return redirect(
            "/modulo/inventario/Productos"
        )


    error_html = ""

    if error:

        error_html = f"""
        <div class="warning">
            Error: {error}
        </div>
        """


    return shell(f"""

    <h1>✏️ Editar producto</h1>


    <div class="card">

        <h2>
            Editar: {product["name"]}
        </h2>

        {error_html}


        <form method="post">

            <div class="grid">

                <div>

                    <label>Código</label>

                    <input
                        name="code"
                        value="{product["code"]}"
                        required
                    >

                </div>


                <div>

                    <label>Nombre</label>

                    <input
                        name="name"
                        value="{product["name"]}"
                        required
                    >

                </div>


                <div>

                    <label>Categoría</label>

                    <input
                        name="category"
                        value="{product["category"] or ""}"
                    >

                </div>


                <div>

                    <label>Unidad</label>

                    <input
                        name="unit"
                        value="{product["unit"]}"
                    >

                </div>


                <div>

                    <label>Precio de compra</label>

                    <input
                        name="purchase_price"
                        type="number"
                        step="0.01"
                        min="0"
                        value="{float(product["purchase_price"]):.2f}"
                    >

                </div>


                <div>

                    <label>Precio de venta</label>

                    <input
                        name="sale_price"
                        type="number"
                        step="0.01"
                        min="0"
                        value="{float(product["sale_price"]):.2f}"
                    >

                </div>


                <div>

                    <label>Stock</label>

                    <input
                        name="stock"
                        type="number"
                        step="0.01"
                        min="0"
                        value="{float(product["stock"]):.2f}"
                    >

                </div>


                <div>

                    <label>Stock mínimo</label>

                    <input
                        name="min_stock"
                        type="number"
                        step="0.01"
                        min="0"
                        value="{float(product["min_stock"]):.2f}"
                    >

                </div>

            </div>


            <br>


            <button type="submit">
                💾 Guardar cambios
            </button>


            <a
                class="btn"
                href="/modulo/inventario/Productos"
                style="
                    margin-left:8px;
                "
            >
                Cancelar
            </a>

        </form>

    </div>

    """)
# =========================================================
# USUARIOS
# =========================================================

# =========================================================
# USUARIOS
# =========================================================

@app.route("/usuarios", methods=["GET", "POST"])
def usuarios():

    if (
        "user_id" not in session
        or session.get("role") != "admin"
    ):
        return redirect("/")

    msg = ""

    if request.method == "POST":

        try:

            with engine.begin() as db:

                next_id = (
                    db.execute(
                        text(
                            "SELECT COALESCE(MAX(id),0)+1 "
                            "FROM users"
                        )
                    ).scalar()
                    or 1
                )

                db.execute(
                    text("""
                        INSERT INTO users
                        (
                            id,
                            username,
                            full_name,
                            password_hash,
                            role,
                            active
                        )
                        VALUES
                        (
                            :id,
                            :u,
                            :n,
                            :p,
                            :r,
                            TRUE
                        )
                    """),
                    {
                        "id": next_id,
                        "u": request.form["username"].strip(),
                        "n": request.form["full_name"].strip(),
                        "p": generate_password_hash(
                            request.form["password"]
                        ),
                        "r": request.form["role"]
                    }
                )

            msg = "Usuario creado correctamente."

        except Exception:
            msg = "No se pudo crear el usuario."

    with engine.begin() as db:

        rows = db.execute(
            text("""
                SELECT username,full_name,role,active
                FROM users
                ORDER BY id DESC
            """)
        ).mappings().all()

    html = ""

    for r in rows:

        html += f"""
        <tr>
            <td>{r['username']}</td>
            <td>{r['full_name']}</td>
            <td>{r['role']}</td>
            <td>{r['active']}</td>
        </tr>
        """

    return shell(
        f"""
        <h1>Usuarios y permisos</h1>

        <div class="card">

        <p>{msg}</p>

        <form method="post">

        <input
            name="username"
            placeholder="Usuario"
            required
        >

        <input
            name="full_name"
            placeholder="Nombre completo"
            required
        >

        <select name="role">

            <option value="empleado">
                Empleado
            </option>

            <option value="admin">
                Administrador
            </option>

        </select>

        <input
            name="password"
            type="password"
            placeholder="Contraseña inicial"
            required
        >

        <button>
            Crear usuario
        </button>

        </form>

        </div>

        <div class="card">

        <h3>Usuarios</h3>

        <table>

        <tr>
            <th>Usuario</th>
            <th>Nombre</th>
            <th>Rol</th>
            <th>Activo</th>
        </tr>

        {html}

        </table>

        </div>
        """
    )


# =========================================================
# ARRANQUE
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000"))
    )

