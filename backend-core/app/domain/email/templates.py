"""Plantillas de email marketing por rubro.

Cada rubro tiene 3 emails en secuencia:
1. Bienvenida / Presentacion (dia 0)
2. Valor / Beneficios (dia 3)
3. Oferta / Call-to-action (dia 7)

Las plantillas son predefinidas, no editables por el usuario (v1).
Usan {{business_name}} y {{contact_name}} como placeholders.
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Rubro: restaurante
# ---------------------------------------------------------------------------
RESTAURANTE_EMAIL_1_SUBJECT = "Bienvenido a {{business_name}}"
RESTAURANTE_EMAIL_1_BODY = """\
<h2>Hola {{contact_name}}, bienvenido a {{business_name}}</h2>
<p>Gracias por contactarnos. En {{business_name}} nos especializamos en ofrecerte la mejor experiencia gastronomica.</p>
<p>Nuestro menu incluye platos frescos preparados al momento, y contamos con servicio a domicilio para que disfrutes donde quieras.</p>
<p>Horario: Lunes a Domingo de 12:00 a 23:00</p>
<p>Te invitamos a conocer nuestro menu completo. Responde a este mensaje y con gusto te ayudamos.</p>
"""

RESTAURANTE_EMAIL_2_SUBJECT = "Descubre nuestros platos estrella en {{business_name}}"
RESTAURANTE_EMAIL_2_BODY = """\
<h2>{{contact_name}}, te presentamos lo mejor de {{business_name}}</h2>
<p>Nuestros clientes aman estos platos:</p>
<ul>
  <li><strong>Especialidad de la casa</strong> — Nuestro plato insignia preparado con ingredientes frescos.</li>
  <li><strong>Menu ejecutivo</strong> — Entrada, plato fuerte y bebida a un precio especial de lunes a viernes.</li>
  <li><strong>Postres artesanales</strong> — El cierre perfecto para tu comida.</li>
</ul>
<p>Haz tu reserva respondiendo a este correo o llamanos.</p>
"""

RESTAURANTE_EMAIL_3_SUBJECT = "Oferta especial para ti en {{business_name}}"
RESTAURANTE_EMAIL_3_BODY = """\
<h2>{{contact_name}}, tenemos algo especial para ti</h2>
<p>Por ser parte de nuestra comunidad, te ofrecemos:</p>
<p style="font-size: 20px; font-weight: bold; color: #d97706;">20% de descuento en tu primera reserva</p>
<p>Valido por 7 dias. Menciona el codigo <strong>WELCOME20</strong> al hacer tu reserva.</p>
<p>Responde a este correo o contactanos por WhatsApp para activar tu descuento.</p>
<p>Te esperamos en {{business_name}}.</p>
"""

# ---------------------------------------------------------------------------
# Rubro: peluqueria
# ---------------------------------------------------------------------------
PELUQUERIA_EMAIL_1_SUBJECT = "Bienvenido a {{business_name}}"
PELUQUERIA_EMAIL_1_BODY = """\
<h2>Hola {{contact_name}}, bienvenido a {{business_name}}</h2>
<p>Gracias por contactarnos. Somos tu salon de belleza de confianza.</p>
<p>Ofrecemos cortes, tintes, manicure, pedicure, peinados y tratamientos capilares con productos profesionales.</p>
<p>Agenda tu cita respondiendo a este mensaje y recibe atencion personalizada.</p>
"""

PELUQUERIA_EMAIL_2_SUBJECT = "Servicios destacados de {{business_name}}"
PELUQUERIA_EMAIL_2_BODY = """\
<h2>{{contact_name}}, conoce nuestros servicios mas populares</h2>
<ul>
  <li><strong>Corte y peinado</strong> — Estilismo personalizado segun tu tipo de rostro.</li>
  <li><strong>Coloracion profesional</strong> — Tintes, mechas y balayage con productos importados.</li>
  <li><strong>Tratamientos capilares</strong> — Keratina, botox y nutricion profunda.</li>
