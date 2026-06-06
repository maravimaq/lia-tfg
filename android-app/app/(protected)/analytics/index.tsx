import React, { useMemo } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";

import { AppColors } from "@/src/constants/colors";
import { useAppTheme } from "@/src/hooks/useAppTheme";

type AnalyticsCardProps = {
  title: string;
  description: string;
  icon: string;
  onPress: () => void;
  styles: ReturnType<typeof createStyles>;
};

function AnalyticsCard({ title, description, icon, onPress, styles }: AnalyticsCardProps) {
  return (
    <Pressable style={styles.card} onPress={onPress}>
      <View style={styles.iconBox}>
        <Text style={styles.icon}>{icon}</Text>
      </View>

      <View style={styles.cardContent}>
        <Text style={styles.cardTitle}>{title}</Text>
        <Text style={styles.cardDescription}>{description}</Text>
      </View>

      <Text style={styles.arrow}>›</Text>
    </Pressable>
  );
}

export default function AnalyticsHomeScreen() {
  const { colors, isDarkMode } = useAppTheme();
  const styles = useMemo(() => createStyles(colors, isDarkMode), [colors, isDarkMode]);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.headerCard}>
        <Text style={styles.title}>Analíticas</Text>
        <Text style={styles.subtitle}>
          Consulta tus gastos, categorías más compradas y hábitos de compra a partir del historial de listas finalizadas.
        </Text>
      </View>

      <AnalyticsCard
        icon="€"
        title="Detalles del gasto mensual"
        description="Resumen mensual, gasto por semana y listas finalizadas del mes."
        onPress={() => router.push("/(protected)/analytics/monthly-expenses" as never)}
        styles={styles}
      />

      <AnalyticsCard
        icon="%"
        title="Categorías más compradas"
        description="Distribución del gasto por categoría y productos más frecuentes."
        onPress={() => router.push("/(protected)/analytics/categories" as never)}
        styles={styles}
      />

      <AnalyticsCard
        icon="↻"
        title="Hábitos de compra"
        description="Frecuencia, días habituales, supermercados más usados y listas repetidas."
        onPress={() => router.push("/(protected)/analytics/habits" as never)}
        styles={styles}
      />
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
    headerCard: {
      backgroundColor: colors.surface,
      borderWidth: 1,
      borderColor: colors.border,
      borderRadius: 18,
      padding: 18,
      shadowColor: "#000",
      shadowOpacity: isDarkMode ? 0.28 : 0.06,
      shadowRadius: 8,
      shadowOffset: { width: 0, height: 3 },
      elevation: 2,
    },
    title: {
      color: colors.title,
      fontSize: 28,
      fontWeight: "900",
      marginBottom: 6,
    },
    subtitle: {
      color: colors.textMuted,
      fontSize: 14,
      lineHeight: 20,
    },
    card: {
      backgroundColor: colors.surface,
      borderWidth: 1,
      borderColor: colors.border,
      borderRadius: 18,
      padding: 16,
      flexDirection: "row",
      alignItems: "center",
      gap: 14,
      shadowColor: "#000",
      shadowOpacity: isDarkMode ? 0.24 : 0.05,
      shadowRadius: 8,
      shadowOffset: { width: 0, height: 3 },
      elevation: 2,
    },
    iconBox: {
      width: 48,
      height: 48,
      borderRadius: 16,
      backgroundColor: colors.card,
      alignItems: "center",
      justifyContent: "center",
      borderWidth: 1,
      borderColor: colors.border,
    },
    icon: {
      color: colors.primary,
      fontSize: 24,
      fontWeight: "900",
    },
    cardContent: {
      flex: 1,
      gap: 4,
    },
    cardTitle: {
      color: colors.title,
      fontSize: 17,
      fontWeight: "900",
    },
    cardDescription: {
      color: colors.textMuted,
      fontSize: 13,
      lineHeight: 18,
    },
    arrow: {
      color: colors.textMuted,
      fontSize: 30,
      fontWeight: "700",
    },
  });
}
