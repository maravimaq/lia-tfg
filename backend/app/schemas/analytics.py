from __future__ import annotations

from pydantic import BaseModel, Field


class WeeklyExpenseItem(BaseModel):
    semana: int
    etiqueta: str
    total: float


class MonthlyListItem(BaseModel):
    id_historial: int
    nombre_lista: str | None
    fecha: str
    supermercado_principal: str | None
    total_gastado: float
    num_productos: int


class MonthlyExpensesSummary(BaseModel):
    total_mensual: float
    variacion_vs_mes_pasado: float | None = None
    media_diaria: float
    numero_compras: int


class MonthlyExpensesResponse(BaseModel):
    year: int
    month: int
    resumen: MonthlyExpensesSummary
    gasto_semana: list[WeeklyExpenseItem]
    listas_mes: list[MonthlyListItem]


class CategoryBreakdownItem(BaseModel):
    categoria: str
    porcentaje_total: float
    gasto: float
    num_productos: int


class CategoryProductsItem(BaseModel):
    categoria: str
    productos: list[str]


class CategoriesAnalyticsResponse(BaseModel):
    year: int
    month: int
    total_mensual: float
    categorias: list[CategoryBreakdownItem]
    productos_por_categoria: list[CategoryProductsItem]


class DaySpendingItem(BaseModel):
    dia_semana: str
    total: float


class RepeatedListItem(BaseModel):
    nombre_lista: str
    veces: int


class SupermarketVisitItem(BaseModel):
    supermercado: str
    visitas: int


class PurchaseHabitsResponse(BaseModel):
    frecuencia_general: str
    dias_medios_entre_compras: float | None = None
    dia_habitual_compra: str | None = None
    gasto_por_dia_semana: list[DaySpendingItem]
    rango_horario_frecuente: str | None = None
    promedio_productos_por_compra: float
    listas_repetidas: list[RepeatedListItem]
    supermercados_favoritos: list[SupermarketVisitItem]


class ProductConsumptionInsight(BaseModel):
    producto_actual: str
    categoria: str | None = None
    supermercado: str | None = None
    cantidad_actual: int
    unidad_medida: str | None = None
    familia_detectada: str | None = None
    compras_historicas: int
    cantidad_media_por_compra: float | None = None
    cantidad_media_mensual: float | None = None
    cantidad_total_mes_actual: float
    cantidad_esperada_restante_mes: float | None = None
    porcentaje_mes_transcurrido: float
    recomendacion_orientativa: str


class ChatbotAnalyticsContextResponse(BaseModel):
    lista_id: int
    nombre_lista: str | None = None
    cadencia_compra: dict = Field(default_factory=dict)
    productos_relevantes: list[ProductConsumptionInsight]
