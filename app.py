import os
import sqlite3
from uuid import uuid4
from urllib.parse import quote
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cambia-esto-en-produccion")

NUMERO_WHATSAPP = "51940849095"

USUARIO_ADMIN = os.environ.get("USUARIO_ADMIN", "admin")
CLAVE_ADMIN = os.environ.get("CLAVE_ADMIN", "123456")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "database")
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")

os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

DB_PATH = os.path.join(DB_DIR, "ventas.db")


def conectar_db():
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row
    return conexion


def crear_tablas():
    conexion = conectar_db()
    cursor = conexion.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            precio REAL NOT NULL,
            imagen TEXT
        )
    """)

    conexion.commit()
    conexion.close()


crear_tablas()


def obtener_productos():
    conexion = conectar_db()
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM productos ORDER BY id DESC")
    productos = cursor.fetchall()
    conexion.close()
    return productos


def obtener_producto_por_id(producto_id):
    conexion = conectar_db()
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM productos WHERE id = ?", (producto_id,))
    producto = cursor.fetchone()
    conexion.close()
    return producto


def login_requerido(func):
    @wraps(func)
    def envoltura(*args, **kwargs):
        if not session.get("admin_logueado"):
            flash("Debes iniciar sesión para entrar al panel de control.")
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return envoltura


@app.route("/")
def inicio():
    return redirect(url_for("tienda_virtual"))


@app.route("/tienda-virtual")
def tienda_virtual():
    productos = obtener_productos()
    return render_template("tienda.html", productos=productos)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"].strip()
        clave = request.form["clave"].strip()

        if usuario == USUARIO_ADMIN and clave == CLAVE_ADMIN:
            session["admin_logueado"] = True
            return redirect(url_for("panel_de_control"))
        else:
            flash("Usuario o contraseña incorrectos.")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("admin_logueado", None)
    flash("Sesión cerrada correctamente.")
    return redirect(url_for("login"))


@app.route("/panel-de-control")
@login_requerido
def panel_de_control():
    productos = obtener_productos()
    return render_template("admin.html", productos=productos)


@app.route("/panel-de-control/agregar", methods=["GET", "POST"])
@login_requerido
def agregar_producto():
    if request.method == "POST":
        nombre = request.form["nombre"].strip()
        precio = request.form["precio"].strip()
        imagen = request.files["imagen"]

        if not nombre or not precio:
            flash("Completa el nombre y el precio.")
            return redirect(url_for("agregar_producto"))

        nombre_imagen = None

        if imagen and imagen.filename:
            extension = os.path.splitext(imagen.filename)[1]
            nombre_imagen = f"{uuid4().hex}{extension}"
            ruta_imagen = os.path.join(UPLOAD_DIR, nombre_imagen)
            imagen.save(ruta_imagen)

        conexion = conectar_db()
        cursor = conexion.cursor()
        cursor.execute(
            "INSERT INTO productos (nombre, precio, imagen) VALUES (?, ?, ?)",
            (nombre, float(precio), nombre_imagen)
        )
        conexion.commit()
        conexion.close()

        flash("Producto agregado correctamente.")
        return redirect(url_for("panel_de_control"))

    return render_template("agregar_producto.html")


@app.route("/panel-de-control/eliminar/<int:id>")
@login_requerido
def eliminar_producto(id):
    producto = obtener_producto_por_id(id)

    if producto:
        if producto["imagen"]:
            ruta_imagen = os.path.join(UPLOAD_DIR, producto["imagen"])
            if os.path.exists(ruta_imagen):
                os.remove(ruta_imagen)

        conexion = conectar_db()
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM productos WHERE id = ?", (id,))
        conexion.commit()
        conexion.close()

        flash("Producto eliminado correctamente.")

    return redirect(url_for("panel_de_control"))


@app.route("/comprar/<int:id>")
def comprar(id):
    producto = obtener_producto_por_id(id)

    if not producto:
        return redirect(url_for("tienda_virtual"))

    carrito = session.get("carrito", [])

    carrito.append({
        "id": producto["id"],
        "nombre": producto["nombre"],
        "precio": float(producto["precio"]),
        "imagen": producto["imagen"]
    })

    session["carrito"] = carrito
    return redirect(url_for("ver_carrito"))


@app.route("/carrito")
def ver_carrito():
    carrito = session.get("carrito", [])
    total = sum(float(p["precio"]) for p in carrito)
    return render_template("carrito.html", carrito=carrito, total=total)


@app.route("/vaciar_carrito")
def vaciar_carrito():
    session["carrito"] = []
    return redirect(url_for("ver_carrito"))


@app.route("/enviar_whatsapp")
def enviar_whatsapp():
    carrito = session.get("carrito", [])

    if not carrito:
        return redirect(url_for("ver_carrito"))

    total = sum(float(p["precio"]) for p in carrito)

    mensaje = "Hola, quiero realizar un pedido en PANES ARTESANALES LAS 3 BENDICIONES - Azuvalentina y Kiory:\n\n"
    for i, producto in enumerate(carrito, start=1):
        mensaje += f"{i}. {producto['nombre']} - S/ {float(producto['precio']):.2f}\n"

    mensaje += f"\nTotal: S/ {total:.2f}"
    mensaje += "\n\nPor favor, deseo confirmar mi pedido."

    mensaje_codificado = quote(mensaje)
    url_whatsapp = f"https://wa.me/{NUMERO_WHATSAPP}?text={mensaje_codificado}"
    return redirect(url_whatsapp)


if __name__ == "__main__":
    app.run(debug=True)