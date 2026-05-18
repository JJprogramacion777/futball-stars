import os

from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, url_for
from datetime import datetime, timedelta# Para que los resultados sean como diccionarios
from flask import flash, redirect, url_for
from flask import Flask, render_template, request, redirect, url_for, flash, session


app = Flask(__name__)
app.secret_key = 'clave_secreta_futball_stars'

# --- CONFIGURACIÓN DE LA BASE DE DATOS POSTGRESQL ---
def get_db_connection():
    try:
        DATABASE_URL = os.environ.get("DATABASE_URL")
        connection = psycopg2.connect(
            DATABASE_URL,
            options='-c search_path=public'   # 👈 fuerza el esquema correcto
        )
        return connection
    except Exception as err:
        print(f"Error de conexión a PostgreSQL: {err}")
        return None

# 1. Ruta de Inicio
@app.route('/')
def home():
    return render_template('index.html')

# 2. Saber Más
@app.route('/sabermas')
def sabermas():
    return render_template('sabermas.html')
#contacto 
@app.route('/contacto')
def contacto():
    return render_template('contacto.html')

# 3. Lógica de Registro
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        correo = request.form.get('correo')
        password = request.form.get('password')

        db = get_db_connection()
        if db is None:
            return "Error: No se pudo conectar a PostgreSQL. Revisa pgAdmin."
            
        cur = db.cursor()
        try:
            # En Postgres usamos %s para los placeholders
            sql = "INSERT INTO usuarios (nombre_completo, correo, password) VALUES (%s, %s, %s)"
            cur.execute(sql, (nombre, correo, password))
            db.commit()
            return redirect(url_for('login'))
        except Exception as err:
            print(f"Error en Registro: {err}")
            return f"Hubo un error o el correo ya está registrado: {err}"
        finally:
            cur.close()
            db.close()
            
    return render_template('register.html')

# 4. Lógica de Login Usuario
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form.get('correo')
        password = request.form.get('password')

        db = get_db_connection()
        if db is None: 
            return "Error de conexión"

        cur = db.cursor(cursor_factory=RealDictCursor)
        sql = "SELECT * FROM usuarios WHERE correo = %s AND password = %s"
        cur.execute(sql, (correo, password))
        usuario = cur.fetchone()
        
        cur.close()
        db.close()

        if usuario:
            return redirect(url_for('reservar')) # <--- EL DESTINO
        else:
            return "Credenciales incorrectas, intenta de nuevo."

    return render_template('login.html')

# 8. LA FUNCIÓN DESTINO (Debe estar al mismo nivel que login)
@app.route('/reservar')
def reservar():
    # 1. Lógica para las fechas del calendario
    dias_calendario = []
    ahora = datetime.now()
    nombres_dias = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']
    nombres_meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

    for i in range(7):
        fecha = ahora + timedelta(days=i)
        dias_calendario.append({
            'nombre': 'Hoy' if i == 0 else nombres_dias[fecha.weekday()],
            'numero': fecha.strftime('%d'),
            'mes': nombres_meses[fecha.month - 1],
            'fecha_completa': fecha.strftime('%Y-%m-%d')
        })

    # 2. Consultar qué canchas están ocupadas HOY (o la fecha seleccionada)
    fecha_hoy = ahora.strftime('%Y-%m-%d')
    canchas_ocupadas = []
    
    db = get_db_connection()
    if db:
        cur = db.cursor()
        # Buscamos los IDs de las canchas que ya tienen reserva para hoy
        cur.execute("SELECT cancha_id FROM reservas WHERE fecha = %s", (fecha_hoy,))
        # Guardamos los resultados en una lista: ['A1', 'B2', etc.]
        canchas_ocupadas = [row[0] for row in cur.fetchall()]
        cur.close()
        db.close()

    return render_template('usuario_reservas.html', dias=dias_calendario, ocupadas=canchas_ocupadas)

# --- DEBAJO COLOCAMOS LA FUNCIÓN DEL FORMULARIO ---
# --- FORMULARIO DE RESERVA ---
@app.route('/reservar/formulario/<cancha_id>', methods=['GET', 'POST'])
def formulario_reserva(cancha_id):
    if request.method == 'POST':
        nombre_equipo = request.form.get('equipo')
        correo_usuario = request.form.get('usuario_correo')
        fecha_reserva = request.form.get('fecha')
        hora_reserva = request.form.get('hora')

        db = get_db_connection()
        if db:
            cur = db.cursor()
            # Validar si la cancha ya está ocupada
            cur.execute("""SELECT id FROM reservas 
                           WHERE cancha_id = %s AND fecha = %s AND hora = %s""", 
                        (cancha_id, fecha_reserva, hora_reserva))
            existe = cur.fetchone()
            cur.close()
            db.close()

            if existe:
                return "<h1>⚠️ Lo sentimos, esta cancha ya está apartada a esa hora.</h1><a href='javascript:history.back()'>Regresar y elegir otra hora</a>"

            # Guardamos datos en sesión temporal para usarlos en el pago
            session['cancha_id'] = cancha_id
            session['usuario_nombre'] = nombre_equipo
            session['usuario_correo'] = correo_usuario
            session['fecha'] = fecha_reserva
            session['hora'] = hora_reserva

            # Redirigir al formulario de pagos
            return redirect(url_for('formulario_pagos'))

    return render_template('formulario_reservas.html', cancha_id=cancha_id)





