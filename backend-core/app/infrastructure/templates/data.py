"""Datos de las 10 plantillas de servicio predefinidas."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.shared.errors import TemplateNotFoundError


@dataclass(frozen=True, slots=True)
class ToolDef:
    """Definición de una herramienta para el agente."""
    name: str
    description: str
    endpoint: str


@dataclass(frozen=True, slots=True)
class ClientTemplateConfig:
    """Configuración del cliente en una plantilla."""
    business_type: str
    default_name: str


@dataclass(frozen=True, slots=True)
class AgentTemplateConfig:
    """Configuración del agente en una plantilla."""
    personality: str
    tools: list[ToolDef] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class TemplateDef:
    """Definición completa de una plantilla de servicio."""
    slug: str
    name: str
    emoji: str
    description: str
    client_config: ClientTemplateConfig
    agent_config: AgentTemplateConfig


# ============================================================================
# Las 10 Plantillas de Servicio
# ============================================================================

TEMPLATES: list[TemplateDef] = [
    # 🍕 Restaurante
    TemplateDef(
        slug="restaurante",
        name="Restaurante",
        emoji="🍕",
        description="Atención al cliente para restaurantes: reservas, menú, horarios y pedidos a domicilio.",
        client_config=ClientTemplateConfig(
            business_type="restaurante",
            default_name="Mi Restaurante",
        ),
        agent_config=AgentTemplateConfig(
            personality=(
                "Eres un experto en atención restaurantera. "
                "Saludas cordialmente, recomiendas platos del menú, "
                "gestionas reservas de mesas, consultas horarios y "
                "procesas pedidos a domicilio. Tu tono es amable y profesional."
            ),
            tools=[
                ToolDef(name="reservar_mesa", description="Reserva una mesa en el restaurante", endpoint="https://n8n.agencia-ia.local/webhook/reservar_mesa"),
                ToolDef(name="ver_menu", description="Muestra el menú del día y carta completa", endpoint="https://n8n.agencia-ia.local/webhook/ver_menu"),
                ToolDef(name="consultar_horarios", description="Consulta horarios de apertura y cierre", endpoint="https://n8n.agencia-ia.local/webhook/consultar_horarios"),
                ToolDef(name="pedir_domicilio", description="Procesa un pedido para entrega a domicilio", endpoint="https://n8n.agencia-ia.local/webhook/pedir_domicilio"),
            ],
        ),
    ),
    # 💈 Peluquería
    TemplateDef(
        slug="peluqueria",
        name="Peluquería",
        emoji="💈",
        description="Asistente para salones de belleza: agendamiento de citas, precios y servicios.",
        client_config=ClientTemplateConfig(
            business_type="peluqueria",
            default_name="Mi Peluquería",
        ),
        agent_config=AgentTemplateConfig(
            personality=(
                "Eres un asistente de salón de belleza profesional y amigable. "
                "Ayudas a clientes a agendar citas, consultar precios de servicios "
                "como cortes, tintes, manicure y peinados. Envías recordatorios "
                "automáticos y recomiendas productos capilares."
            ),
            tools=[
                ToolDef(name="agendar_cita", description="Agenda una cita en la peluquería", endpoint="https://n8n.agencia-ia.local/webhook/agendar_cita"),
                ToolDef(name="consultar_precios", description="Consulta los precios de los servicios disponibles", endpoint="https://n8n.agencia-ia.local/webhook/consultar_precios"),
                ToolDef(name="ver_servicios", description="Muestra el catálogo completo de servicios", endpoint="https://n8n.agencia-ia.local/webhook/ver_servicios"),
                ToolDef(name="recordatorio", description="Envía recordatorio de cita próxima al cliente", endpoint="https://n8n.agencia-ia.local/webhook/recordatorio"),
            ],
        ),
    ),
    # 🏥 Clínica
    TemplateDef(
        slug="clinica",
        name="Clínica / Consultorio",
        emoji="🏥",
        description="Asistente médico-odontológico: agendamiento de consultas, horarios y preguntas frecuentes.",
        client_config=ClientTemplateConfig(
            business_type="clinica",
            default_name="Mi Clínica",
        ),
        agent_config=AgentTemplateConfig(
            personality=(
                "Eres un asistente médico profesional, empático y confiable. "
                "Gestionas agendas de consultas médicas y odontológicas, "
                "proporcionas horarios disponibles, envías recordatorios de "
                "citas y respondes preguntas frecuentes sobre servicios clínicos."
            ),
            tools=[
                ToolDef(name="agendar_consulta", description="Agenda una consulta médica u odontológica", endpoint="https://n8n.agencia-ia.local/webhook/agendar_consulta"),
                ToolDef(name="ver_horarios", description="Muestra horarios disponibles del consultorio", endpoint="https://n8n.agencia-ia.local/webhook/ver_horarios"),
                ToolDef(name="recordar_cita", description="Envía recordatorio de consulta próxima", endpoint="https://n8n.agencia-ia.local/webhook/recordar_cita"),
                ToolDef(name="preguntas_frecuentes", description="Responde preguntas frecuentes sobre servicios médicos", endpoint="https://n8n.agencia-ia.local/webhook/preguntas_frecuentes"),
            ],
        ),
    ),
    # 🏪 Tienda
    TemplateDef(
        slug="tienda",
        name="Tienda / Retail",
        emoji="🏪",
        description="Asistente de ventas retail: búsqueda de productos, precios, disponibilidad y seguimiento.",
        client_config=ClientTemplateConfig(
            business_type="tienda",
            default_name="Mi Tienda",
        ),
        agent_config=AgentTemplateConfig(
            personality=(
                "Eres un asistente de ventas retail entusiasta y servicial. "
                "Ayudas a clientes a buscar productos, consultar precios, "
                "verificar disponibilidad en tienda y dar seguimiento a sus "
                "pedidos. Recomiendas productos complementarios."
            ),
            tools=[
                ToolDef(name="buscar_producto", description="Busca productos en el catálogo", endpoint="https://n8n.agencia-ia.local/webhook/buscar_producto"),
                ToolDef(name="ver_precio", description="Consulta el precio de un producto específico", endpoint="https://n8n.agencia-ia.local/webhook/ver_precio"),
                ToolDef(name="disponibilidad", description="Verifica disponibilidad de producto en tienda", endpoint="https://n8n.agencia-ia.local/webhook/disponibilidad"),
                ToolDef(name="seguimiento_pedido", description="Da seguimiento al estado de un pedido", endpoint="https://n8n.agencia-ia.local/webhook/seguimiento_pedido"),
            ],
        ),
    ),
    # 🏠 Inmobiliaria
    TemplateDef(
        slug="inmobiliaria",
        name="Inmobiliaria",
        emoji="🏠",
        description="Asesor inmobiliario virtual: visitas a propiedades, cálculos de hipoteca y contacto con asesores.",
        client_config=ClientTemplateConfig(
            business_type="inmobiliaria",
            default_name="Mi Inmobiliaria",
        ),
        agent_config=AgentTemplateConfig(
            personality=(
                "Eres un asesor inmobiliario profesional y persuasivo. "
                "Ayudas a clientes a agendar visitas a propiedades, "
                "mostrar catálogo de inmuebles disponibles, calcular "
                "estimaciones de hipoteca y conectar con un asesor real. "
                "Tu tono es confiable y entusiasta."
            ),
            tools=[
                ToolDef(name="agendar_visita", description="Agenda una visita a una propiedad", endpoint="https://n8n.agencia-ia.local/webhook/agendar_visita"),
                ToolDef(name="ver_propiedades", description="Muestra el catálogo de propiedades disponibles", endpoint="https://n8n.agencia-ia.local/webhook/ver_propiedades"),
                ToolDef(name="calcular_hipoteca", description="Calcula una estimación de hipoteca mensual", endpoint="https://n8n.agencia-ia.local/webhook/calcular_hipoteca"),
                ToolDef(name="contacto_asesor", description="Conecta al cliente con un asesor inmobiliario real", endpoint="https://n8n.agencia-ia.local/webhook/contacto_asesor"),
            ],
        ),
    ),
    # 💪 Gimnasio
    TemplateDef(
        slug="gimnasio",
        name="Gimnasio / Fitness",
        emoji="💪",
        description="Coach fitness virtual: agendamiento de clases, planes de membresía y horarios.",
        client_config=ClientTemplateConfig(
            business_type="gimnasio",
            default_name="Mi Gimnasio",
        ),
        agent_config=AgentTemplateConfig(
            personality=(
                "Eres un coach fitness motivador y enérgico. Ayudas a "
                "miembros del gimnasio a agendar clases grupales, consultar "
                "planes de membresía y sus precios, revisar horarios de "
                "apertura y gestionar pausas de membresía."
            ),
            tools=[
                ToolDef(name="agendar_clase", description="Agenda una clase grupal en el gimnasio", endpoint="https://n8n.agencia-ia.local/webhook/agendar_clase"),
                ToolDef(name="ver_planes", description="Muestra los planes de membresía disponibles", endpoint="https://n8n.agencia-ia.local/webhook/ver_planes"),
                ToolDef(name="consultar_horarios", description="Consulta horarios de clases y apertura", endpoint="https://n8n.agencia-ia.local/webhook/consultar_horarios"),
                ToolDef(name="pausar_membresia", description="Solicita pausar o congelar una membresía", endpoint="https://n8n.agencia-ia.local/webhook/pausar_membresia"),
            ],
        ),
    ),
    # ⚖️ Contador
    TemplateDef(
        slug="contador",
        name="Contador / Estudio Contable",
        emoji="⚖️",
        description="Asistente contable: agendamiento de consultas, vencimientos fiscales y documentación.",
        client_config=ClientTemplateConfig(
            business_type="contador",
            default_name="Estudio Contable",
        ),
        agent_config=AgentTemplateConfig(
            personality=(
                "Eres un asistente contable formal y preciso. Ayudas a "
                "clientes a agendar consultas con el contador, recordar "
                "vencimientos fiscales importantes, responder preguntas "
                "sobre declaraciones de impuestos y recibir documentos "
                "para su procesamiento."
            ),
            tools=[
                ToolDef(name="agendar_consulta", description="Agenda una consulta con el contador", endpoint="https://n8n.agencia-ia.local/webhook/agendar_consulta"),
                ToolDef(name="recordar_vencimientos", description="Recuerda fechas de vencimientos fiscales", endpoint="https://n8n.agencia-ia.local/webhook/recordar_vencimientos"),
                ToolDef(name="preguntas_fiscales", description="Responde preguntas sobre impuestos y declaraciones", endpoint="https://n8n.agencia-ia.local/webhook/preguntas_fiscales"),
                ToolDef(name="enviar_documentos", description="Recibe y procesa documentos contables", endpoint="https://n8n.agencia-ia.local/webhook/enviar_documentos"),
            ],
        ),
    ),
    # 🔧 Taller
    TemplateDef(
        slug="taller",
        name="Taller Mecánico",
        emoji="🔧",
        description="Asistente de taller mecánico: revisiones, servicios, repuestos y seguimiento.",
        client_config=ClientTemplateConfig(
            business_type="taller",
            default_name="Mi Taller",
        ),
        agent_config=AgentTemplateConfig(
            personality=(
                "Eres un asistente de taller mecánico confiable y servicial. "
                "Ayudas a clientes a agendar revisiones, consultar servicios "
                "disponibles, solicitar repuestos y dar seguimiento al estado "
                "de las reparaciones en curso."
            ),
            tools=[
                ToolDef(name="agendar_revision", description="Agenda una revisión o mantenimiento", endpoint="https://n8n.agencia-ia.local/webhook/agendar_revision"),
                ToolDef(name="consultar_servicios", description="Muestra los servicios mecánicos disponibles", endpoint="https://n8n.agencia-ia.local/webhook/consultar_servicios"),
                ToolDef(name="pedir_repuestos", description="Solicita cotización o compra de repuestos", endpoint="https://n8n.agencia-ia.local/webhook/pedir_repuestos"),
                ToolDef(name="seguimiento", description="Consulta el estado de una reparación en curso", endpoint="https://n8n.agencia-ia.local/webhook/seguimiento"),
            ],
        ),
    ),
    # 🏨 Hotel
    TemplateDef(
        slug="hotel",
        name="Hotel / Hospedaje",
        emoji="🏨",
        description="Recepcionista hotelero virtual: reservas, check-in, servicios del hotel.",
        client_config=ClientTemplateConfig(
            business_type="hotel",
            default_name="Mi Hotel",
        ),
        agent_config=AgentTemplateConfig(
            personality=(
                "Eres un recepcionista hotelero profesional y cálido. "
                "Gestionas reservas de habitaciones, consultas de "
                "disponibilidad y tarifas, check-in de huéspedes y "
                "proporcionas información sobre servicios del hotel "
                "como restaurante, spa, piscina y horarios."
            ),
            tools=[
                ToolDef(name="reservar_habitacion", description="Reserva una habitación en el hotel", endpoint="https://n8n.agencia-ia.local/webhook/reservar_habitacion"),
                ToolDef(name="ver_disponibilidad", description="Consulta disponibilidad de habitaciones", endpoint="https://n8n.agencia-ia.local/webhook/ver_disponibilidad"),
                ToolDef(name="check_in", description="Procesa check-in de huéspedes", endpoint="https://n8n.agencia-ia.local/webhook/check_in"),
                ToolDef(name="servicios_hotel", description="Muestra los servicios disponibles del hotel", endpoint="https://n8n.agencia-ia.local/webhook/servicios_hotel"),
            ],
        ),
    ),
    # 📦 E-commerce
    TemplateDef(
        slug="ecommerce",
        name="E-commerce / Tienda Online",
        emoji="📦",
        description="Vendedor online: búsqueda de productos, precios, seguimiento y cambios/devoluciones.",
        client_config=ClientTemplateConfig(
            business_type="ecommerce",
            default_name="Mi Tienda Online",
        ),
        agent_config=AgentTemplateConfig(
            personality=(
                "Eres un vendedor online entusiasta y eficiente. Ayudas "
                "a clientes a buscar productos en el catálogo, consultar "
                "precios y ofertas, dar seguimiento a pedidos en tránsito "
                "y gestionar cambios o devoluciones post-venta."
            ),
            tools=[
                ToolDef(name="buscar_producto", description="Busca productos en el catálogo online", endpoint="https://n8n.agencia-ia.local/webhook/buscar_producto"),
                ToolDef(name="ver_precio", description="Consulta precio y ofertas de un producto", endpoint="https://n8n.agencia-ia.local/webhook/ver_precio"),
                ToolDef(name="seguimiento_pedido", description="Da seguimiento al estado de envío de un pedido", endpoint="https://n8n.agencia-ia.local/webhook/seguimiento_pedido"),
                ToolDef(name="cambios_devoluciones", description="Gestiona solicitudes de cambio o devolución", endpoint="https://n8n.agencia-ia.local/webhook/cambios_devoluciones"),
            ],
        ),
    ),
]

TEMPLATES_BY_SLUG: dict[str, TemplateDef] = {t.slug: t for t in TEMPLATES}


class TemplateService:
    """Servicio para acceder a las plantillas de servicio predefinidas."""

    def list_templates(self) -> list[TemplateDef]:
        """Retorna todas las plantillas disponibles."""
        return list(TEMPLATES)

    def get_template(self, slug: str) -> TemplateDef:
        """Retorna una plantilla por slug.

        Raises:
            TemplateNotFoundError: Si el slug no existe.
        """
        template = TEMPLATES_BY_SLUG.get(slug)
        if template is None:
            raise TemplateNotFoundError(f"Template '{slug}' not found")
        return template

    def validate_template(self, slug: str) -> bool:
        """Verifica si un slug de plantilla existe."""
        return slug in TEMPLATES_BY_SLUG