</ul>
<p>Consulta precios y disponibilidad respondiendo a este correo.</p>
"""

PELUQUERIA_EMAIL_3_SUBJECT = "Descuento exclusivo en {{business_name}}"
PELUQUERIA_EMAIL_3_BODY = """\
<h2>{{contact_name}}, un regalo para ti</h2>
<p style="font-size: 20px; font-weight: bold; color: #d97706;">15% de descuento en tu primer servicio</p>
<p>Aplica en corte, tinte o cualquier tratamiento. Menciona el codigo <strong>BELLEZA15</strong>.</p>
<p>Valido por 7 dias. Agenda tu cita ahora.</p>
"""

# ---------------------------------------------------------------------------
# Rubro: clinica
# ---------------------------------------------------------------------------
CLINICA_EMAIL_1_SUBJECT = "Bienvenido a {{business_name}}"
CLINICA_EMAIL_1_BODY = """\
<h2>Hola {{contact_name}}, bienvenido a {{business_name}}</h2>
<p>Gracias por confiar en nosotros para tu salud. Somos un centro medico comprometido con tu bienestar.</p>
<p>Ofrecemos consultas medicas generales, odontologia, especialidades y estudios diagnosticos.</p>
<p>Responde a este mensaje para agendar tu consulta o conocer nuestros horarios.</p>
"""

CLINICA_EMAIL_2_SUBJECT = "Nuestros servicios medicos en {{business_name}}"
CLINICA_EMAIL_2_BODY = """\
<h2>{{contact_name}}, conoce como podemos ayudarte</h2>
<ul>
  <li><strong>Medicina general</strong> — Consultas de rutina, chequeos y seguimiento.</li>
  <li><strong>Odontologia</strong> — Limpieza, caries, brackets y estetica dental.</li>
  <li><strong>Especialidades</strong> — Cardiologia, dermatologia, pediatria y mas.</li>
</ul>
<p>Agenda tu consulta con nosotros. Tu salud es primero.</p>
"""

CLINICA_EMAIL_3_SUBJECT = "Chequeo preventivo con descuento en {{business_name}}"
CLINICA_EMAIL_3_BODY = """\
<h2>{{contact_name}}, cuida tu salud</h2>
<p style="font-size: 20px; font-weight: bold; color: #d97706;">30% de descuento en tu primer chequeo general</p>
<p>Incluye consulta medica, toma de signos vitales y orientacion nutricional basica.</p>
<p>Menciona el codigo <strong>SALUD30</strong>. Valido por 15 dias.</p>
"""

# ---------------------------------------------------------------------------
# Rubro: tienda
# ---------------------------------------------------------------------------
TIENDA_EMAIL_1_SUBJECT = "Bienvenido a {{business_name}}"
TIENDA_EMAIL_1_BODY = """\
<h2>Hola {{contact_name}}, bienvenido a {{business_name}}</h2>
<p>Gracias por visitarnos. Somos tu tienda de confianza con los mejores productos.</p>
<p>Contamos con un amplio catalogo en moda, hogar, tecnologia y mas. Pregunta por lo que buscas y te ayudamos a encontrarlo.</p>
"""

TIENDA_EMAIL_2_SUBJECT = "Novedades y productos destacados de {{business_name}}"
TIENDA_EMAIL_2_BODY = """\
<h2>{{contact_name}}, mira lo que tenemos para ti</h2>
<ul>
  <li><strong>Nuevos ingresos</strong> — Productos recien llegados esta temporada.</li>
  <li><strong>Ofertas de la semana</strong> — Descuentos especiales en productos seleccionados.</li>
  <li><strong>Envio a domicilio</strong> — Recibe tu compra donde estes, rapido y seguro.</li>
