import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { router } from "expo-router";

import { AppColors } from "@/src/constants/colors";
import { useAppTheme } from "@/src/hooks/useAppTheme";
import { analyticsService } from "@/src/services/analytics";
import { MonthlyExpensesResponse } from "@/src/types/analytics";

const MONTH_NAMES = [
  "Enero",
  "Febrero",
  "Marzo",
  "Abril",
  "Mayo",
  "Junio",
  "Julio",
  "Agosto",
  "Septiembre",
  "Octubre",
  "Noviembre",
  "Diciembre",
];

function formatCurrency(value: number) {
  return `${value.toFixed(2).replace(".", ",")} €`;
}

function formatShortDate(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleDateString("es-ES", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function getCurrentMonthState() {
  const now = new Date();
  return {
    year: now.getFullYear(),
    month: now.getMonth() + 1,
  };
}

function moveMonth(year: number, month: number, offset: number) {
  const date = new Date(year, month - 1 + offset, 1);
  return {
    year: date.getFullYear(),
    month: date.getMonth() + 1,
  };
}

export default function MonthlyExpensesScreen() {
  const { colors, isDarkMode } = useAppTheme();
  const styles = useMemo(() => createStyles(colors, isDarkMode), [colors, isDarkMode]);
  const initialMonth = useMemo(() => getCurrentMonthState(), []);
  const [year, setYear] = useState(initialMonth.year);
  const [month, setMonth] = useState(initialMonth.month);
  const [data, setData] = useState<MonthlyExpensesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(
    async (showRefresh = false) => {
      try {
        setError(null);
        if (showRefresh) {
          setRefreshing(true);
        } else {
          setLoading(true);
        }

        const response = await analyticsService.getMonthlyExpenses(year, month);
        setData(response);
      } catch (err: any) {
        setError(
          err?.response?.data?.detail ||
            "No se pudieron cargar las analíticas de gasto mensual."
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [year, month]
  );

  useEffect(() => {
    loadData();
  }, [loadData]);

  const maxWeeklyExpense = useMemo(() => {
    if (!data?.gasto_semana.length) return 0;
    return Math.max(...data.gasto_semana.map((item) => item.total));
  }, [data]);

  const changeMonth = (offset: number) => {
    const next = moveMonth(year, month, offset);
    setYear(next.year);
    setMonth(next.month);
  };

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={() => loadData(true)}
          tintColor={colors.primary}
          colors={[colors.primary]}
        />
      }
    >
      <Pressable style={styles.backButton} onPress={() => router.back()}>
        <Text style={styles.backText}>← Volver</Text>
      </Pressable>

      <View style={styles.headerRow}>
        <Pressable style={styles.monthButton} onPress={() => changeMonth(-1)}>
          <Text style={styles.monthButtonText}>‹</Text>
        </Pressable>

        <View style={styles.monthBox}>
          <Text style={styles.monthLabel}>Mes</Text>
          <Text style={styles.monthValue}>{MONTH_NAMES[month - 1]} {year}</Text>
        </View>

        <Pressable style={styles.monthButton} onPress={() => changeMonth(1)}>
          <Text style={styles.monthButtonText}>›</Text>
        </Pressable>
      </View>

      <Text style={styles.title}>Detalles del gasto mensual</Text>

      {loading ? (
        <View style={styles.stateCard}>
          <ActivityIndicator color={colors.primary} />
          <Text style={styles.stateText}>Cargando analíticas...</Text>
        </View>
      ) : error ? (
        <View style={styles.stateCard}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      ) : data ? (
        <>
          <View style={styles.summaryCard}>
            <Text style={styles.sectionTitle}>Resumen</Text>

            <View style={styles.summaryRow}>
              <Text style={styles.label}>Total mensual:</Text>
              <Text style={styles.value}>{formatCurrency(data.resumen.total_mensual)}</Text>
            </View>

            <View style={styles.summaryRow}>
              <Text style={styles.label}>Variación vs mes pasado:</Text>
              <Text style={styles.value}>
                {data.resumen.variacion_vs_mes_pasado === null
                  ? "Sin datos"
                  : `${data.resumen.variacion_vs_mes_pasado > 0 ? "+" : ""}${data.resumen.variacion_vs_mes_pasado.toFixed(1).replace(".", ",")}%`}
              </Text>
            </View>

            <View style={styles.summaryRow}>
              <Text style={styles.label}>Media diaria:</Text>
              <Text style={styles.value}>{formatCurrency(data.resumen.media_diaria)}</Text>
            </View>

            <View style={styles.summaryRow}>
              <Text style={styles.label}>Número de compras:</Text>
              <Text style={styles.value}>{data.resumen.numero_compras}</Text>
            </View>
          </View>

          <View style={styles.card}>
            <Text style={styles.sectionTitle}>Gasto/Semana</Text>

            <View style={styles.barChart}>
              {data.gasto_semana.map((item) => {
                const height = maxWeeklyExpense > 0 ? Math.max((item.total / maxWeeklyExpense) * 120, 4) : 4;

                return (
                  <View key={item.semana} style={styles.barItem}>
                    <View style={styles.barTrack}>
                      <View style={[styles.verticalBar, { height }]} />
                    </View>
                    <Text style={styles.barValue}>{formatCurrency(item.total)}</Text>
                    <Text style={styles.barLabel}>{item.etiqueta}</Text>
                  </View>
                );
              })}
            </View>
          </View>

          <View style={styles.card}>
            <Text style={styles.sectionTitle}>Listas del mes</Text>

            {data.listas_mes.length === 0 ? (
              <Text style={styles.emptyText}>No hay listas finalizadas en este mes.</Text>
            ) : (
              data.listas_mes.map((list) => (
                <View key={list.id_historial} style={styles.listRow}>
                  <View style={styles.listMain}>
                    <Text style={styles.listSupermarket}>
                      {list.supermercado_principal || "Sin supermercado"}
                    </Text>
                    <Text style={styles.listName}>{list.nombre_lista || "Lista sin nombre"}</Text>
                    <Text style={styles.listDate}>
                      {formatShortDate(list.fecha)} · {list.num_productos} productos
                    </Text>
                  </View>
                  <Text style={styles.listAmount}>{formatCurrency(list.total_gastado)}</Text>
                </View>
              ))
            )}
          </View>
        </>
      ) : null}
    </ScrollView>
  );
}

function createStyles(colors: AppColors, isDarkMode: boolean) {
  return StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: colors.background,
    },
    content: {
      padding: 18,
      paddingBottom: 34,
      gap: 14,
    },
    backButton: {
      alignSelf: "flex-start",
      paddingVertical: 6,
    },
    backText: {
      color: colors.title,
      fontSize: 14,
      fontWeight: "800",
    },
    headerRow: {
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "center",
      gap: 10,
    },
    monthButton: {
      width: 40,
      height: 40,
      borderRadius: 14,
      borderWidth: 1,
      borderColor: colors.border,
      backgroundColor: colors.surface,
      alignItems: "center",
      justifyContent: "center",
    },
    monthButtonText: {
      color: colors.title,
      fontSize: 28,
      lineHeight: 30,
      fontWeight: "900",
    },
    monthBox: {
      minWidth: 180,
      borderRadius: 14,
      borderWidth: 1,
      borderColor: colors.border,
      backgroundColor: colors.surface,
      paddingHorizontal: 16,
      paddingVertical: 8,
      alignItems: "center",
    },
    monthLabel: {
      color: colors.textMuted,
      fontSize: 11,
      fontWeight: "700",
    },
    monthValue: {
      color: colors.title,
      fontSize: 15,
      fontWeight: "900",
    },
    title: {
      color: colors.title,
      fontSize: 26,
      fontWeight: "900",
      textAlign: "center",
    },
    card: {
      backgroundColor: colors.surface,
      borderRadius: 18,
      borderWidth: 1,
      borderColor: colors.border,
      padding: 16,
      shadowColor: "#000",
      shadowOpacity: isDarkMode ? 0.24 : 0.05,
      shadowRadius: 8,
      shadowOffset: { width: 0, height: 3 },
      elevation: 2,
    },
    summaryCard: {
      backgroundColor: colors.card,
      borderRadius: 18,
      borderWidth: 1,
      borderColor: colors.border,
      padding: 16,
    },
    sectionTitle: {
      color: colors.title,
      fontSize: 17,
      fontWeight: "900",
      marginBottom: 12,
    },
    summaryRow: {
      flexDirection: "row",
      justifyContent: "space-between",
      gap: 12,
      marginBottom: 8,
    },
    label: {
      flex: 1,
      color: colors.text,
      fontSize: 14,
    },
    value: {
      color: colors.title,
      fontSize: 14,
      fontWeight: "800",
    },
    barChart: {
      height: 190,
      flexDirection: "row",
      alignItems: "flex-end",
      justifyContent: "space-between",
      gap: 10,
    },
    barItem: {
      flex: 1,
      alignItems: "center",
      gap: 6,
    },
    barTrack: {
      height: 125,
      width: "100%",
      justifyContent: "flex-end",
      alignItems: "center",
      borderBottomWidth: 1,
      borderBottomColor: colors.border,
    },
    verticalBar: {
      width: "70%",
      maxWidth: 46,
      borderTopLeftRadius: 8,
      borderTopRightRadius: 8,
      backgroundColor: colors.cyan,
    },
    barValue: {
      color: colors.text,
      fontSize: 11,
      fontWeight: "800",
    },
    barLabel: {
      color: colors.textMuted,
      fontSize: 10,
      textAlign: "center",
    },
    listRow: {
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "space-between",
      borderBottomWidth: 1,
      borderBottomColor: colors.border,
      paddingVertical: 12,
      gap: 12,
    },
    listMain: {
      flex: 1,
      gap: 3,
    },
    listSupermarket: {
      color: colors.primary,
      fontSize: 12,
      fontWeight: "900",
    },
    listName: {
      color: colors.title,
      fontSize: 15,
      fontWeight: "900",
    },
    listDate: {
      color: colors.textMuted,
      fontSize: 12,
    },
    listAmount: {
      color: colors.title,
      fontSize: 15,
      fontWeight: "900",
    },
    emptyText: {
      color: colors.textMuted,
      fontSize: 14,
      lineHeight: 20,
    },
    stateCard: {
      backgroundColor: colors.surface,
      borderRadius: 18,
      borderWidth: 1,
      borderColor: colors.border,
      padding: 18,
      alignItems: "center",
      gap: 10,
    },
    stateText: {
      color: colors.textMuted,
      fontSize: 14,
    },
    errorText: {
      color: colors.danger,
      fontSize: 14,
      textAlign: "center",
      lineHeight: 20,
    },
  });
}
