import os
@app.route("/comprar/<int:id>")
def comprar(id):
    producto = obtener_producto_por_id(id)

    if producto is None:
        flash("El producto seleccionado no existe.", "error")
        return redirect(url_for("tienda_virtual"))

    carrito = session.get("carrito", [])
    carrito.append(
        {
            "id": producto["id"],
            "nombre": producto["nombre"],
            "precio": float(producto["precio"]),
            "imagen": producto["imagen"],
        }
    )
    session["carrito"] = carrito
    flash(f"{producto['nombre']} fue agregado al carrito.", "ok")
    return redirect(url_for("ver_carrito"))


@app.route("/carrito")
def ver_carrito():
    carrito = session.get("carrito", [])
    total = sum(float(item["precio"]) for item in carrito)
    return render_template("carrito.html", carrito=carrito, total=total)


@app.route("/vaciar-carrito", methods=["POST"])
def vaciar_carrito():
    session["carrito"] = []
    flash("Carrito vaciado correctamente.", "ok")
    return redirect(url_for("ver_carrito"))


@app.route("/enviar-whatsapp")
def enviar_whatsapp():
    carrito = session.get("carrito", [])

    if not carrito:
        flash("Tu carrito está vacío.", "error")
        return redirect(url_for("ver_carrito"))

    total = sum(float(item["precio"]) for item in carrito)

    mensaje = "Hola, quiero realizar un pedido en PANES ARTESANALES LAS 3 BENDICIONES - Azuvalentina y Kiory:\n\n"
    for i, producto in enumerate(carrito, start=1):
        mensaje += f"{i}. {producto['nombre']} - S/ {float(producto['precio']):.2f}\n"

    mensaje += f"\nTotal: S/ {total:.2f}"
    mensaje += "\n\nPor favor, deseo confirmar mi pedido."

    mensaje_codificado = quote(mensaje)
    url_whatsapp = f"https://wa.me/{app.config['NUMERO_WHATSAPP']}?text={mensaje_codificado}"
    return redirect(url_whatsapp)


@app.errorhandler(404)
def no_encontrado(error):
    return render_template("base.html", contenido_error="Página no encontrada."), 404


@app.errorhandler(500)
def error_interno(error):
    return render_template("base.html", contenido_error="Ocurrió un error interno en el servidor."), 500


if __name__ == "__main__":
    with app.app_context():
        crear_tablas()
    app.run(debug=True)