</ul>
<p>Responde a este correo y te mostramos lo que buscas.</p>
"""

TIENDA_EMAIL_3_SUBJECT = "Descuento especial en tu primera compra en {{business_name}}"
TIENDA_EMAIL_3_BODY = """\
<h2>{{contact_name}}, una oferta exclusiva</h2>
<p style="font-size: 20px; font-weight: bold; color: #d97706;">10% de descuento en tu primera compra</p>
<p>Valido en todos nuestros productos. Usa el codigo <strong>TIENDA10</strong>.</p>
<p>Visitanos o responde a este correo para hacer tu pedido.</p>
"""

# ---------------------------------------------------------------------------
# Rubro: inmobiliaria
# ---------------------------------------------------------------------------
INMOBILIARIA_EMAIL_1_SUBJECT = "Bienvenido a {{business_name}}"
INMOBILIARIA_EMAIL_1_BODY = """\
<h2>Hola {{contact_name}}, bienvenido a {{business_name}}</h2>
<p>Gracias por tu interes en el mercado inmobiliario. Somos expertos en ayudarte a encontrar la propiedad ideal.</p>
<p>Contamos con un amplio catalogo de casas, departamentos, terrenos y locales comerciales en las mejores zonas.</p>
<p>Cuentanos que buscas y te enviamos opciones personalizadas.</p>
"""

INMOBILIARIA_EMAIL_2_SUBJECT = "Propiedades destacadas de {{business_name}}"
INMOBILIARIA_EMAIL_2_BODY = """\
<h2>{{contact_name}}, estas son nuestras propiedades recomendadas</h2>
<ul>
  <li><strong>Departamentos</strong> — Desde 1 hasta 3 habitaciones en zonas centricas.</li>
  <li><strong>Casas</strong> — Con jardin, cochera y excelente ubicacion.</li>
  <li><strong>Terrenos</strong> — Ideales para construccion o inversion.</li>
</ul>
<p>Agenda una visita respondiendo a este correo. Te acompanamos en todo el proceso.</p>
"""

INMOBILIARIA_EMAIL_3_SUBJECT = "Calcula tu hipoteca con {{business_name}}"
INMOBILIARIA_EMAIL_3_BODY = """\
<h2>{{contact_name}}, da el primer paso hacia tu nuevo hogar</h2>
<p>Te ofrecemos:</p>
<p style="font-size: 20px; font-weight: bold; color: #d97706;">Asesoria gratuita de credito hipotecario</p>
<p>Nuestros asesores te ayudan a calcular tu capacidad de credito y encontrar la mejor tasa del mercado.</p>
<p>Sin compromiso. Responde a este correo y un asesor te contactara en 24 horas.</p>
"""

# ---------------------------------------------------------------------------
# Rubro: gimnasio
# ---------------------------------------------------------------------------
GIMNASIO_EMAIL_1_SUBJECT = "Bienvenido a {{business_name}}"
GIMNASIO_EMAIL_1_BODY = """\
<h2>Hola {{contact_name}}, bienvenido a {{business_name}}</h2>
<p>Gracias por tu interes en entrenar con nosotros. Somos el gimnasio que te ayuda a alcanzar tus metas.</p>
<p>Contamos con equipos de ultima generacion, clases grupales (yoga, spinning, funcional) y entrenadores certificados.</p>
<p>Ven a conocernos. Tu primera clase es gratis.</p>
"""

GIMNASIO_EMAIL_2_SUBJECT = "Clases y planes en {{business_name}}"
GIMNASIO_EMAIL_2_BODY = """\
<h2>{{contact_name}}, descubre todo lo que tenemos</h2>
<ul>
  <li><strong>Planes de membresia</strong> — Mensual, trimestral y anual con precios especiales.</li>
  <li><strong>Clases grupales</strong> — Yoga, spinning, zumba, boxeo y funcional.</li>
  <li><strong>Entrenamiento personalizado</strong> — Planes disenados por entrenadores certificados.</li>
</ul>
<p>Pregunta por nuestros horarios y precios.</p>
"""

GIMNASIO_EMAIL_3_SUBJECT = "Oferta de bienvenida en {{business_name}}"
GIMNASIO_EMAIL_3_BODY = """\
<h2>{{contact_name}}, empieza a entrenar hoy</h2>
<p style="font-size: 20px; font-weight: bold; color: #d97706;">50% de descuento en tu primer mes</p>
<p>Incluye acceso ilimitado a todas las areas y clases grupales sin costo adicional.</p>
<p>Menciona el codigo <strong>FUERZA50</strong>. Valido por 7 dias.</p>
"""

# ---------------------------------------------------------------------------
# Rubro: contador
# ---------------------------------------------------------------------------
CONTADOR_EMAIL_1_SUBJECT = "Bienvenido a {{business_name}}"
CONTADOR_EMAIL_1_BODY = """\
<h2>Hola {{contact_name}}, bienvenido a {{business_name}}</h2>
<p>Gracias por confiar en nosotros para tus temas contables y fiscales. Somos un estudio contable con amplia experiencia.</p>
<p>Ofrecemos declaraciones de impuestos, contabilidad empresarial, asesoria fiscal y gestion de nominas.</p>
<p>Agenda una consulta gratuita respondiendo a este correo.</p>
"""

CONTADOR_EMAIL_2_SUBJECT = "Servicios contables de {{business_name}}"
CONTADOR_EMAIL_2_BODY = """\
<h2>{{contact_name}}, como podemos ayudarte</h2>
<ul>
  <li><strong>Declaraciones fiscales</strong> — ISR, IVA, retenciones y regimenes especiales.</li>
  <li><strong>Contabilidad mensual</strong> — Estados financieros, balances y reportes.</li>
  <li><strong>Asesoria fiscal</strong> — Planeacion tributaria para personas fisicas y morales.</li>
