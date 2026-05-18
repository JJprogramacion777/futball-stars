
-- En Postgres, si ya creaste la base de datos manualmente, no necesitas el CREATE DATABASE aquí.

-- 1. Tabla de Usuarios
CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    nombre_completo VARCHAR(100) NOT NULL,
    correo VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Tabla de Administradores
CREATE TABLE IF NOT EXISTS administradores (
    id SERIAL PRIMARY KEY,
    usuario VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);

-- 3. Insertar administrador (Asegúrate de hashear esta clave luego en Python por seguridad)
INSERT INTO administradores (usuario, password) 
VALUES ('admin_futball', 'FutballAdmin2026!')
ON CONFLICT (usuario) DO NOTHING; -- Evita error si ya existe

-- 4. Tabla de Reservas
CREATE TABLE IF NOT EXISTS reservas (
    id SERIAL PRIMARY KEY,
    cancha_id VARCHAR(10),
    usuario_nombre VARCHAR(100),
    usuario_correo VARCHAR(100),
    fecha DATE,
    hora TIME
);


ALTER TABLE reservas 
ADD CONSTRAINT reserva_unica UNIQUE (cancha_id, fecha, hora);


CREATE TABLE mensajes_contacto (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre TEXT NOT NULL,
    correo TEXT NOT NULL,
    mensaje TEXT NOT NULL,
    fecha_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    leido BOOLEAN DEFAULT FALSE
);

CREATE TABLE historial_eliminaciones (
    id SERIAL PRIMARY KEY,
    mensaje_id INT,
    nombre_admin TEXT,
    fecha_eliminacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pagos (
    id_pago SERIAL PRIMARY KEY,
    id_reserva INTEGER,
    monto DECIMAL(10,2),
    metodo_pago VARCHAR(50),
    estado VARCHAR(20),
    fecha_pago TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    referencia VARCHAR(100)
);



