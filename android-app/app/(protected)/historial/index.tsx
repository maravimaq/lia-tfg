import { useCallback, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  RefreshControl,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { router, useFocusEffect } from "expo-router";

import { AppColors } from "@/src/constants/colors";
import { useAppTheme } from "@/src/hooks/useAppTheme";
import { historialService } from "@/src/services/historial";
import { HistorialLista } from "@/src/types/historial";

function formatEuro(value?: string | number | null) {
  const numberValue = Number(value ?? 0);

  if (Number.isNaN(numberValue)) {
    return "0,00 €";
  }

  return `${numberValue.toFixed(2).replace(".", ",")} €`;
}

function formatDate(value?: string | null) {
  if (!value) return "Sin fecha";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Sin fecha";
  }

  return date.toLocaleDateString("es-ES", {
    day: "2-digit",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatEstado(value?: string | null) {
  if (!value) return "Finalizada";

  return value.charAt(0).toUpperCase() + value.slice(1);
}

export default function HistorialScreen() {
  const [historial, setHistorial] = useState<HistorialLista[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const { colors } = useAppTheme();
  const styles = useMemo(() => createStyles(colors), [colors]);

  const loadHistorial = useCallback(async () => {
    try {
      const data = await historialService.getMiHistorial();
      setHistorial(data);
    } catch (error: any) {
      console.error(error);
      Alert.alert(
        "Error",
        error?.response?.data?.detail || "No se ha podido cargar el historial."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      loadHistorial();
    }, [loadHistorial])
  );

  const handleRefresh = () => {
    setRefreshing(true);
    loadHistorial();
  };

  const handleOpenHistorial = (item: HistorialLista) => {
    router.push({
      pathname: "/historial/[id]",
      params: { id: item.id_historial.toString() },
    });
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Cargando historial...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={historial}
        keyExtractor={(item) => item.id_historial.toString()}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            tintColor={colors.primary}
            colors={[colors.primary]}
            progressBackgroundColor={colors.surface}
          />
        }
        contentContainerStyle={[
          styles.listContent,
          historial.length === 0 && styles.emptyListContent,
        ]}
        ListHeaderComponent={
          <View>
            <TouchableOpacity
              style={styles.backButton}
              onPress={() => router.replace("/listas")}
            >
              <Text style={styles.backButtonText}>← Volver a listas</Text>
            </TouchableOpacity>

            <View style={styles.headerCard}>
              <Text style={styles.title}>Historial de listas</Text>
              <Text style={styles.subtitle}>
                Consulta las listas que ya has finalizado y repítelas cuando
                quieras volver a comprar lo mismo.
              </Text>
            </View>
          </View>
        }
        ListEmptyComponent={
          <View style={styles.emptyBox}>
            <Text style={styles.emptyTitle}>Todavía no hay historial.</Text>
            <Text style={styles.emptyText}>
              Cuando finalices una lista de la compra, aparecerá aquí.
            </Text>

            <TouchableOpacity
              style={styles.emptyButton}
              onPress={() => router.replace("/listas")}
            >
              <Text style={styles.emptyButtonText}>Ir a mis listas</Text>
            </TouchableOpacity>
          </View>
        }
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.card}
            onPress={() => handleOpenHistorial(item)}
          >
            <View style={styles.cardContent}>
              <View style={styles.cardHeader}>
                <View style={styles.cardTitleBox}>
                  <Text style={styles.cardTitle}>
                    {item.nombre_lista ?? "Lista finalizada"}
                  </Text>

                  <Text style={styles.cardDate}>{formatDate(item.fecha)}</Text>
                </View>

                <View style={styles.statusBadge}>
                  <Text style={styles.statusText}>
                    {formatEstado(item.estado)}
                  </Text>
                </View>
              </View>

              <View style={styles.cardFooter}>
                <View style={styles.metaPill}>
                  <Text style={styles.metaPillText}>
                    {item.num_productos} producto
                    {item.num_productos === 1 ? "" : "s"}
                  </Text>
                </View>

                <Text style={styles.total}>{formatEuro(item.total_gastado)}</Text>
              </View>
            </View>

            <Text style={styles.arrow}>›</Text>
          </TouchableOpacity>
        )}
      />
    </View>
  );
}

const createStyles = (colors: AppColors) => StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: colors.background,
  },
  listContent: {
    paddingBottom: 30,
  },
  emptyListContent: {
    flexGrow: 1,
  },
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: colors.background,
    padding: 20,
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    color: colors.textMuted,
  },
  backButton: {
    marginBottom: 16,
  },
  backButtonText: {
    fontSize: 16,
    fontWeight: "800",
    color: colors.title,
  },
  headerCard: {
    backgroundColor: colors.surface,
    borderRadius: 22,
    padding: 18,
    borderWidth: 1,
    borderColor: colors.border,
    marginBottom: 18,
  },
  title: {
    fontSize: 30,
    fontWeight: "900",
    color: colors.title,
    marginBottom: 6,
  },
  subtitle: {
    fontSize: 15,
    color: colors.textMuted,
    lineHeight: 21,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: 18,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: colors.border,
    flexDirection: "row",
    alignItems: "center",
  },
  cardContent: {
    flex: 1,
    marginRight: 12,
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: 10,
    marginBottom: 14,
  },
  cardTitleBox: {
    flex: 1,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: "900",
    color: colors.title,
    marginBottom: 4,
  },
  cardDate: {
    color: colors.textMuted,
    fontSize: 13,
    lineHeight: 18,
  },
  statusBadge: {
    backgroundColor: "#ECFDF5",
    borderRadius: 999,
    paddingVertical: 5,
    paddingHorizontal: 10,
  },
  statusText: {
    color: "#166534",
    fontSize: 12,
    fontWeight: "900",
  },
  cardFooter: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },
  metaPill: {
    backgroundColor: colors.backgroundAlt,
    borderRadius: 999,
    paddingVertical: 6,
    paddingHorizontal: 10,
  },
  metaPillText: {
    color: colors.title,
    fontWeight: "800",
    fontSize: 12,
  },
  total: {
    fontSize: 18,
    fontWeight: "900",
    color: colors.title,
  },
  arrow: {
    fontSize: 32,
    color: colors.textMuted,
  },
  emptyBox: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: 18,
    padding: 24,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: "center",
    justifyContent: "center",
  },
  emptyTitle: {
    color: colors.title,
    fontWeight: "900",
    fontSize: 18,
    marginBottom: 8,
    textAlign: "center",
  },
  emptyText: {
    color: colors.textMuted,
    fontSize: 15,
    textAlign: "center",
    lineHeight: 21,
    marginBottom: 18,
  },
  emptyButton: {
    backgroundColor: colors.primary,
    borderRadius: 14,
    paddingVertical: 12,
    paddingHorizontal: 18,
  },
  emptyButtonText: {
    color: colors.white,
    fontWeight: "900",
  },
});