# --- PROCESAR PAGO ---
@app.route('/procesar_pago', methods=['POST'])
def procesar_pago():
    metodo = request.form.get('metodo_pago')
    monto = request.form.get('monto')

    db = get_db_connection()
    if db:
        cur = db.cursor()
        try:
            # Insertar pago
            cur.execute("""
                INSERT INTO pagos (monto, metodo_pago, estado)
                VALUES (%s, %s, %s) RETURNING id_pago
            """, (monto, metodo, "Completado"))
            id_pago = cur.fetchone()[0]

            # Insertar reserva vinculada al pago
            cur.execute("""
                INSERT INTO reservas (cancha_id, usuario_nombre, usuario_correo, fecha, hora)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                session['cancha_id'],
                session['usuario_nombre'],
                session['usuario_correo'],
                session['fecha'],
                session['hora']
            ))
            db.commit()

            flash("✅ Reserva confirmada con pago exitoso")
            # Redirigir al apartado de reservas del usuario
            return redirect(url_for('usuarios_reservas'))

        except Exception as e:
            db.rollback()
            return f"Error: {e}"
        finally:
            cur.close()
            db.close()


# --- USUARIOS RESERVAS ---
@app.route('/usuarios/reservas')
def usuarios_reservas():
    db = get_db_connection()
    cur = db.cursor()
    cur.execute(
        "SELECT * FROM reservas WHERE usuario_correo = %s",
        (session['usuario_correo'],)
    )
    reservas_usuario = cur.fetchall()
    cur.close()
    db.close()
    return render_template('usuario_reservas.html', reservas=reservas_usuario)





# 5. Login Administrador
@app.route('/login/admin', methods=['GET', 'POST'])
def login_admin():
    if request.method == 'POST':
        usuario_input = request.form.get('usuario_admin')
        password_input = request.form.get('password_admin')

        db = get_db_connection()
        if db is None: return "Error de conexión"

        cur = db.cursor(cursor_factory=RealDictCursor)
        sql = "SELECT * FROM administradores WHERE usuario = %s AND password = %s"
        cur.execute(sql, (usuario_input, password_input))
        admin = cur.fetchone()
        
        cur.close()
        db.close()

        if admin:
            return redirect(url_for('dashboard'))
        else:
            return "Acceso denegado: Credenciales de administrador incorrectas."

    return render_template('login_admin.html')

@app.route('/dashboard')
def dashboard():
    seccion = request.args.get('seccion')
    db = get_db_connection()
    cur = db.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT * FROM reservas ORDER BY fecha DESC")
    reservas = cur.fetchall()

    cur.execute("SELECT * FROM usuarios ORDER BY fecha_registro DESC")
    clientes = cur.fetchall()

    pagos = []
    if seccion == 'pagos':
        cur.execute("""
            SELECT id_pago, metodo_pago, monto, estado, fecha_pago, referencia
            FROM pagos
            ORDER BY fecha_pago DESC;
        """)
        pagos = cur.fetchall()

    cur.close()
    db.close()

    return render_template(
        'dashboard.html',
        reservas=reservas,
        clientes=clientes,
        pagos=pagos,
        notificaciones=reservas[:5],
        seccion_activa=seccion
    )


    
    
@app.route('/formulario_pagos', methods=['GET', 'POST'])
def formulario_pagos():
    if request.method == 'POST':
        metodo_pago = request.form['metodo_pago']
        monto = request.form['monto']
        estado = 'Completado'  # Puedes ajustar según tu lógica
        referencia = request.form.get('referencia', 'N/A')  # opcional

        db = get_db_connection()
        cur = db.cursor()
        cur.execute("""
            INSERT INTO pagos (metodo_pago, monto, estado, referencia)
            VALUES (%s, %s, %s, %s)
        """, (metodo_pago, monto, estado, referencia))
        db.commit()
        cur.close()
        db.close()

        # Redirige al dashboard en la sección de pagos
        return redirect(url_for('dashboard', seccion='pagos'))

    return render_template('formulario_pagos.html')




# --- FUNCIONES CRUD PARA RESERVAS ---

# A. Eliminar Reserva
@app.route('/dashboard/reserva/eliminar/<int:id>')
def eliminar_reserva(id):
    db = get_db_connection()
    if db:
        cur = db.cursor()
        cur.execute("DELETE FROM reservas WHERE id = %s", (id,))
        db.commit()
        cur.close()
        db.close()
        flash("Reserva eliminada correctamente")
    return redirect(url_for('dashboard'))

# B. Editar Reserva
@app.route('/dashboard/reserva/editar/<int:id>', methods=['GET', 'POST'])
def editar_reserva(id):
    db = get_db_connection()
    cur = db.cursor(cursor_factory=RealDictCursor)
    
    if request.method == 'POST':
        equipo = request.form.get('equipo')
        fecha = request.form.get('fecha')
        hora = request.form.get('hora')
        
        cur.execute("""
            UPDATE reservas 
            SET usuario_nombre = %s, fecha = %s, hora = %s 
            WHERE id = %s
        """, (equipo, fecha, hora, id))
        db.commit()
        db.close()
        return redirect(url_for('dashboard'))
    
    cur.execute("SELECT * FROM reservas WHERE id = %s", (id,))
    reserva = cur.fetchone()
    cur.close()
    db.close()
    return render_template('editar_reserva.html', reserva=reserva)

@app.route('/dashboard/canchas')
def dashboard_canchas():
    db = get_db_connection()
    if db:
        cur = db.cursor()
        # Pedimos los datos tal cual los tienes en la BD
        cur.execute("SELECT cancha_id, usuario_nombre, fecha, hora, id FROM reservas")
        lista_reservas = cur.fetchall()
        cur.close()
        db.close()
        return render_template('dashboard_canchas.html', reservas=lista_reservas)
    return "Error de conexión"





# --- RUTA PARA CERRAR SESIÓN ---
@app.route('/logout')
def logout():
    # Esta función ahora es única y no choca con nadie
    return redirect(url_for('home'))

@app.route('/enviar_contacto', methods=['POST'])
def enviar_contacto():
    nombre = request.form.get('nombre')
    correo = request.form.get('correo')
    mensaje = request.form.get('mensaje')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO mensajes_contacto (nombre, correo, mensaje)
        VALUES (%s, %s, %s)
    """, (nombre, correo, mensaje))

    conn.commit()
    cursor.close()
    conn.close()

    # Mensaje temporal para el usuario
    flash("✅ Tu mensaje fue enviado correctamente. Te responderemos pronto.", "success")
    return redirect(url_for('contacto'))
 
    #admin notificaciones