</ul>
<p>Responde a este correo y un contador certificado te atendera.</p>
"""

CONTADOR_EMAIL_3_SUBJECT = "Consulta fiscal gratuita con {{business_name}}"
CONTADOR_EMAIL_3_BODY = """\
<h2>{{contact_name}}, resuelve tus dudas fiscales</h2>
<p style="font-size: 20px; font-weight: bold; color: #d97706;">Primera consulta fiscal sin costo</h2>
<p>Te ayudamos a revisar tu situacion fiscal actual y encontrar oportunidades de ahorro.</p>
<p>Sin compromiso. Responde a este correo para agendar tu consulta.</p>
"""

# ---------------------------------------------------------------------------
# Rubro: taller
# ---------------------------------------------------------------------------
TALLER_EMAIL_1_SUBJECT = "Bienvenido a {{business_name}}"
TALLER_EMAIL_1_BODY = """\
<h2>Hola {{contact_name}}, bienvenido a {{business_name}}</h2>
<p>Gracias por contactarnos. Somos tu taller mecanico de confianza.</p>
<p>Ofrecemos mantenimiento preventivo, reparacion general, diagnostico computarizado, frenos, suspension y mucho mas.</p>
<p>Agenda tu cita respondiendo a este mensaje.</p>
"""

TALLER_EMAIL_2_SUBJECT = "Servicios mecanicos de {{business_name}}"
TALLER_EMAIL_2_BODY = """\
<h2>{{contact_name}}, conoce nuestros servicios</h2>
<ul>
  <li><strong>Mantenimiento preventivo</strong> — Cambio de aceite, filtros, bujias y revision general.</li>
  <li><strong>Frenos y suspension</strong> — Revision y cambio de balatas, amortiguadores y rotulas.</li>
  <li><strong>Diagnostico computarizado</strong> — Escaneo completo con equipo profesional.</li>
</ul>
<p>Solicita tu cotizacion sin costo.</p>
"""

TALLER_EMAIL_3_SUBJECT = "Descuento en servicio para {{business_name}}"
TALLER_EMAIL_3_BODY = """\
<h2>{{contact_name}}, una oferta para tu auto</h2>
<p style="font-size: 20px; font-weight: bold; color: #d97706;">15% de descuento en tu primer servicio</p>
<p>Valido en mantenimiento preventivo o diagnostico computarizado. Menciona el codigo <strong>TALLER15</strong>.</p>
<p>Agenda tu cita hoy. Valido por 15 dias.</p>
"""

# ---------------------------------------------------------------------------
# Rubro: hotel
# ---------------------------------------------------------------------------
HOTEL_EMAIL_1_SUBJECT = "Bienvenido a {{business_name}}"
HOTEL_EMAIL_1_BODY = """\
<h2>Hola {{contact_name}}, bienvenido a {{business_name}}</h2>
<p>Gracias por tu interes en hospedarte con nosotros. Somos el lugar perfecto para tu descanso.</p>
<p>Ofrecemos habitaciones comodas, servicio de restaurante, alberca, spa y atencion personalizada las 24 horas.</p>
<p>Consulta disponibilidad y tarifas respondiendo a este mensaje.</p>
"""

HOTEL_EMAIL_2_SUBJECT = "Servicios y amenidades de {{business_name}}"
HOTEL_EMAIL_2_BODY = """\
<h2>{{contact_name}}, descubre lo que ofrecemos</h2>
<ul>
  <li><strong>Habitaciones</strong> — Sencillas, dobles y suites con todas las comodidades.</li>
  <li><strong>Restaurante</strong> — Desayuno buffet y cenas a la carta.</li>
  <li><strong>Alberca y spa</strong> — Relajate en nuestras instalaciones.</li>
