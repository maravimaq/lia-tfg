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
import { PurchaseHabitsResponse } from "@/src/types/analytics";

function formatCurrency(value: number) {
  return `${value.toFixed(2).replace(".", ",")} €`;
}

export default function HabitsAnalyticsScreen() {
  const { colors, isDarkMode } = useAppTheme();
  const styles = useMemo(() => createStyles(colors, isDarkMode), [colors, isDarkMode]);
  const [data, setData] = useState<PurchaseHabitsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async (showRefresh = false) => {
    try {
      setError(null);
      if (showRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      const response = await analyticsService.getHabits();
      setData(response);
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          "No se pudieron cargar los hábitos de compra."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const maxDaySpending = useMemo(() => {
    if (!data?.gasto_por_dia_semana.length) return 0;
    return Math.max(...data.gasto_por_dia_semana.map((item) => item.total));
  }, [data]);

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

      <Text style={styles.title}>Hábitos de compra</Text>

      {loading ? (
        <View style={styles.stateCard}>
          <ActivityIndicator color={colors.primary} />
          <Text style={styles.stateText}>Cargando hábitos...</Text>
        </View>
      ) : error ? (
        <View style={styles.stateCard}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      ) : data ? (
        <>
          <View style={styles.card}>
            <Text style={styles.sectionTitle}>Frecuencia general</Text>
            <Text style={styles.paragraph}>{data.frecuencia_general}</Text>

            {data.dias_medios_entre_compras !== null ? (
              <Text style={styles.mutedText}>
                Media aproximada: {data.dias_medios_entre_compras.toFixed(1).replace(".", ",")} días entre compras.
              </Text>
            ) : null}
          </View>

          <View style={styles.card}>
            <Text style={styles.sectionTitle}>Día habitual de compra</Text>
            <Text style={styles.paragraph}>
              {data.dia_habitual_compra
                ? `Sueles comprar más los ${data.dia_habitual_compra.toLowerCase()}.`
                : "Todavía no hay suficiente historial para detectar un día habitual."}
            </Text>
          </View>

          <View style={styles.card}>
            <Text style={styles.sectionTitle}>Gasto total acumulado por día</Text>

            {data.gasto_por_dia_semana.map((item) => {
              const width = maxDaySpending > 0 ? Math.max((item.total / maxDaySpending) * 100, 2) : 2;

              return (
                <View key={item.dia_semana} style={styles.dayRow}>
                  <Text style={styles.dayLabel}>{item.dia_semana}</Text>
                  <View style={styles.dayTrack}>
                    <View style={[styles.dayFill, { width: `${width}%` }]} />
                  </View>
                  <Text style={styles.dayAmount}>{formatCurrency(item.total)}</Text>
                </View>
              );
            })}
          </View>

          <View style={styles.card}>
            <Text style={styles.sectionTitle}>Horas habituales de compra</Text>
            <Text style={styles.paragraph}>
              Rango frecuente: <Text style={styles.bold}>{data.rango_horario_frecuente || "Sin datos suficientes"}</Text>
            </Text>
          </View>

          <View style={styles.card}>
            <Text style={styles.sectionTitle}>Promedio de productos por compra</Text>
            <Text style={styles.paragraph}>
              Promedio: <Text style={styles.bold}>{data.promedio_productos_por_compra.toFixed(1).replace(".", ",")} productos</Text>
            </Text>
          </View>

          <View style={styles.card}>
            <Text style={styles.sectionTitle}>Listas repetidas</Text>

            {data.listas_repetidas.length === 0 ? (
              <Text style={styles.emptyText}>No hay listas repetidas todavía.</Text>
            ) : (
              data.listas_repetidas.map((item) => (
                <Text key={item.nombre_lista} style={styles.bullet}>
                  • <Text style={styles.bold}>{item.nombre_lista}</Text> — repetida {item.veces} veces.
                </Text>
              ))
            )}
          </View>

          <View style={styles.card}>
            <Text style={styles.sectionTitle}>Supermercados favoritos</Text>

            {data.supermercados_favoritos.length === 0 ? (
              <Text style={styles.emptyText}>No hay supermercados suficientes para calcular preferencias.</Text>
            ) : (
              data.supermercados_favoritos.map((item) => (
                <Text key={item.supermercado} style={styles.bullet}>
                  • <Text style={styles.bold}>{item.supermercado}</Text> — visitado {item.visitas} veces.
                </Text>
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
    title: {
      color: colors.title,
      fontSize: 26,
      fontWeight: "900",
      textAlign: "center",
      marginBottom: 2,
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
    sectionTitle: {
      color: colors.title,
      fontSize: 17,
      fontWeight: "900",
      marginBottom: 8,
    },
    paragraph: {
      color: colors.text,
      fontSize: 14,
      lineHeight: 21,
    },
    mutedText: {
      color: colors.textMuted,
      fontSize: 13,
      lineHeight: 19,
      marginTop: 4,
    },
    bold: {
      color: colors.title,
      fontWeight: "900",
    },
    dayRow: {
      flexDirection: "row",
      alignItems: "center",
      gap: 8,
      marginBottom: 10,
    },
    dayLabel: {
      width: 76,
      color: colors.text,
      fontSize: 12,
      fontWeight: "800",
    },
    dayTrack: {
      flex: 1,
      height: 12,
      borderRadius: 999,
      backgroundColor: colors.card,
      borderWidth: 1,
      borderColor: colors.border,
      overflow: "hidden",
    },
    dayFill: {
      height: "100%",
      borderRadius: 999,
      backgroundColor: colors.cyan,
    },
    dayAmount: {
      width: 64,
      textAlign: "right",
      color: colors.title,
      fontSize: 12,
      fontWeight: "900",
    },
    bullet: {
      color: colors.text,
      fontSize: 14,
      lineHeight: 22,
      marginBottom: 4,
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
