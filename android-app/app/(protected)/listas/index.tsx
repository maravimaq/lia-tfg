import { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  RefreshControl,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { router } from "expo-router";

import { Colors } from "@/src/constants/colors";
import { listasService } from "@/src/services/listas";
import { ListaCompra, ListaCompraDetalle } from "@/src/types/lista";

type TabActiva = "propias" | "compartidas";

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
    month: "short",
    year: "numeric",
  });
}

export default function ListasScreen() {
  const [tabActiva, setTabActiva] = useState<TabActiva>("propias");
  const [listas, setListas] = useState<ListaCompra[]>([]);
  const [listasCompartidas, setListasCompartidas] = useState<ListaCompraDetalle[]>([]);
  const [nombreLista, setNombreLista] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [creating, setCreating] = useState(false);
  const [sharedWarning, setSharedWarning] = useState<string | null>(null);

  const loadListas = useCallback(async () => {
    try {
      setSharedWarning(null);
      const data = await listasService.getMisListas();
      setListas(data);

      try {
        const comparticiones = await listasService.getCompartidas();
        const detallesCompartidos = await Promise.all(
          comparticiones.map((comparticion) =>
            listasService.getDetalle(comparticion.lista_id)
          )
        );
        setListasCompartidas(detallesCompartidos);
      } catch (sharedError: any) {
        console.error(sharedError);
        setListasCompartidas([]);
        setSharedWarning(
          sharedError?.response?.data?.detail ||
            "No se han podido cargar las listas compartidas contigo."
        );
      }
    } catch (error: any) {
      console.error(error);
      Alert.alert(
        "Error",
        error?.response?.data?.detail || "No se han podido cargar las listas."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadListas();
  }, [loadListas]);

  const handleCreateLista = async () => {
    const nombre = nombreLista.trim();

    if (!nombre) {
      Alert.alert("Campo obligatorio", "Introduce un nombre para la lista.");
      return;
    }

    try {
      setCreating(true);

      const nuevaLista = await listasService.create({
        nombre_lista: nombre,
        compartida: false,
      });

      setListas((prev) => [nuevaLista, ...prev]);
      setNombreLista("");
      setTabActiva("propias");
    } catch (error: any) {
      console.error(error);
      Alert.alert(
        "Error",
        error?.response?.data?.detail || "No se ha podido crear la lista."
      );
    } finally {
      setCreating(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadListas();
  };

  const listasMostradas = tabActiva === "propias" ? listas : listasCompartidas;

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={Colors.primary} />
        <Text style={styles.loadingText}>Cargando listas...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.headerRow}>
        <View>
          <Text style={styles.title}>Listas</Text>
          <Text style={styles.subtitle}>Gestiona tus compras y productos.</Text>
        </View>

        <TouchableOpacity
          style={styles.catalogButton}
          onPress={() => router.push("/productos")}
        >
          <Text style={styles.catalogButtonText}>Catálogo</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.createBox}>
        <Text style={styles.createTitle}>Nueva lista</Text>
        <TextInput
          value={nombreLista}
          onChangeText={setNombreLista}
          placeholder="Ej: Compra semanal"
          placeholderTextColor={Colors.textMuted}
          style={styles.input}
          returnKeyType="done"
          onSubmitEditing={handleCreateLista}
        />

        <TouchableOpacity
          style={[styles.createButton, creating && styles.disabledButton]}
          onPress={handleCreateLista}
          disabled={creating}
        >
          <Text style={styles.createButtonText}>
            {creating ? "Creando..." : "Crear lista"}
          </Text>
        </TouchableOpacity>
      </View>

      <View style={styles.tabs}>
        <TouchableOpacity
          style={[styles.tab, tabActiva === "propias" && styles.tabActive]}
          onPress={() => setTabActiva("propias")}
        >
          <Text
            style={[
              styles.tabText,
              tabActiva === "propias" && styles.tabTextActive,
            ]}
          >
            Mis listas ({listas.length})
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.tab, tabActiva === "compartidas" && styles.tabActive]}
          onPress={() => setTabActiva("compartidas")}
        >
          <Text
            style={[
              styles.tabText,
              tabActiva === "compartidas" && styles.tabTextActive,
            ]}
          >
            Compartidas ({listasCompartidas.length})
          </Text>
        </TouchableOpacity>
      </View>

      {sharedWarning && tabActiva === "compartidas" ? (
        <View style={styles.warningBox}>
          <Text style={styles.warningText}>{sharedWarning}</Text>
        </View>
      ) : null}

      <FlatList
        data={listasMostradas}
        keyExtractor={(item) => item.id_lista.toString()}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />
        }
        contentContainerStyle={
          listasMostradas.length === 0 ? styles.emptyListContent : undefined
        }
        ListEmptyComponent={
          <View style={styles.emptyBox}>
            <Text style={styles.emptyTitle}>
              {tabActiva === "propias"
                ? "Todavía no tienes listas."
                : "No tienes listas compartidas contigo."}
            </Text>
            <Text style={styles.emptyText}>
              {tabActiva === "propias"
                ? "Crea una lista para empezar a añadir productos."
                : "Cuando alguien comparta una lista contigo aparecerá aquí."}
            </Text>
          </View>
        }
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.card}
            activeOpacity={0.82}
            onPress={() =>
              router.push({
                pathname: "/listas/[id]",
                params: { id: item.id_lista.toString() },
              })
            }
          >
            <View style={styles.cardContent}>
              <View style={styles.cardTopRow}>
                <Text style={styles.cardTitle}>{item.nombre_lista}</Text>
                <Text style={styles.arrow}>›</Text>
              </View>

              <Text style={styles.cardSubtitle}>
                Total estimado: {formatEuro(item.total_estimado)}
              </Text>

              <View style={styles.badgeRow}>
                <View style={styles.badge}>
                  <Text style={styles.badgeText}>
                    {tabActiva === "compartidas" ? "Compartida contigo" : "Propia"}
                  </Text>
                </View>

                <Text style={styles.dateText}>
                  Modificada: {formatDate(item.fecha_modificacion)}
                </Text>
              </View>
            </View>
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
    backgroundColor: Colors.background,
  },
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: Colors.background,
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    color: Colors.textMuted,
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: 12,
    marginBottom: 18,
  },
  title: {
    fontSize: 30,
    fontWeight: "800",
    color: Colors.title,
  },
  subtitle: {
    marginTop: 4,
    color: Colors.textMuted,
    fontSize: 14,
  },
  catalogButton: {
    backgroundColor: Colors.black,
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderRadius: 14,
  },
  catalogButtonText: {
    color: Colors.white,
    fontWeight: "800",
  },
  createBox: {
    backgroundColor: Colors.surface,
    borderRadius: 18,
    padding: 14,
    marginBottom: 16,
    gap: 10,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  createTitle: {
    fontSize: 16,
    fontWeight: "800",
    color: Colors.title,
  },
  input: {
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
    backgroundColor: Colors.white,
    color: Colors.text,
  },
  createButton: {
    backgroundColor: Colors.primary,
    paddingVertical: 13,
    borderRadius: 14,
    alignItems: "center",
  },
  disabledButton: {
    opacity: 0.6,
  },
  createButtonText: {
    color: Colors.white,
    fontSize: 16,
    fontWeight: "800",
  },
  tabs: {
    flexDirection: "row",
    gap: 10,
    marginBottom: 14,
  },
  tab: {
    flex: 1,
    minHeight: 42,
    borderRadius: 22,
    backgroundColor: Colors.card,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: Colors.border,
  },
  tabActive: {
    backgroundColor: Colors.black,
    borderColor: Colors.black,
  },
  tabText: {
    fontSize: 13,
    fontWeight: "800",
    color: Colors.text,
  },
  tabTextActive: {
    color: Colors.white,
  },
  warningBox: {
    backgroundColor: "#FFF7ED",
    borderWidth: 1,
    borderColor: "#FED7AA",
    borderRadius: 14,
    padding: 12,
    marginBottom: 12,
  },
  warningText: {
    color: "#9A3412",
    lineHeight: 20,
  },
  card: {
    backgroundColor: Colors.surface,
    borderRadius: 18,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  cardContent: {
    gap: 8,
  },
  cardTopRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },
  cardTitle: {
    flex: 1,
    fontSize: 18,
    fontWeight: "800",
    color: Colors.title,
  },
  cardSubtitle: {
    fontSize: 15,
    color: Colors.textMuted,
    fontWeight: "600",
  },
  arrow: {
    fontSize: 30,
    color: Colors.textMuted,
  },
  badgeRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 10,
    marginTop: 4,
  },
  badge: {
    backgroundColor: Colors.backgroundAlt,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 999,
  },
  badgeText: {
    color: Colors.primary,
    fontSize: 12,
    fontWeight: "800",
  },
  dateText: {
    flex: 1,
    textAlign: "right",
    color: Colors.textMuted,
    fontSize: 12,
  },
  emptyListContent: {
    flexGrow: 1,
  },
  emptyBox: {
    flex: 1,
    paddingTop: 60,
    alignItems: "center",
  },
  emptyTitle: {
    color: Colors.title,
    fontSize: 17,
    fontWeight: "800",
    marginBottom: 6,
  },
  emptyText: {
    color: Colors.textMuted,
    fontSize: 14,
    textAlign: "center",
    lineHeight: 20,
  },
});
