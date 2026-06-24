# Requerimientos del Sistema - Orpey Servicios

## 1. Descripción General
**Nombre del proyecto:** Orpey Servicios - Sistema de Gestión de Servicio Técnico
**Objetivo:** [Gestionar negocio de servicio técnico para optimizar el tiempo, el dinero y el esfuerzo del negocio. Este sistema será usado por el dueño del negocio, los técnicos y mi asistente. El sistema de ordenes de servicio es prioritario para el negocio, es el mas importante en la estapa incial de software. por lo tanto quiero poder ingresar clientes y equipos de la manera mas eficiente posible, que me permita no cometer errores. el sistema debe ser robusto, simple y rapido. no quiero software que sea lento o que me obligue a hacer muchas cosas para hacer cosas simples. También buscamos crear cotizaciones de manera rapida que puedan ser enviadas por whatsapp o correo electronico al cliente y su vez al ser aprobadas se actualicen inmediatamente y envien una notificación para poder proceder ya sea con trabajo o con el proceso de abono. Por ahora no vamos a trabajar con facturacion electronica porque estoy tramitando la firma y poniendo al dia el RUC. El servicio técnico actualmente se especializa en brindar mantenimiento y reparación a domicilio, no poseemos local por lo cual no vamos a desarrollar todavia un sistema de inventario]

## 2. Dashboard
incluye las estadisticas genenrales, ordenes de servicio activas, cuanta pc, laptops, impresoras y telefonos hay en reparación. Equipos asiginados por técnico, cotizaciones abiertas, cerradas y cuantas ordenes cerradas que ya fueron facturadas como nota de venta (ya que la factura electronica vas ser implementada en un futuro).

## 3.Gestion de ordenes de servicio
1. Crear una orden de servicio
Campos de la creación de una orden de servicio:
  - [ ] Número de orden (auto-generado)
  - [ ] Fecha de ingreso (auto-generada)
  - [ ] Nombre del cliente (En este caso con la expresion regular de nombre y apellido primera letra mayuscula y el resto minuscula) importante poder tener una funcion de auto-complete con los clientes existentes creados con anterioridad.
  - [ ] Teléfono del cliente (con la estructura +593 de ecuador)
  - [ ] Equipo/Dispositivo
  - [ ] Descripción del problema
  - [ ] Diagnóstico
  - [ ] Trabajo a realizar
  - [ ] Repuesto a instalar
  - [ ] Datos financieros con lo campos para rellenar total orden, abono por cancelar (Por cancelar es la resta de total orden menos abono)
  - [ ] Técnico asignado (Poder asignar tecnico responsable)
  - [ ] Garantía (días esta opcion poder elegirla dependiendo del trabajo que se realizo en el equipo, por ejemplo mantenimiento de impresoras  y computadoras es de 30 días y con la opcion de no hay garatia)
  - [ ] Notas internas (Importante para que cuando revisemos las ordenes sepamos detalles importantes del servicio)
  - [ ] Numero de identificación, o RUC si el cliente es empresa 
2. Editar una orden de servicio
3. Eliminar una orden de servicio
4. Ver el historial de ordenes de servicio
5. Buscar una orden de servicio
6. Imprimir orden de servicio (en un pdf donde se muestren los siguientes datos, que solo los visibles para el cliente)
    1. Nombre del negocio (el logo png de orpey servicios)
    2. Nombre del cliente
    3. Teléfono del cliente (con la estructura +593 de ecuador)
    4. Email del cliente
    5. Dirección del cliente 
    6. Equipo/Dispositivo
    7. Descripción del problema
    8. Diagnóstico
    9. Trabajo a realizar
    10. Datos financiero como total orden, abono por cancelar (Por cancelar es la resta de total orden menos abono)
    11. Técnico asignado
    12. Garantía 
    13. Fecha de ingreso
    14. Numero de identificación, o RUC si el cliente es empresa 
    15. Terminos y condiciones del servicio tecnico:
         1. El período de vigencia de la garantía del equipo que se presente en nuestro centro de servicio se validaŕá desde la fecha indicada en la orden  de servicio.
         2. Los mantenimientos de impresoras y computadoras tienen  1 mes de garantía.
         3. No se da garantía por cabezales y cartuchos, ya que son propiedad del cliente y su vida util depende del uso correcto de los mismos.
         4. Toda pantalla de teléfonos, laptop o tablet que se instala se entrega PROBADA en su presencia, una vez sale del local no tiene garantía debido a lo delicado de dichos repuestos.
         5. Artículos eléctricos como cargadores y baterias se entregan probados ya que pueden verse afectados por factores ajenos a nuestra empresa.
         6.Equipos que se reciben por humedad o con daños causados por insectos o roedores, no tienen garantía.
         7. Los equipos no reclamados durante 30 días pasarán a ser propiedad de ORPEY SERVICIOS Técnicos
         8. ORPEY SERVICIOS Técnicos, no se hace responsable por la pérdida de información o datos guardados en los dispositivos entregados para servicio técnico
