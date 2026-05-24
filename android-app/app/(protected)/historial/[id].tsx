import { useCallback, useState } from "react";
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
import { router, useFocusEffect, useLocalSearchParams } from "expo-router";

import { Colors } from "@/src/constants/colors";
import { historialService } from "@/src/services/historial";
import {
  HistorialListaDetalle,
  HistorialProductoLista,
} from "@/src/types/historial";

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

export default function DetalleHistorialScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();

  const historialId = Number(id);

  const [historial, setHistorial] = useState<HistorialListaDetalle | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const [showRepeatModal, setShowRepeatModal] = useState(false);
  const [repeating, setRepeating] = useState(false);

  const loadDetalle = useCallback(async () => {
    if (!historialId || Number.isNaN(historialId)) {
      Alert.alert("Error", "Identificador de historial no válido.");
      router.replace("/historial");
      return;
    }

    try {
      const data = await historialService.getDetalle(historialId);
      setHistorial(data);
    } catch (error: any) {
      console.error(error);
      Alert.alert(
        "Error",
        error?.response?.data?.detail ||
          "No se ha podido cargar el detalle del historial."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [historialId]);

  useFocusEffect(
    useCallback(() => {
      loadDetalle();
    }, [loadDetalle])
  );

  const handleRefresh = () => {
    setRefreshing(true);
    loadDetalle();
  };

  const closeRepeatModal = () => {
    if (!repeating) {
      setShowRepeatModal(false);
    }
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

      router.replace({
        pathname: "/listas/[id]",
        params: { id: nuevaLista.id_lista.toString() },
      });
    } catch (error: any) {
      console.error(error);
      Alert.alert(
        "Error",
        error?.response?.data?.detail || "No se ha podido repetir la lista."
      );
    } finally {
      setRepeating(false);
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
          {item.categoria ?? "Sin categoría"} ·{" "}
          {item.unidad_medida ?? "Sin unidad"}
        </Text>

        <Text style={styles.productMeta}>
          Precio unidad: {formatEuro(item.precio_unitario)}
        </Text>

        <Text style={styles.productTotal}>
          Subtotal: {formatEuro(item.precio_estimado)}
        </Text>
      </View>

      <View style={styles.quantityBadge}>
        <Text style={styles.quantityText}>x{item.cantidad}</Text>
      </View>
    </View>
  );

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={Colors.primary} />
        <Text style={styles.loadingText}>Cargando historial...</Text>
      </View>
    );
  }

  if (!historial) {
    return (
      <View style={styles.center}>
        <Text style={styles.emptyTitle}>No se ha encontrado el historial.</Text>

        <TouchableOpacity
          style={styles.centerButton}
          onPress={() => router.replace("/historial")}
        >
          <Text style={styles.centerButtonText}>Volver al historial</Text>
        </TouchableOpacity>
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
        contentContainerStyle={styles.listContent}
        ListHeaderComponent={
          <View>
            <TouchableOpacity
              style={styles.backButton}
              onPress={() => router.replace("/historial")}
            >
              <Text style={styles.backButtonText}>← Volver al historial</Text>
            </TouchableOpacity>

            <View style={styles.summaryCard}>
              <View style={styles.summaryHeader}>
                <View style={styles.titleBox}>
                  <Text style={styles.title}>
                    {historial.nombre_lista ?? "Lista finalizada"}
                  </Text>
                  <Text style={styles.date}>{formatDate(historial.fecha)}</Text>
                </View>

                <View style={styles.statusBadge}>
                  <Text style={styles.statusText}>
                    {formatEstado(historial.estado)}
                  </Text>
                </View>
              </View>

              <View style={styles.summaryRow}>
                <View style={styles.summaryItem}>
                  <Text style={styles.summaryLabel}>Productos</Text>
                  <Text style={styles.summaryValue}>
                    {historial.num_productos}
                  </Text>
                </View>

                <View style={styles.summaryItem}>
                  <Text style={styles.summaryLabel}>Total gastado</Text>
                  <Text style={styles.summaryValue}>
                    {formatEuro(historial.total_gastado)}
                  </Text>
                </View>
              </View>

              <TouchableOpacity
                style={[styles.repeatButton, repeating && styles.disabledButton]}
                onPress={() => setShowRepeatModal(true)}
                disabled={repeating}
              >
                <Text style={styles.repeatButtonText}>Repetir lista</Text>
              </TouchableOpacity>
            </View>

            <Text style={styles.sectionTitle}>Productos guardados</Text>
          </View>
        }
        ListEmptyComponent={
          <View style={styles.emptyBox}>
            <Text style={styles.emptyTitle}>
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
              Se creará una nueva lista llamada{" "}
              <Text style={styles.modalStrong}>
                Copia de {historial.nombre_lista ?? "esta lista"}
              </Text>
              , con los productos y cantidades guardados en este historial.
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
                style={[
                  styles.modalConfirmButton,
                  repeating && styles.disabledButton,
                ]}
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
    backgroundColor: Colors.background,
  },
  listContent: {
    paddingBottom: 30,
  },
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: Colors.background,
    padding: 20,
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    color: Colors.textMuted,
  },
  centerButton: {
    backgroundColor: Colors.primary,
    paddingVertical: 12,
    paddingHorizontal: 18,
    borderRadius: 14,
    marginTop: 14,
  },
  centerButtonText: {
    color: Colors.white,
    fontWeight: "900",
  },
  backButton: {
    marginBottom: 16,
  },
  backButtonText: {
    fontSize: 16,
    fontWeight: "800",
    color: Colors.title,
  },
  summaryCard: {
    backgroundColor: Colors.surface,
    borderRadius: 22,
    padding: 18,
    borderWidth: 1,
    borderColor: Colors.border,
    marginBottom: 18,
  },
  summaryHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: 12,
    marginBottom: 18,
  },
  titleBox: {
    flex: 1,
  },
  title: {
    fontSize: 28,
    fontWeight: "900",
    marginBottom: 6,
    color: Colors.title,
  },
  date: {
    fontSize: 14,
    color: Colors.textMuted,
    lineHeight: 20,
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
  summaryRow: {
    flexDirection: "row",
    gap: 10,
    marginBottom: 16,
  },
  summaryItem: {
    flex: 1,
    backgroundColor: Colors.backgroundAlt,
    borderRadius: 16,
    padding: 14,
  },
  summaryLabel: {
    color: Colors.textMuted,
    fontSize: 12,
    fontWeight: "800",
    marginBottom: 6,
  },
  summaryValue: {
    color: Colors.title,
    fontSize: 18,
    fontWeight: "900",
  },
  repeatButton: {
    minHeight: 48,
    backgroundColor: Colors.black,
    borderRadius: 16,
    alignItems: "center",
    justifyContent: "center",
  },
  repeatButtonText: {
    color: Colors.white,
    fontWeight: "900",
    fontSize: 15,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "900",
    color: Colors.title,
    marginBottom: 12,
  },
  card: {
    backgroundColor: Colors.surface,
    borderRadius: 18,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: Colors.border,
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
    fontWeight: "900",
    marginBottom: 4,
    color: Colors.title,
  },
  productMeta: {
    color: Colors.textMuted,
    fontSize: 14,
    marginBottom: 2,
  },
  productTotal: {
    fontSize: 15,
    fontWeight: "900",
    marginTop: 6,
    color: Colors.text,
  },
  quantityBadge: {
    minWidth: 44,
    paddingVertical: 7,
    paddingHorizontal: 10,
    borderRadius: 999,
    backgroundColor: Colors.backgroundAlt,
    alignItems: "center",
  },
  quantityText: {
    fontSize: 15,
    fontWeight: "900",
    color: Colors.title,
  },
  emptyBox: {
    backgroundColor: Colors.surface,
    borderRadius: 18,
    padding: 24,
    borderWidth: 1,
    borderColor: Colors.border,
    alignItems: "center",
  },
  emptyTitle: {
    color: Colors.title,
    fontWeight: "900",
    fontSize: 17,
    marginBottom: 6,
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
    backgroundColor: Colors.surface,
    borderRadius: 22,
    padding: 22,
  },
  modalTitle: {
    fontSize: 22,
    fontWeight: "900",
    marginBottom: 10,
    color: Colors.title,
  },
  modalText: {
    fontSize: 16,
    color: Colors.textMuted,
    lineHeight: 22,
    marginBottom: 22,
  },
  modalStrong: {
    color: Colors.title,
    fontWeight: "900",
  },
  modalActions: {
    flexDirection: "row",
    justifyContent: "flex-end",
    gap: 12,
  },
  modalCancelButton: {
    paddingVertical: 11,
    paddingHorizontal: 16,
    borderRadius: 12,
    backgroundColor: Colors.card,
  },
  modalCancelText: {
    color: Colors.title,
    fontWeight: "900",
  },
  modalConfirmButton: {
    paddingVertical: 11,
    paddingHorizontal: 16,
    borderRadius: 12,
    backgroundColor: Colors.primary,
  },
  modalConfirmText: {
    color: Colors.white,
    fontWeight: "900",
  },
  disabledButton: {
    opacity: 0.6,
  },
});