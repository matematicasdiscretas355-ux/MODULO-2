from flask import (
    Flask, render_template, render_template_string,
    request, redirect, url_for, session
)
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "SmartRoute-clave-local-2026"
)

RUTA_DB = os.path.join(
    os.path.dirname(__file__), "vehiculos.db"
)

USUARIO = "admin"
CLAVE_HASH = generate_password_hash("SmartRoute2026!")


def conectar():
    return sqlite3.connect(RUTA_DB)


# CREAR TABLAS SIN BORRAR DATOS
def crear_tabla():
    conexion = conectar()

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS vehiculos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placa TEXT UNIQUE NOT NULL,
            marca TEXT NOT NULL,
            modelo TEXT NOT NULL,
            anio INTEGER NOT NULL,
            capacidad_peso REAL NOT NULL,
            capacidad_volumen REAL NOT NULL,
            estado TEXT NOT NULL DEFAULT 'Disponible'
        )
    """)

    columnas = [
        fila[1]
        for fila in conexion.execute(
            "PRAGMA table_info(vehiculos)"
        ).fetchall()
    ]

    if "fecha_creacion" not in columnas:
        conexion.execute(
            "ALTER TABLE vehiculos ADD COLUMN fecha_creacion TEXT"
        )
        conexion.execute("""
            UPDATE vehiculos
            SET fecha_creacion = ?
            WHERE fecha_creacion IS NULL
        """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))

    if "fecha_eliminacion" not in columnas:
        conexion.execute(
            "ALTER TABLE vehiculos ADD COLUMN fecha_eliminacion TEXT"
        )

    if "eliminado" not in columnas:
        conexion.execute("""
            ALTER TABLE vehiculos
            ADD COLUMN eliminado INTEGER NOT NULL DEFAULT 0
        """)

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS usuarios_vehiculos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            contrasena TEXT NOT NULL
        )
    """)

    cantidad = conexion.execute(
        "SELECT COUNT(*) FROM usuarios_vehiculos"
    ).fetchone()[0]

    if cantidad == 0:
        conexion.execute("""
            INSERT INTO usuarios_vehiculos (usuario, contrasena)
            VALUES (?, ?)
        """, (
            "adminveh",
            generate_password_hash("Ruta2026!")
        ))

    conexion.commit()
    conexion.close()


crear_tabla()


# PROTEGER EL INGRESO GENERAL
def requiere_login(funcion):
    @wraps(funcion)
    def verificar(*args, **kwargs):
        if "usuario" not in session:
            return redirect(url_for("login"))
        return funcion(*args, **kwargs)
    return verificar


# PROTEGER EL MODULO DE VEHICULOS
def requiere_acceso_vehiculos(funcion):
    @wraps(funcion)
    def verificar(*args, **kwargs):
        if not session.get("acceso_vehiculos"):
            return redirect(url_for("acceso_vehiculos"))
        return funcion(*args, **kwargs)
    return verificar


# INGRESO GENERAL
@app.route("/login", methods=["GET", "POST"])
def login():
    mensaje = ""

    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        contrasena = request.form.get("contrasena", "")

        if (
            usuario == USUARIO
            and check_password_hash(CLAVE_HASH, contrasena)
        ):
            session.clear()
            session["usuario"] = usuario
            return redirect(url_for("menu"))

        mensaje = "Usuario o contraseña incorrectos."

    return render_template("login.html", mensaje=mensaje)


# CERRAR TODO EL SISTEMA
@app.route("/cerrar_sesion")
def cerrar_sesion():
    session.clear()
    return redirect(url_for("login"))


# MENU PRINCIPAL
@app.route("/")
@requiere_login
def menu():
    return render_template("menu.html")


# INGRESO A ADMINISTRACION DE VEHICULOS
@app.route("/acceso-vehiculos", methods=["GET", "POST"])
@requiere_login
def acceso_vehiculos():
    mensaje = ""

    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        contrasena = request.form.get("contrasena", "")

        conexion = conectar()

        cuenta = conexion.execute("""
            SELECT usuario, contrasena
            FROM usuarios_vehiculos
            WHERE usuario = ?
        """, (usuario,)).fetchone()

        conexion.close()

        if cuenta and check_password_hash(cuenta[1], contrasena):
            session["acceso_vehiculos"] = True
            session["usuario_vehiculos"] = cuenta[0]
            return redirect(url_for("inicio"))

        mensaje = "Usuario o contraseña incorrectos."

    return render_template(
        "acceso_vehiculos.html",
        mensaje=mensaje
    )