7. Poder enviar esta orden de servicio mediante whatsapp o correo electronico al cliente
8. Estados equipos: [Revisión,En reparación, Esperando repuesto, Terminada, Entregada]
9. Un boton para poder convertir en nota de venta (Utilizar la estructura de nota de venta de Ecuador ya que estoy inscrito en el SRI)

## 4. Gestion de clientes
1. Crear un cliente 
2. Editar un cliente
3. Eliminar un cliente
4. Ver el historial de clientes
5. Buscar un cliente
6. ficha del cliente (Mostrar el historial de ordenes, datos de contacto y datos de identificación, etc) y poder tener un boton con funciones para poder crear una nueva orden de servicio o una nueva cotización o contactar por medio de whatsapp o correo electronico al cliente.
7. - Campos de cada cliente:
  - [ ] Nombre del cliente (En este caso con la expresion regular de nombre y apellido primera letra mayuscula y el resto minuscula)
  - [ ] Teléfono del cliente (con la estructura +593 de ecuador)
  - [ ] Email del cliente
  - [ ] Dirección del cliente 
  - [ ] Numero de identificación, o RUC si el cliente es empresa 


### 5 Gestión de Técnicos
- [ ] Registro de técnicos
- [ ] Asignación de órdenes
- [ ] Carga de trabajo actual
- [ ] Historial de reparaciones

### 6 Configuración del Sistema
- [ ] Datos del taller (nombre, logo, dirección, teléfono)
- [ ] Plantillas de presupuesto/factura
- [ ] Gestión de usuarios y contraseñas
- [ ] Backup de base de datos

---

## 7. Base de Datos Existente
**Archivos disponibles:**
- `orpey_db_backup.sql` - Backup SQL existente
- `ORDENES_CONSOLIDADAS_FINAL.xlsx` - Datos en Excel
- `IMPORTAR_A_POSTGRES.sql` - Script de importación

**Estructura actual de la base de datos:**
[verificar los campos y cotejarlos con los datos necesarios para el sistema y editarlo para mayor eficiencia de la base de datos

## 6. Requisitos Técnicos
**Stack preferido:**
- Backend: FastAPI (Python 3.13+)
- Base de datos: PostgreSQL
- Frontend: [por definir]
- Deploy local: Docker / directo [por definir]
- Deploy nube: [Definir proveedor]

**Hardware disponible:**
- [ ] Servidor local (especificar)
- [ ] PCs del taller

## 7. Integraciones Futuras (opcional)
- [ ] WhatsApp para notificaciones
- [ ] Email 
- [ ] Portal web para clientes
- [ ] App móvil
- [ ] Facturación electrónica
- [ ] Sistema de inventario para repuestos

## 8. Usuarios y Roles
| Rol | Descripción | Permisos |
|-----|-------------|----------|
| Administrador | | | Daniel Baltodano
| Técnico | | | (Daniel Baltodano)
| Asistente | | | Sofía Soler

## 10. Observaciones Adicionales importantes para tomar en cuenta al momento de programar
- El sistema estas siendo operado en Ecuador, ciudad de Guayaquil por lo tanto se debe de tomar en cuenta la normativa ecuatoriana vigente en materia tributaria.
- Recordar que soy un principiante en lo que respecta a programacion, estoy interesado en comprender como funciona cada parte del sistema. Por lo tanto, el programador debe de explicarme cada paso que realiza, y detallar cada componente, libreria, framework, base de datos, etc. que se utiliza en el proyecto, comentar el codigo en español y detallar las funciones que realiza cada parte del codigo. lo nombres de los archivos e infraestructuras debe ser intuitivo. 
- Estoy utilizados distintos entornos de desarrollo para desarrollar el sistema, los cuales son:
  - opencode para programar el backend desde la terminal de ubuntu
  - antigravity para programar el frontend 
  - PostgreSQL
  - FastAPI

## Estilos del frontend
Utilizar un estilo moderno y limpio, con colores de orpey servicios, logo png de orpey servicios que esta alojado en la carpeta /home/skorggamor/app-orpey/datos-orpey y un diseño intuitivo.