</ul>
<p>Responde para recibir nuestras tarifas especiales.</p>
"""

HOTEL_EMAIL_3_SUBJECT = "Tarifa especial en {{business_name}}"
HOTEL_EMAIL_3_BODY = """\
<h2>{{contact_name}}, reserva con descuento</h2>
<p style="font-size: 20px; font-weight: bold; color: #d97706;">25% de descuento en tu primera reserva</p>
<p>Incluye desayuno buffet para dos personas. Menciona el codigo <strong>HOTEL25</strong>.</p>
<p>Valido para estancias de minimo 2 noches. Reserva ahora.</p>
"""

# ---------------------------------------------------------------------------
# Rubro: ecommerce
# ---------------------------------------------------------------------------
ECOMMERCE_EMAIL_1_SUBJECT = "Bienvenido a {{business_name}}"
ECOMMERCE_EMAIL_1_BODY = """\
<h2>Hola {{contact_name}}, bienvenido a {{business_name}}</h2>
<p>Gracias por visitar nuestra tienda online. Somos tu destino para comprar desde casa.</p>
<p>Contamos con miles de productos en moda, electronica, hogar, deportes y mucho mas con envio a todo el pais.</p>
<p>Explora nuestro catalogo y pregunta por lo que necesites.</p>
"""

ECOMMERCE_EMAIL_2_SUBJECT = "Novedades y ofertas de {{business_name}}"
ECOMMERCE_EMAIL_2_BODY = """\
<h2>{{contact_name}}, no te pierdas nuestras ofertas</h2>
<ul>
  <li><strong>Ofertas relampago</strong> — Descuentos por tiempo limitado cada semana.</li>
  <li><strong>Nuevos productos</strong> — Lo mas reciente en todas nuestras categorias.</li>
  <li><strong>Envio gratis</strong> — En pedidos superiores a $999.</li>