# CREAR CUENTAS PARA EL MODULO
@app.route("/crear-usuario-vehiculos", methods=["GET", "POST"])
@requiere_login
def crear_usuario_vehiculos():
    if session.get("usuario") != "admin":
        return "No tienes permiso para crear usuarios.", 403

    mensaje = ""

    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        contrasena = request.form.get("contrasena", "")

        if len(usuario) < 3:
            mensaje = "El usuario debe tener al menos 3 caracteres."

        elif len(contrasena) < 8:
            mensaje = "La contraseña debe tener al menos 8 caracteres."

        else:
            conexion = conectar()

            try:
                conexion.execute("""
                    INSERT INTO usuarios_vehiculos
                    (usuario, contrasena)
                    VALUES (?, ?)
                """, (
                    usuario,
                    generate_password_hash(contrasena)
                ))

                conexion.commit()
                mensaje = "Usuario creado correctamente."

            except sqlite3.IntegrityError:
                mensaje = "Ese nombre de usuario ya existe."

            finally:
                conexion.close()

    return render_template_string("""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Crear usuario | SmartRoute</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background: #eef3f9;
                padding: 30px;
            }
            .caja {
                max-width: 420px;
                margin: 40px auto;
                background: white;
                padding: 28px;
                border-radius: 14px;
            }
            input, button {
                width: 100%;
                padding: 12px;
                margin-top: 10px;
                box-sizing: border-box;
            }
            button {
                background: #2457a7;
                color: white;
                border: 0;
                border-radius: 7px;
                cursor: pointer;
            }
            a {
                color: #2457a7;
            }
        </style>
    </head>
    <body>
        <div class="caja">
            <h2>Crear usuario de vehículos</h2>
            <p>{{ mensaje }}</p>

            <form method="POST">
                <label>Nombre de usuario</label>
                <input name="usuario" required minlength="3">

                <label>Contraseña (mínimo 8 caracteres)</label>
                <input type="password" name="contrasena"
                       required minlength="8">

                <button type="submit">Crear cuenta</button>
            </form>

            <p><a href="{{ url_for('menu') }}">Volver al menú</a></p>
        </div>
    </body>
    </html>
    """, mensaje=mensaje)


# CERRAR SOLO EL ACCESO AL MODULO
@app.route("/cerrar-acceso-vehiculos")
@requiere_login
def cerrar_acceso_vehiculos():
    session.pop("acceso_vehiculos", None)
    session.pop("usuario_vehiculos", None)
    return redirect(url_for("menu"))


# COMPROBAR PLACA MIENTRAS SE ESCRIBE
@app.route("/comprobar-placa")
@requiere_login
@requiere_acceso_vehiculos
def comprobar_placa():
    placa = request.args.get("placa", "").strip().upper()

    if not placa:
        return {"existe": False}

    conexion = conectar()

    vehiculo = conexion.execute("""
        SELECT id
        FROM vehiculos
        WHERE UPPER(placa) = ?
        AND eliminado = 0
    """, (placa,)).fetchone()

    conexion.close()

    return {"existe": vehiculo is not None}


