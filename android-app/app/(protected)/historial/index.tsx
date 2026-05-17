import { useCallback, useEffect, useState } from "react";
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
import { router } from "expo-router";

import { historialService } from "@/src/services/historial";
import { HistorialLista } from "@/src/types/historial";

function formatDate(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleDateString("es-ES", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function HistorialScreen() {
  const [historial, setHistorial] = useState<HistorialLista[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadHistorial = useCallback(async () => {
    try {
      const data = await historialService.getMiHistorial();
      setHistorial(data);
    } catch (error) {
      console.error(error);
      Alert.alert("Error", "No se ha podido cargar el historial.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadHistorial();
  }, [loadHistorial]);

  const handleRefresh = () => {
    setRefreshing(true);
    loadHistorial();
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" />
        <Text style={styles.loadingText}>Cargando historial...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
        <Text style={styles.backButtonText}>← Volver</Text>
      </TouchableOpacity>

      <Text style={styles.title}>Historial</Text>
      <Text style={styles.subtitle}>
        Aquí aparecen las listas que ya has finalizado.
      </Text>

      <FlatList
        data={historial}
        keyExtractor={(item) => item.id_historial.toString()}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />
        }
        contentContainerStyle={
          historial.length === 0 ? styles.emptyListContent : undefined
        }
        ListEmptyComponent={
          <View style={styles.emptyBox}>
            <Text style={styles.emptyTitle}>Todavía no hay historial.</Text>
            <Text style={styles.emptyText}>
              Cuando finalices una lista de la compra, aparecerá aquí.
            </Text>
          </View>
        }
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.card}
            onPress={() =>
              router.push({
                pathname: "/historial/[id]",
                params: { id: item.id_historial.toString() },
              })
            }
          >
            <View style={styles.cardContent}>
              <View style={styles.cardHeader}>
                <Text style={styles.cardTitle}>{item.nombre_lista ?? "Lista finalizada"}</Text>
                <View style={styles.statusBadge}>
                  <Text style={styles.statusText}>{item.estado}</Text>
                </View>
              </View>

              <Text style={styles.cardDate}>{formatDate(item.fecha)}</Text>

              <View style={styles.cardFooter}>
                <Text style={styles.cardMeta}>
                  {item.num_productos} producto{item.num_productos === 1 ? "" : "s"}
                </Text>

                <Text style={styles.total}>{item.total_gastado} €</Text>
              </View>
            </View>

            <Text style={styles.arrow}>›</Text>
          </TouchableOpacity>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: "#F8F8F8",
  },
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#F8F8F8",
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
  },
  backButton: {
    marginBottom: 16,
  },
  backButtonText: {
    fontSize: 16,
    fontWeight: "600",
  },
  title: {
    fontSize: 28,
    fontWeight: "700",
    marginBottom: 6,
  },
  subtitle: {
    fontSize: 15,
    color: "#666",
    marginBottom: 20,
  },
  card: {
    backgroundColor: "#FFFFFF",
    borderRadius: 14,
    padding: 16,
    marginBottom: 12,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  cardContent: {
    flex: 1,
    marginRight: 12,
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 10,
    marginBottom: 6,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: "#111827",
  },
  statusBadge: {
    backgroundColor: "#DCFCE7",
    borderRadius: 999,
    paddingVertical: 4,
    paddingHorizontal: 10,
  },
  statusText: {
    color: "#166534",
    fontSize: 12,
    fontWeight: "700",
    textTransform: "capitalize",
  },
  cardDate: {
    color: "#666",
    fontSize: 14,
    marginBottom: 10,
  },
  cardFooter: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },
  cardMeta: {
    color: "#666",
    fontSize: 14,
  },
  total: {
    fontSize: 18,
    fontWeight: "800",
    color: "#111827",
  },
  arrow: {
    fontSize: 32,
    color: "#999",
  },
  emptyListContent: {
    flexGrow: 1,
  },
  emptyBox: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 20,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: "700",
    marginBottom: 8,
    color: "#111827",
  },
  emptyText: {
    color: "#777",
    fontSize: 16,
    textAlign: "center",
    lineHeight: 22,
  },
});
