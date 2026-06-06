export type WeeklyExpenseItem = {
  semana: number;
  etiqueta: string;
  total: number;
};

export type MonthlyListItem = {
  id_historial: number;
  nombre_lista: string | null;
  fecha: string;
  supermercado_principal: string | null;
  total_gastado: number;
  num_productos: number;
};

export type MonthlyExpensesSummary = {
  total_mensual: number;
  variacion_vs_mes_pasado: number | null;
  media_diaria: number;
  numero_compras: number;
};

export type MonthlyExpensesResponse = {
  year: number;
  month: number;
  resumen: MonthlyExpensesSummary;
  gasto_semana: WeeklyExpenseItem[];
  listas_mes: MonthlyListItem[];
};

export type CategoryBreakdownItem = {
  categoria: string;
  porcentaje_total: number;
  gasto: number;
  num_productos: number;
};

export type CategoryProductsItem = {
  categoria: string;
  productos: string[];
};

export type CategoriesAnalyticsResponse = {
  year: number;
  month: number;
  total_mensual: number;
  categorias: CategoryBreakdownItem[];
  productos_por_categoria: CategoryProductsItem[];
};

export type DaySpendingItem = {
  dia_semana: string;
  total: number;
};

export type RepeatedListItem = {
  nombre_lista: string;
  veces: number;
};

export type SupermarketVisitItem = {
  supermercado: string;
  visitas: number;
};

export type PurchaseHabitsResponse = {
  frecuencia_general: string;
  dias_medios_entre_compras: number | null;
  dia_habitual_compra: string | null;
  gasto_por_dia_semana: DaySpendingItem[];
  rango_horario_frecuente: string | null;
  promedio_productos_por_compra: number;
  listas_repetidas: RepeatedListItem[];
  supermercados_favoritos: SupermarketVisitItem[];
};
