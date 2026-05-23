import { useCallback, useEffect, useMemo, useState } from "react";
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
import { ListaCompra } from "@/src/types/lista";

type Tab = "propias" | "compartidas";

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
  });
}

function getSharedBadgeText(lista: ListaCompra, isCompartida: boolean) {
  if (!isCompartida) {
    return lista.compartida ? "Compartida" : "Privada";
  }

  if (lista.tipo_compartido === "visualizacion") {
    return "Solo visualización";
  }

  if (lista.tipo_compartido === "edicion") {
    return "Con privilegios";
  }

  return "Compartida contigo";
}

export default function ListasScreen() {
  const [activeTab, setActiveTab] = useState<Tab>("propias");

  const [misListas, setMisListas] = useState<ListaCompra[]>([]);
  const [listasCompartidas, setListasCompartidas] = useState<ListaCompra[]>([]);

  const [nombreLista, setNombreLista] = useState("");
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const listasMostradas = useMemo(() => {
    return activeTab === "propias" ? misListas : listasCompartidas;
  }, [activeTab, misListas, listasCompartidas]);

  const loadListas = useCallback(async () => {
    try {
      const [propias, compartidas] = await Promise.all([
        listasService.getMisListas(),
        listasService.getCompartidas(),
      ]);

      setMisListas(propias);
      setListasCompartidas(compartidas);
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

  const handleRefresh = () => {
    setRefreshing(true);
    loadListas();
  };

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

      setNombreLista("");
      setMisListas((prev) => [nuevaLista, ...prev]);
      setActiveTab("propias");

      router.push({
        pathname: "/listas/[id]",
        params: { id: nuevaLista.id_lista.toString() },
      });
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

  const handleOpenLista = (lista: ListaCompra) => {
    router.push({
      pathname: "/listas/[id]",
      params: { id: lista.id_lista.toString() },
    });
  };

  const renderLista = ({ item }: { item: ListaCompra }) => {
    const isCompartida = activeTab === "compartidas";

    return (
      <TouchableOpacity style={styles.card} onPress={() => handleOpenLista(item)}>
        <View style={styles.cardContent}>
          <Text style={styles.cardTitle}>{item.nombre_lista}</Text>

          <Text style={styles.cardText}>
            Total estimado: {formatEuro(item.total_estimado)}
          </Text>

          <Text style={styles.cardText}>
            Última modificación: {formatDate(item.fecha_modificacion)}
          </Text>

          <View
            style={[
              styles.badge,
              isCompartida &&
                item.tipo_compartido === "visualizacion" &&
                styles.readOnlyBadge,
              isCompartida &&
                item.tipo_compartido === "edicion" &&
                styles.editBadge,
            ]}
          >
            <Text
              style={[
                styles.badgeText,
                isCompartida &&
                  item.tipo_compartido === "visualizacion" &&
                  styles.readOnlyBadgeText,
                isCompartida &&
                  item.tipo_compartido === "edicion" &&
                  styles.editBadgeText,
              ]}
            >
              {getSharedBadgeText(item, isCompartida)}
            </Text>
          </View>
        </View>

        <Text style={styles.arrow}>›</Text>
      </TouchableOpacity>
    );
  };

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
      <FlatList
        data={listasMostradas}
        keyExtractor={(item) => item.id_lista.toString()}
        renderItem={renderLista}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />
        }
        ListHeaderComponent={
          <View>
            <View style={styles.header}>
              <View>
                <Text style={styles.title}>Listas</Text>
                <Text style={styles.subtitle}>
                  Gestiona tus listas de la compra y las que han compartido contigo.
                </Text>
              </View>

              <TouchableOpacity
                style={styles.catalogButton}
                onPress={() => router.push("/productos")}
              >
                <Text style={styles.catalogButtonText}>Catálogo</Text>
              </TouchableOpacity>
            </View>

            <View style={styles.tabs}>
              <TouchableOpacity
                style={[styles.tabButton, activeTab === "propias" && styles.activeTabButton]}
                onPress={() => setActiveTab("propias")}
              >
                <Text
                  style={[
                    styles.tabButtonText,
                    activeTab === "propias" && styles.activeTabButtonText,
                  ]}
                >
                  Mis listas
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[
                  styles.tabButton,
                  activeTab === "compartidas" && styles.activeTabButton,
                ]}
                onPress={() => setActiveTab("compartidas")}
              >
                <Text
                  style={[
                    styles.tabButtonText,
                    activeTab === "compartidas" && styles.activeTabButtonText,
                  ]}
                >
                  Compartidas conmigo
                </Text>
              </TouchableOpacity>
            </View>

            {activeTab === "propias" ? (
              <View style={styles.createCard}>
                <TextInput
                  value={nombreLista}
                  onChangeText={setNombreLista}
                  placeholder="Nombre de la lista"
                  placeholderTextColor={Colors.textMuted}
                  style={styles.input}
                  editable={!creating}
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
            ) : null}

            <Text style={styles.sectionTitle}>
              {activeTab === "propias" ? "Mis listas" : "Listas compartidas conmigo"}
            </Text>
          </View>
        }
        ListEmptyComponent={
          <View style={styles.emptyBox}>
            <Text style={styles.emptyTitle}>
              {activeTab === "propias"
                ? "Todavía no tienes listas."
                : "No tienes listas compartidas."}
            </Text>

            <Text style={styles.emptyText}>
              {activeTab === "propias"
                ? "Crea una lista para empezar a añadir productos."
                : "Cuando otro usuario comparta una lista contigo, aparecerá aquí."}
            </Text>
          </View>
        }
        contentContainerStyle={styles.listContent}
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
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: 12,
    marginBottom: 18,
  },
  title: {
    fontSize: 30,
    fontWeight: "900",
    color: Colors.title,
  },
  subtitle: {
    marginTop: 4,
    fontSize: 14,
    color: Colors.textMuted,
    lineHeight: 20,
  },
  catalogButton: {
    backgroundColor: Colors.black,
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderRadius: 14,
  },
  catalogButtonText: {
    color: Colors.white,
    fontWeight: "900",
  },
  tabs: {
    flexDirection: "row",
    backgroundColor: Colors.card,
    padding: 4,
    borderRadius: 16,
    marginBottom: 16,
    gap: 4,
  },
  tabButton: {
    flex: 1,
    minHeight: 42,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 12,
    paddingHorizontal: 10,
  },
  activeTabButton: {
    backgroundColor: Colors.primary,
  },
  tabButtonText: {
    color: Colors.textMuted,
    fontWeight: "900",
    fontSize: 13,
    textAlign: "center",
  },
  activeTabButtonText: {
    color: Colors.white,
  },
  createCard: {
    backgroundColor: Colors.surface,
    borderRadius: 20,
    padding: 14,
    borderWidth: 1,
    borderColor: Colors.border,
    marginBottom: 18,
    gap: 12,
  },
  input: {
    minHeight: 46,
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 14,
    paddingHorizontal: 14,
    fontSize: 16,
    backgroundColor: Colors.white,
    color: Colors.text,
  },
  createButton: {
    minHeight: 46,
    backgroundColor: Colors.primary,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
  },
  createButtonText: {
    color: Colors.white,
    fontSize: 15,
    fontWeight: "900",
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
    alignItems: "center",
  },
  cardContent: {
    flex: 1,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: "900",
    color: Colors.title,
    marginBottom: 6,
  },
  cardText: {
    fontSize: 14,
    color: Colors.textMuted,
    marginBottom: 3,
  },
  badge: {
    alignSelf: "flex-start",
    marginTop: 8,
    backgroundColor: Colors.backgroundAlt,
    borderRadius: 999,
    paddingVertical: 5,
    paddingHorizontal: 10,
  },
  badgeText: {
    fontSize: 12,
    fontWeight: "800",
    color: Colors.title,
  },
  editBadge: {
    backgroundColor: "#ECFDF5",
  },
  editBadgeText: {
    color: "#166534",
  },
  readOnlyBadge: {
    backgroundColor: "#FEF3C7",
  },
  readOnlyBadgeText: {
    color: "#92400E",
  },
  arrow: {
    fontSize: 32,
    color: Colors.textMuted,
    marginLeft: 12,
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
  emptyText: {
    color: Colors.textMuted,
    fontSize: 14,
    textAlign: "center",
    lineHeight: 20,
  },
  disabledButton: {
    opacity: 0.6,
  },
});