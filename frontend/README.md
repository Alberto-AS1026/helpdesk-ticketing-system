# Frontend (interfaz)

La interfaz está hecha con **HTML, CSS y JavaScript sin frameworks**: no hay
React, ni paso de compilación, ni librerías descargadas de Internet. Nginx
sirve estos archivos tal cual. La única librería externa es Chart.js, para
los gráficos del dashboard, y está copiada en `js/vendor/`.

El aspecto imita a las herramientas profesionales de gestión de servicios
(tipo ServiceNow): cabecera oscura con un buscador global, menú lateral con
las colas de trabajo, listas compactas y una ficha de incidente con su flujo
de estados.

## Páginas

| Página | Para qué sirve | Script |
|---|---|---|
| `login.html` | Iniciar sesión | `login.js` |
| `index.html` | Listas de incidentes (todas las vistas del menú lateral) | `tickets.js` |
| `ticket.html` | Ficha de un incidente: datos, acciones, notas y resolución | `ticket.js` |
| `new.html` | Crear un incidente | `new.js` |
| `dashboard.html` | Indicadores y gráficos (solo personal técnico) | `dashboard.js` |
| `chat.html` | Chat en tiempo real | `chat.js` |

## Cómo se monta cada página

Cada página carga sus scripts en este orden:

1. **`theme.js`**, en la cabecera del HTML, para aplicar el modo claro u
   oscuro antes de pintar nada (así no hay un destello blanco al cargar).
2. **`api.js`**, con las herramientas que usan todas las páginas: llamar a la
   API con el token de sesión, cerrar la sesión si caduca, crear elementos de
   forma segura, dar formato a fechas, números de incidente (`INC0000001`) y
   prioridades, y la conexión en tiempo real del chat.
3. **`layout.js`**, que construye la cabecera (logo, buscador global, usuario,
   tema y salir) y el menú lateral, y coloca dentro el contenido de la
   página. Gracias a esto, cada HTML solo contiene su parte propia y el menú
   se mantiene igual en todas las pantallas.
4. **El script de la página**, que carga los datos y responde a los clics.

Como son scripts clásicos (no módulos), todos comparten el mismo espacio de
nombres: dos scripts de la misma página no pueden declarar una variable o
función de nivel superior con el mismo nombre.

## Las vistas del menú lateral

Todas las listas son la misma página, `index.html`, con un parámetro `view`
en la dirección que decide qué se muestra:

| Dirección | Lista |
|---|---|
| `/?view=mine` | Mis incidentes (empleados) |
| `/?view=assigned` | Asignados a mí (técnicos) |
| `/?view=unassigned` | Sin asignar |
| `/?view=open` · `progress` · `pending` · `resolved` | Por estado |
| `/?view=all` | Todos los incidentes |

El menú enseña a cada persona solo las entradas de su rol. Esto es una
comodidad, no una medida de seguridad: quien decide de verdad qué puede ver
cada uno es la API.

## Seguridad en la interfaz

- **Nunca se usa `innerHTML`** con datos que vengan de usuarios: todo se
  pinta con `textContent`, de modo que si alguien escribe código en un
  comentario, se muestra como texto y no se ejecuta.
- Nginx aplica una **política de seguridad de contenidos (CSP)** que solo
  permite ejecutar los scripts y estilos de la propia aplicación. Por eso no
  hay `<script>` ni estilos escritos dentro de los HTML, ni recursos de otros
  dominios.
- La sesión se guarda en `sessionStorage`, que es independiente en cada
  pestaña y se borra al cerrarla.

## Estilos

Todo el diseño está en `css/style.css`. Los colores se definen como
variables al principio del archivo, una vez para el modo claro y otra para el
oscuro, así que cambiar la paleta es cuestión de tocar esas líneas. En
pantallas estrechas el menú lateral se oculta y se abre con el botón ☰, y las
fichas pasan de dos columnas a una.
