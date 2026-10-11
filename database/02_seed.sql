-- =========================================
-- Datos de prueba (solo para desarrollo)
-- =========================================

INSERT INTO departments (name, description) VALUES
    ('Administración', 'Gestión y contabilidad'),
    ('Ventas', 'Equipo comercial'),
    ('Recursos Humanos', 'Personal y nóminas'),
    ('IT', 'Departamento de sistemas');

INSERT INTO categories (name) VALUES
    ('Hardware'), ('Software'), ('Red'), ('Cuentas y accesos'), ('Impresoras');

INSERT INTO priorities (name, level) VALUES
    ('Baja', 1), ('Media', 2), ('Alta', 3), ('Crítica', 4);

INSERT INTO users (full_name, email, password_hash, role, department_id) VALUES
    ('Laura Gómez',   'laura@empresa.test',  'hash_de_prueba', 'user',       1),
    ('Carlos Ruiz',   'carlos@empresa.test', 'hash_de_prueba', 'user',       2),
    ('Marta Díaz',    'marta@empresa.test',  'hash_de_prueba', 'user',       3),
    ('Pablo Torres',  'pablo@empresa.test',  'hash_de_prueba', 'technician', 4),
    ('Ana Sánchez',   'ana@empresa.test',    'hash_de_prueba', 'technician', 4),
    ('Admin Sistema', 'admin@empresa.test',  'hash_de_prueba', 'admin',      4);

INSERT INTO technicians (user_id, specialty, level) VALUES
    (4, 'Hardware y equipos', 'N1'),
    (5, 'Redes y servidores', 'N2');

INSERT INTO computers (hostname, serial_number, brand, model, os, assigned_to, department_id) VALUES
    ('PC-ADM-01',  'SN1001', 'Dell',   'OptiPlex 7090', 'Windows 11', 1, 1),
    ('PC-VEN-01',  'SN1002', 'HP',     'ProDesk 400',   'Windows 11', 2, 2),
    ('PC-RRHH-01', 'SN1003', 'Lenovo', 'ThinkCentre M70', 'Windows 10', 3, 3);

INSERT INTO tickets (title, description, status, priority_id, category_id, created_by, assigned_to, computer_id, created_at) VALUES
    ('No arranca el PC', 'Al encender no da señal de vídeo', 'Abierto', 3, 1, 1, 1, 1, NOW() - INTERVAL '2 days'),
    ('Sin acceso a internet', 'No hay conexión desde esta mañana', 'En progreso', 4, 3, 2, 2, 2, NOW() - INTERVAL '1 day'),
    ('Impresora no imprime', 'Se queda en cola', 'Pendiente', 2, 5, 3, 1, NULL, NOW() - INTERVAL '3 days'),
    ('Olvidé mi contraseña', 'No puedo entrar al correo', 'Abierto', 1, 4, 3, NULL, NULL, NOW() - INTERVAL '1 hour');

INSERT INTO ticket_comments (ticket_id, user_id, comment) VALUES
    (1, 4, 'Reviso el cable de vídeo y la fuente de alimentación.'),
    (2, 5, 'Parece un fallo del switch de la planta 2.');
