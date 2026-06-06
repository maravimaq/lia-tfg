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
import { CategoriesAnalyticsResponse } from "@/src/types/analytics";

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

export default function CategoriesAnalyticsScreen() {
  const { colors, isDarkMode } = useAppTheme();
  const styles = useMemo(() => createStyles(colors, isDarkMode), [colors, isDarkMode]);
  const initialMonth = useMemo(() => getCurrentMonthState(), []);
  const [year, setYear] = useState(initialMonth.year);
  const [month, setMonth] = useState(initialMonth.month);
  const [data, setData] = useState<CategoriesAnalyticsResponse | null>(null);
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

        const response = await analyticsService.getCategories(year, month);
        setData(response);
      } catch (err: any) {
        setError(
          err?.response?.data?.detail ||
            "No se pudieron cargar las analíticas de categorías."
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

      <Text style={styles.title}>Categorías más compradas</Text>

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
            <Text style={styles.summaryText}>Gasto total categorizado: <Text style={styles.bold}>{formatCurrency(data.total_mensual)}</Text></Text>
            <Text style={styles.summaryText}>Categorías detectadas: <Text style={styles.bold}>{data.categorias.length}</Text></Text>
          </View>

          <View style={styles.card}>
            <Text style={styles.sectionTitle}>Distribución por categoría</Text>

            {data.categorias.length === 0 ? (
              <Text style={styles.emptyText}>No hay categorías registradas en este mes.</Text>
            ) : (
              data.categorias.map((category) => (
                <View key={category.categoria} style={styles.categoryBlock}>
                  <View style={styles.categoryHeader}>
                    <Text style={styles.categoryName}>{category.categoria}</Text>
                    <Text style={styles.categoryAmount}>{formatCurrency(category.gasto)}</Text>
                  </View>

                  <View style={styles.progressTrack}>
                    <View
                      style={[
                        styles.progressFill,
                        { width: `${Math.min(category.porcentaje_total, 100)}%` },
                      ]}
                    />
                  </View>

                  <View style={styles.categoryMetaRow}>
                    <Text style={styles.categoryMeta}>{category.porcentaje_total.toFixed(1).replace(".", ",")}% del total</Text>
                    <Text style={styles.categoryMeta}>{category.num_productos} productos</Text>
                  </View>
                </View>
              ))
            )}
          </View>

          <View style={styles.card}>
            <Text style={styles.sectionTitle}>Tabla detallada</Text>

            <View style={styles.tableHeader}>
              <Text style={[styles.tableCell, styles.tableHeaderText]}>Categoría</Text>
              <Text style={[styles.tableCell, styles.tableHeaderText]}>%</Text>
              <Text style={[styles.tableCell, styles.tableHeaderText]}>Gasto</Text>
            </View>

            {data.categorias.map((category) => (
              <View key={`row-${category.categoria}`} style={styles.tableRow}>
                <Text style={styles.tableCell}>{category.categoria}</Text>
                <Text style={styles.tableCell}>{category.porcentaje_total.toFixed(1).replace(".", ",")}%</Text>
                <Text style={styles.tableCell}>{formatCurrency(category.gasto)}</Text>
              </View>
            ))}
          </View>

          <View style={styles.card}>
            <Text style={styles.sectionTitle}>Productos/Categoría</Text>

            {data.productos_por_categoria.length === 0 ? (
              <Text style={styles.emptyText}>No hay productos agrupados por categoría.</Text>
            ) : (
              data.productos_por_categoria.map((group) => (
                <View key={group.categoria} style={styles.productGroup}>
                  <Text style={styles.productCategory}>{group.categoria}</Text>
                  <Text style={styles.productList}>{group.productos.join(", ")}</Text>
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
      gap: 6,
    },
    sectionTitle: {
      color: colors.title,
      fontSize: 17,
      fontWeight: "900",
      marginBottom: 12,
    },
    summaryText: {
      color: colors.text,
      fontSize: 14,
    },
    bold: {
      color: colors.title,
      fontWeight: "900",
    },
    categoryBlock: {
      marginBottom: 16,
      gap: 7,
    },
    categoryHeader: {
      flexDirection: "row",
      justifyContent: "space-between",
      alignItems: "center",
      gap: 12,
    },
    categoryName: {
      flex: 1,
      color: colors.title,
      fontSize: 15,
      fontWeight: "900",
    },
    categoryAmount: {
      color: colors.title,
      fontSize: 14,
      fontWeight: "900",
    },
    progressTrack: {
      height: 12,
      borderRadius: 999,
      backgroundColor: colors.card,
      overflow: "hidden",
      borderWidth: 1,
      borderColor: colors.border,
    },
    progressFill: {
      height: "100%",
      borderRadius: 999,
      backgroundColor: colors.lightPurple,
    },
    categoryMetaRow: {
      flexDirection: "row",
      justifyContent: "space-between",
      gap: 12,
    },
    categoryMeta: {
      color: colors.textMuted,
      fontSize: 12,
      fontWeight: "700",
    },
    tableHeader: {
      flexDirection: "row",
      backgroundColor: colors.card,
      borderWidth: 1,
      borderColor: colors.border,
      borderTopLeftRadius: 12,
      borderTopRightRadius: 12,
    },
    tableRow: {
      flexDirection: "row",
      borderLeftWidth: 1,
      borderRightWidth: 1,
      borderBottomWidth: 1,
      borderColor: colors.border,
    },
    tableCell: {
      flex: 1,
      color: colors.text,
      fontSize: 13,
      paddingVertical: 9,
      paddingHorizontal: 8,
      textAlign: "center",
    },
    tableHeaderText: {
      color: colors.title,
      fontWeight: "900",
    },
    productGroup: {
      borderBottomWidth: 1,
      borderBottomColor: colors.border,
      paddingVertical: 10,
      gap: 4,
    },
    productCategory: {
      color: colors.title,
      fontSize: 14,
      fontWeight: "900",
    },
    productList: {
      color: colors.text,
      fontSize: 13,
      lineHeight: 19,
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