@app.route('/admin/notificaciones')
def notificaciones():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Mensajes activos
    cursor.execute("SELECT * FROM mensajes_contacto ORDER BY fecha_envio DESC")
    mensajes = cursor.fetchall()

    # Últimas eliminaciones (ejemplo: 5 más recientes)
    cursor.execute("""
        SELECT h.id, h.mensaje_id, h.nombre_admin, h.fecha_eliminacion
        FROM historial_eliminaciones h
        ORDER BY h.fecha_eliminacion DESC
        LIMIT 5
    """)
    eliminaciones = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('notificaciones.html', mensajes=mensajes, eliminaciones=eliminaciones)


@app.route('/admin/eliminar_mensaje/<int:id>', methods=['POST'])
def eliminar_mensaje(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Registrar eliminación antes de borrar
    cursor.execute("""
        INSERT INTO historial_eliminaciones (mensaje_id, nombre_admin)
        VALUES (%s, %s)
    """, (id, "Administrador"))

    # Eliminar mensaje
    cursor.execute("DELETE FROM mensajes_contacto WHERE id = %s", (id,))
    conn.commit()

    cursor.close()
    conn.close()

    flash("🗑️ Mensaje eliminado correctamente y registrado en el historial.", "success")
    return redirect(url_for('notificaciones'))

# --- RUTA CLIENTES (CRUD) ---
@app.route('/clientes')
def clientes():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Traemos todos los clientes registrados
    cursor.execute("SELECT id, nombre_completo, correo, fecha_registro FROM usuarios ORDER BY fecha_registro DESC")
    clientes = cursor.fetchall()

    cursor.close()
    conn.close()

    # Renderizamos la plantilla clientes.html con su CSS propio
    return render_template('clientes.html', clientes=clientes)

# --- CIERRE DEL ARCHIVO ---
if __name__ == '__main__':
    app.run(debug=True)