</ul>
<p>Visita nuestra tienda o responde a este correo para recibir recomendaciones.</p>
"""

ECOMMERCE_EMAIL_3_SUBJECT = "Cupon de bienvenida en {{business_name}}"
ECOMMERCE_EMAIL_3_BODY = """\
<h2>{{contact_name}}, un regalo por unirte</h2>
<p style="font-size: 20px; font-weight: bold; color: #d97706;">15% de descuento en tu primer pedido</p>
<p>Usa el codigo <strong>ECOMMERCE15</strong> al finalizar tu compra. Sin minimo de compra.</p>
<p>Valido por 7 dias. Empieza a comprar ahora.</p>
"""


@dataclass(frozen=True, slots=True)
class EmailTemplate:
    """Una plantilla de email individual (sujeto + cuerpo)."""
    subject: str
    body_html: str


@dataclass(frozen=True, slots=True)
class RubroEmailSequence:
    """Secuencia de 3 emails para un rubro especifico."""
    slug: str
    emails: tuple[EmailTemplate, EmailTemplate, EmailTemplate]


def _build_sequence(slug: str, e1_subj: str, e1_body: str, e2_subj: str, e2_body: str, e3_subj: str, e3_body: str) -> RubroEmailSequence:
    return RubroEmailSequence(
        slug=slug,
        emails=(
            EmailTemplate(subject=e1_subj, body_html=e1_body),
            EmailTemplate(subject=e2_subj, body_html=e2_body),
            EmailTemplate(subject=e3_subj, body_html=e3_body),
        ),
    )


EMAIL_SEQUENCES: list[RubroEmailSequence] = [
    _build_sequence("restaurante", RESTAURANTE_EMAIL_1_SUBJECT, RESTAURANTE_EMAIL_1_BODY, RESTAURANTE_EMAIL_2_SUBJECT, RESTAURANTE_EMAIL_2_BODY, RESTAURANTE_EMAIL_3_SUBJECT, RESTAURANTE_EMAIL_3_BODY),
    _build_sequence("peluqueria", PELUQUERIA_EMAIL_1_SUBJECT, PELUQUERIA_EMAIL_1_BODY, PELUQUERIA_EMAIL_2_SUBJECT, PELUQUERIA_EMAIL_2_BODY, PELUQUERIA_EMAIL_3_SUBJECT, PELUQUERIA_EMAIL_3_BODY),
    _build_sequence("clinica", CLINICA_EMAIL_1_SUBJECT, CLINICA_EMAIL_1_BODY, CLINICA_EMAIL_2_SUBJECT, CLINICA_EMAIL_2_BODY, CLINICA_EMAIL_3_SUBJECT, CLINICA_EMAIL_3_BODY),
    _build_sequence("tienda", TIENDA_EMAIL_1_SUBJECT, TIENDA_EMAIL_1_BODY, TIENDA_EMAIL_2_SUBJECT, TIENDA_EMAIL_2_BODY, TIENDA_EMAIL_3_SUBJECT, TIENDA_EMAIL_3_BODY),
    _build_sequence("inmobiliaria", INMOBILIARIA_EMAIL_1_SUBJECT, INMOBILIARIA_EMAIL_1_BODY, INMOBILIARIA_EMAIL_2_SUBJECT, INMOBILIARIA_EMAIL_2_BODY, INMOBILIARIA_EMAIL_3_SUBJECT, INMOBILIARIA_EMAIL_3_BODY),
    _build_sequence("gimnasio", GIMNASIO_EMAIL_1_SUBJECT, GIMNASIO_EMAIL_1_BODY, GIMNASIO_EMAIL_2_SUBJECT, GIMNASIO_EMAIL_2_BODY, GIMNASIO_EMAIL_3_SUBJECT, GIMNASIO_EMAIL_3_BODY),
    _build_sequence("contador", CONTADOR_EMAIL_1_SUBJECT, CONTADOR_EMAIL_1_BODY, CONTADOR_EMAIL_2_SUBJECT, CONTADOR_EMAIL_2_BODY, CONTADOR_EMAIL_3_SUBJECT, CONTADOR_EMAIL_3_BODY),
    _build_sequence("taller", TALLER_EMAIL_1_SUBJECT, TALLER_EMAIL_1_BODY, TALLER_EMAIL_2_SUBJECT, TALLER_EMAIL_2_BODY, TALLER_EMAIL_3_SUBJECT, TALLER_EMAIL_3_BODY),
    _build_sequence("hotel", HOTEL_EMAIL_1_SUBJECT, HOTEL_EMAIL_1_BODY, HOTEL_EMAIL_2_SUBJECT, HOTEL_EMAIL_2_BODY, HOTEL_EMAIL_3_SUBJECT, HOTEL_EMAIL_3_BODY),
    _build_sequence("ecommerce", ECOMMERCE_EMAIL_1_SUBJECT, ECOMMERCE_EMAIL_1_BODY, ECOMMERCE_EMAIL_2_SUBJECT, ECOMMERCE_EMAIL_2_BODY, ECOMMERCE_EMAIL_3_SUBJECT, ECOMMERCE_EMAIL_3_BODY),
]

EMAIL_SEQUENCES_BY_SLUG: dict[str, RubroEmailSequence] = {s.slug: s for s in EMAIL_SEQUENCES}


def get_email_template(rubro_slug: str, sequence_number: int) -> EmailTemplate:
    """Obtiene la plantilla de email para un rubro y numero de secuencia (1, 2, o 3)."""
    seq = EMAIL_SEQUENCES_BY_SLUG.get(rubro_slug)
    if seq is None:
        raise ValueError(f"Invalid rubro: {rubro_slug}")
    if sequence_number not in (1, 2, 3):
        raise ValueError(f"Invalid sequence_number: {sequence_number}. Must be 1, 2, or 3.")
    return seq.emails[sequence_number - 1]


def get_all_rubro_slugs() -> list[str]:
    """Retorna todos los slugs de rubro con plantillas de email."""
    return list(EMAIL_SEQUENCES_BY_SLUG.keys())