# ADMINISTRACION DE VEHICULOS
@app.route("/vehiculos", methods=["GET", "POST"])
@requiere_login
@requiere_acceso_vehiculos
def inicio():
    mensaje = ""

    if request.method == "POST":
        placa = request.form["placa"].strip().upper()
        marca = request.form["marca"].strip()
        modelo = request.form["modelo"].strip()
        anio = request.form["anio"]
        peso = request.form["capacidad_peso"]
        volumen = request.form["capacidad_volumen"]
        estado = request.form["estado"]

        conexion = conectar()

        try:
            conexion.execute("""
                INSERT INTO vehiculos (
                    placa, marca, modelo, anio,
                    capacidad_peso, capacidad_volumen, estado,
                    fecha_creacion, fecha_eliminacion, eliminado
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, 0)
            """, (
                placa,
                marca,
                modelo,
                int(anio),
                float(peso),
                float(volumen),
                estado,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))

            conexion.commit()
            return redirect(url_for("inicio"))

        except sqlite3.IntegrityError:
            mensaje = "Esa placa ya está registrada."

        except ValueError:
            mensaje = "Revisa el año y las capacidades."

        finally:
            conexion.close()

    buscar = request.args.get("buscar", "").strip()

    conexion = conectar()

    if buscar:
        vehiculos = conexion.execute("""
            SELECT *
            FROM vehiculos
            WHERE eliminado = 0
            AND (placa LIKE ? OR marca LIKE ?)
            ORDER BY id DESC
        """, ("%" + buscar + "%", "%" + buscar + "%")).fetchall()

    else:
        vehiculos = conexion.execute("""
            SELECT *
            FROM vehiculos
            WHERE eliminado = 0
            ORDER BY id DESC
        """).fetchall()

    total = conexion.execute("""
        SELECT COUNT(*)
        FROM vehiculos
        WHERE eliminado = 0
    """).fetchone()[0]

    disponibles = conexion.execute("""
        SELECT COUNT(*)
        FROM vehiculos
        WHERE eliminado = 0 AND estado = 'Disponible'
    """).fetchone()[0]

    en_uso = conexion.execute("""
        SELECT COUNT(*)
        FROM vehiculos
        WHERE eliminado = 0 AND estado = 'En uso'
    """).fetchone()[0]

    conexion.close()

    return render_template(
        "index.html",
        vehiculos=vehiculos,
        mensaje=mensaje,
        buscar=buscar,
        total=total,
        disponibles=disponibles,
        en_uso=en_uso
    )


# CAMBIAR EL ESTADO DE UN VEHICULO
@app.route("/cambiar_estado", methods=["POST"])
@requiere_login
@requiere_acceso_vehiculos
def cambiar_estado():
    id_vehiculo = request.form["id"]
    nuevo_estado = request.form["estado"]

    if nuevo_estado not in [
        "Disponible", "En uso", "Mantenimiento"
    ]:
        return redirect(url_for("inicio"))

    conexion = conectar()

    conexion.execute("""
        UPDATE vehiculos
        SET estado = ?
        WHERE id = ? AND eliminado = 0
    """, (nuevo_estado, id_vehiculo))

    conexion.commit()
    conexion.close()

    return redirect(url_for("inicio"))


# ENVIAR VEHICULO A LA PAPELERA
@app.route("/eliminar", methods=["POST"])
@requiere_login
@requiere_acceso_vehiculos
def eliminar():
    id_vehiculo = request.form["id"]

    conexion = conectar()

    conexion.execute("""
        UPDATE vehiculos
        SET eliminado = 1, fecha_eliminacion = ?
        WHERE id = ? AND eliminado = 0
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        id_vehiculo
    ))

    conexion.commit()
    conexion.close()

    return redirect(url_for("inicio"))


# VER LA PAPELERA
@app.route("/eliminados")
@requiere_login
@requiere_acceso_vehiculos
def eliminados():
    conexion = conectar()

    vehiculos = conexion.execute("""
        SELECT *
        FROM vehiculos
        WHERE eliminado = 1
        ORDER BY fecha_eliminacion DESC, id DESC
    """).fetchall()

    conexion.close()

    return render_template(
        "eliminados.html",
        vehiculos=vehiculos
    )


# RESTAURAR VEHICULO
@app.route("/restaurar", methods=["POST"])
@requiere_login
@requiere_acceso_vehiculos
def restaurar():
    id_vehiculo = request.form["id"]

    conexion = conectar()

    conexion.execute("""
        UPDATE vehiculos
        SET eliminado = 0, fecha_eliminacion = NULL
        WHERE id = ? AND eliminado = 1
    """, (id_vehiculo,))

    conexion.commit()
    conexion.close()

    return redirect(url_for("eliminados"))


if __name__ == "__main__":
    app.run(debug=True)