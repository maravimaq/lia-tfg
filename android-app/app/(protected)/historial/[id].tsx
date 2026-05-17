import { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Modal,
  RefreshControl,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { router, useLocalSearchParams } from "expo-router";

import { historialService } from "@/src/services/historial";
import {
  HistorialListaDetalle,
  HistorialProductoLista,
} from "@/src/types/historial";

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

export default function DetalleHistorialScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();

  const historialId = Number(id);

  const [historial, setHistorial] = useState<HistorialListaDetalle | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showRepeatModal, setShowRepeatModal] = useState(false);
  const [repeating, setRepeating] = useState(false);

  const loadDetalle = useCallback(async () => {
    if (!historialId || Number.isNaN(historialId)) {
      Alert.alert("Error", "Identificador de historial no válido.");
      router.back();
      return;
    }

    try {
      const data = await historialService.getDetalle(historialId);
      setHistorial(data);
    } catch (error) {
      console.error(error);
      Alert.alert("Error", "No se ha podido cargar el detalle del historial.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [historialId]);

  useEffect(() => {
    loadDetalle();
  }, [loadDetalle]);

  const handleRefresh = () => {
    setRefreshing(true);
    loadDetalle();
  };

  const handleRepeatList = async () => {
    if (!historial) {
      return;
    }

    try {
      setRepeating(true);

      const nuevaLista = await historialService.repetirLista(
        historial.id_historial
      );

      setShowRepeatModal(false);

      Alert.alert(
        "Lista repetida",
        "Se ha creado una nueva lista con los productos de este historial.",
        [
          {
            text: "Quedarme aquí",
            style: "cancel",
          },
          {
            text: "Ver nueva lista",
            onPress: () =>
              router.push({
                pathname: "/listas/[id]",
                params: { id: nuevaLista.id_lista.toString() },
              }),
          },
        ]
      );
    } catch (error) {
      console.error(error);
      Alert.alert("Error", "No se ha podido repetir la lista.");
    } finally {
      setRepeating(false);
    }
  };

  const closeRepeatModal = () => {
    if (!repeating) {
      setShowRepeatModal(false);
    }
  };

  const renderProduct = ({ item }: { item: HistorialProductoLista }) => (
    <View style={styles.card}>
      <View style={styles.productInfo}>
        <Text style={styles.productName}>{item.nombre_producto}</Text>

        <Text style={styles.productMeta}>
          {item.marca ?? "Sin marca"} · {item.supermercado}
        </Text>

        <Text style={styles.productMeta}>
          {item.categoria ?? "Sin categoría"} · {item.unidad_medida ?? "Sin unidad"}
        </Text>

        <Text style={styles.productMeta}>Precio unidad: {item.precio_unitario} €</Text>

        <Text style={styles.productTotal}>Subtotal: {item.precio_estimado} €</Text>
      </View>

      <View style={styles.quantityBadge}>
        <Text style={styles.quantityText}>x{item.cantidad}</Text>
      </View>
    </View>
  );

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" />
        <Text style={styles.loadingText}>Cargando historial...</Text>
      </View>
    );
  }

  if (!historial) {
    return (
      <View style={styles.center}>
        <Text>No se ha encontrado el historial.</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={historial.productos}
        keyExtractor={(item) => item.id_historial_producto.toString()}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />
        }
        ListHeaderComponent={
          <View>
            <TouchableOpacity
              style={styles.backButton}
              onPress={() => router.back()}
            >
              <Text style={styles.backButtonText}>← Volver</Text>
            </TouchableOpacity>

            <View style={styles.summaryCard}>
              <View style={styles.summaryHeader}>
                <View>
                  <Text style={styles.title}>{historial.nombre_lista ?? "Lista finalizada"}</Text>
                  <Text style={styles.date}>{formatDate(historial.fecha)}</Text>
                </View>

                <View style={styles.statusBadge}>
                  <Text style={styles.statusText}>{historial.estado}</Text>
                </View>
              </View>

              <View style={styles.summaryRow}>
                <View style={styles.summaryItem}>
                  <Text style={styles.summaryLabel}>Productos</Text>
                  <Text style={styles.summaryValue}>{historial.num_productos}</Text>
                </View>

                <View style={styles.summaryItem}>
                  <Text style={styles.summaryLabel}>Total gastado</Text>
                  <Text style={styles.summaryValue}>
                    {historial.total_gastado} €
                  </Text>
                </View>
              </View>

              <TouchableOpacity
                style={styles.repeatButton}
                onPress={() => setShowRepeatModal(true)}
              >
                <Text style={styles.repeatButtonText}>Repetir lista</Text>
              </TouchableOpacity>
            </View>

            <Text style={styles.sectionTitle}>Productos guardados</Text>
          </View>
        }
        ListEmptyComponent={
          <View style={styles.emptyBox}>
            <Text style={styles.emptyText}>
              Este historial no tiene productos guardados.
            </Text>
          </View>
        }
        renderItem={renderProduct}
      />

      <Modal
        visible={showRepeatModal}
        transparent
        animationType="fade"
        onRequestClose={closeRepeatModal}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>Repetir lista</Text>

            <Text style={styles.modalText}>
              Se creará una nueva lista con los productos y cantidades guardados
              en este historial.
            </Text>

            <View style={styles.modalActions}>
              <TouchableOpacity
                style={styles.modalCancelButton}
                onPress={closeRepeatModal}
                disabled={repeating}
              >
                <Text style={styles.modalCancelText}>Cancelar</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.modalConfirmButton, repeating && styles.disabledButton]}
                onPress={handleRepeatList}
                disabled={repeating}
              >
                <Text style={styles.modalConfirmText}>
                  {repeating ? "Creando..." : "Repetir"}
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
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
  summaryCard: {
    backgroundColor: "#FFFFFF",
    borderRadius: 16,
    padding: 16,
    marginBottom: 20,
  },
  summaryHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: 12,
    marginBottom: 16,
  },
  title: {
    fontSize: 28,
    fontWeight: "700",
    marginBottom: 6,
    color: "#111827",
  },
  date: {
    fontSize: 14,
    color: "#666",
  },
  statusBadge: {
    backgroundColor: "#DCFCE7",
    borderRadius: 999,
    paddingVertical: 5,
    paddingHorizontal: 10,
  },
  statusText: {
    color: "#166534",
    fontSize: 12,
    fontWeight: "700",
    textTransform: "capitalize",
  },
  summaryRow: {
    flexDirection: "row",
    gap: 12,
    marginBottom: 16,
  },
  summaryItem: {
    flex: 1,
    backgroundColor: "#F3F4F6",
    borderRadius: 12,
    padding: 12,
  },
  summaryLabel: {
    color: "#666",
    fontSize: 13,
    marginBottom: 4,
  },
  summaryValue: {
    color: "#111827",
    fontSize: 18,
    fontWeight: "800",
  },
  repeatButton: {
    backgroundColor: "#111827",
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: "center",
  },
  repeatButtonText: {
    color: "#FFFFFF",
    fontWeight: "700",
    fontSize: 16,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: "800",
    color: "#111827",
    marginBottom: 12,
  },
  card: {
    backgroundColor: "#FFFFFF",
    borderRadius: 14,
    padding: 16,
    marginBottom: 12,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: 12,
  },
  productInfo: {
    flex: 1,
  },
  productName: {
    fontSize: 18,
    fontWeight: "700",
    marginBottom: 4,
    color: "#111827",
  },
  productMeta: {
    color: "#666",
    fontSize: 14,
    marginBottom: 2,
  },
  productTotal: {
    fontSize: 15,
    fontWeight: "700",
    marginTop: 6,
    color: "#111827",
  },
  quantityBadge: {
    minWidth: 44,
    paddingVertical: 7,
    paddingHorizontal: 10,
    borderRadius: 999,
    backgroundColor: "#E5E7EB",
    alignItems: "center",
  },
  quantityText: {
    fontSize: 15,
    fontWeight: "800",
    color: "#111827",
  },
  emptyBox: {
    paddingTop: 24,
    alignItems: "center",
  },
  emptyText: {
    color: "#777",
    fontSize: 16,
    textAlign: "center",
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0, 0, 0, 0.45)",
    justifyContent: "center",
    alignItems: "center",
    padding: 24,
  },
  modalCard: {
    width: "100%",
    maxWidth: 420,
    backgroundColor: "#FFFFFF",
    borderRadius: 18,
    padding: 22,
  },
  modalTitle: {
    fontSize: 22,
    fontWeight: "800",
    marginBottom: 10,
    color: "#111827",
  },
  modalText: {
    fontSize: 16,
    color: "#4B5563",
    lineHeight: 22,
    marginBottom: 22,
  },
  modalActions: {
    flexDirection: "row",
    justifyContent: "flex-end",
    gap: 12,
  },
  modalCancelButton: {
    paddingVertical: 11,
    paddingHorizontal: 16,
    borderRadius: 10,
    backgroundColor: "#E5E7EB",
  },
  modalCancelText: {
    color: "#111827",
    fontWeight: "700",
  },
  modalConfirmButton: {
    paddingVertical: 11,
    paddingHorizontal: 16,
    borderRadius: 10,
    backgroundColor: "#111827",
  },
  modalConfirmText: {
    color: "#FFFFFF",
    fontWeight: "800",
  },
  disabledButton: {
    opacity: 0.6,
  },
});
