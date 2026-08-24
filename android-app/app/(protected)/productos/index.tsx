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
import { router, useLocalSearchParams } from "expo-router";

import { ProductImage } from "@/src/components/ProductImage";
import { Colors } from "@/src/constants/colors";
import { listasService } from "@/src/services/listas";
import { productosService } from "@/src/services/productos";
import { ListaCompraDetalle, ProductoLista } from "@/src/types/lista";
import { Producto } from "@/src/types/producto";

type OrdenPrecio = "asc" | "desc";

function formatEuro(value?: string | number | null) {
  const numberValue = Number(value ?? 0);

  if (Number.isNaN(numberValue)) {
    return "0,00 €";
  }

  return `${numberValue.toFixed(2).replace(".", ",")} €`;
}

export default function ProductosScreen() {
  const { listaId } = useLocalSearchParams<{ listaId?: string }>();

  const listaIdNumber = listaId ? Number(listaId) : null;
  const isAddingToList = !!listaIdNumber && !Number.isNaN(listaIdNumber);

  const [productos, setProductos] = useState<Producto[]>([]);
  const [productosEnLista, setProductosEnLista] = useState<ProductoLista[]>([]);
  const [listaDestino, setListaDestino] = useState<ListaCompraDetalle | null>(
    null
  );

  const [nombre, setNombre] = useState("");
  const [marca, setMarca] = useState("");
  const [supermercado, setSupermercado] = useState("");
  const [categoria, setCategoria] = useState("");
  const [ordenPrecio, setOrdenPrecio] = useState<OrdenPrecio>("asc");

  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [addingProductId, setAddingProductId] = useState<number | null>(null);
  const [lastAddedProductId, setLastAddedProductId] = useState<number | null>(
    null
  );

  const hasFilters = useMemo(
    () =>
      !!(
        nombre.trim() ||
        marca.trim() ||
        supermercado.trim() ||
        categoria.trim()
      ),
    [nombre, marca, supermercado, categoria]
  );

  const canAddToSelectedList = useMemo(() => {
    if (!isAddingToList) return false;
    if (!listaDestino) return false;

    return listaDestino.tipo_compartido !== "visualizacion";
  }, [isAddingToList, listaDestino]);

  const loadProductos = useCallback(
    async (showFullLoading = false) => {
      try {
        if (showFullLoading) {
          setLoading(true);
        }

        const shouldUseSearch = hasFilters || ordenPrecio === "desc";

        const data = shouldUseSearch
          ? await productosService.search({
              nombre: nombre.trim() || undefined,
              marca: marca.trim() || undefined,
              supermercado: supermercado.trim() || undefined,
              categoria: categoria.trim() || undefined,
              orden_precio: ordenPrecio,
            })
          : await productosService.getAll();

        setProductos(data);
      } catch (error: any) {
        console.error(error);
        Alert.alert(
          "Error",
          error?.response?.data?.detail ||
            "No se han podido cargar los productos."
        );
      } finally {
        setLoading(false);
        setSearching(false);
        setRefreshing(false);
      }
    },
    [categoria, hasFilters, marca, nombre, ordenPrecio, supermercado]
  );

  const loadListaDestino = useCallback(async () => {
    if (!isAddingToList || !listaIdNumber) {
      setListaDestino(null);
      setProductosEnLista([]);
      return;
    }

    try {
      const detalle = await listasService.getDetalle(listaIdNumber);

      setListaDestino(detalle);
      setProductosEnLista(detalle.productos ?? []);
    } catch (error: any) {
      console.error(error);
      Alert.alert(
        "Error",
        error?.response?.data?.detail ||
          "No se han podido cargar los productos actuales de la lista."
      );
    }
  }, [isAddingToList, listaIdNumber]);

  useEffect(() => {
    const loadInitialData = async () => {
      setLoading(true);

      await Promise.all([loadProductos(false), loadListaDestino()]);

      setLoading(false);
    };

    loadInitialData();
  }, [loadListaDestino]);

  const handleSearch = async () => {
    setSearching(true);
    await loadProductos(false);
  };

  const handleClearFilters = async () => {
    setNombre("");
    setMarca("");
    setSupermercado("");
    setCategoria("");
    setOrdenPrecio("asc");
    setSearching(true);

    try {
      const data = await productosService.getAll();
      setProductos(data);
    } catch (error: any) {
      console.error(error);
      Alert.alert(
        "Error",
        error?.response?.data?.detail ||
          "No se han podido cargar los productos."
      );
    } finally {
      setSearching(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await Promise.all([loadProductos(false), loadListaDestino()]);
  };

  const handleAddProducto = async (producto: Producto) => {
    if (!isAddingToList || !listaIdNumber) {
      Alert.alert(
        "Sin lista seleccionada",
        "Abre esta pantalla desde el detalle de una lista para añadir productos."
      );
      return;
    }

    if (!canAddToSelectedList) {
      Alert.alert(
        "Solo visualización",
        "No tienes permisos para modificar productos en esta lista."
      );
      return;
    }

    try {
      setAddingProductId(producto.id_producto);

      const productoExistente = productosEnLista.find(
        (productoLista) => productoLista.producto_id === producto.id_producto
      );

      if (productoExistente) {
        await listasService.updateProducto(productoExistente.id_producto_lista, {
          cantidad: productoExistente.cantidad + 1,
        });
      } else {
        await listasService.addProducto({
          lista_id: listaIdNumber,
          producto_id: producto.id_producto,
          cantidad: 1,
        });
      }

      await loadListaDestino();
      setLastAddedProductId(producto.id_producto);

      Alert.alert(
        productoExistente ? "Cantidad actualizada" : "Producto añadido",
        productoExistente
          ? `${producto.nombre} ya estaba en la lista, así que se ha sumado una unidad.`
          : `${producto.nombre} se ha añadido a la lista.`,
        [
          {
            text: "Seguir añadiendo",
            style: "cancel",
          },
          {
            text: "Volver a la lista",
            onPress: () => router.back(),
          },
        ]
      );
    } catch (error: any) {
      console.error(error);
      Alert.alert(
        "Error",
        error?.response?.data?.detail ||
          "No se ha podido añadir el producto."
      );
    } finally {
      setAddingProductId(null);
    }
  };

  const getCantidadEnLista = (productoId: number) => {
    const productoLista = productosEnLista.find(
      (item) => item.producto_id === productoId
    );

    return productoLista?.cantidad ?? 0;
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={Colors.primary} />
        <Text style={styles.loadingText}>Cargando productos...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={productos}
        keyExtractor={(item) => item.id_producto.toString()}
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

            <View style={styles.headerRow}>
              <View style={styles.headerTextBox}>
                <Text style={styles.title}>Productos</Text>
                <Text style={styles.subtitle}>
                  {isAddingToList
                    ? "Selecciona productos para añadirlos a la lista."
                    : "Consulta, filtra y compara productos del catálogo."}
                </Text>
              </View>

              <TouchableOpacity
                style={styles.compareButton}
                onPress={() => router.push("/productos/comparar")}
              >
                <Text style={styles.compareButtonText}>Comparar precios</Text>
              </TouchableOpacity>
            </View>

            {isAddingToList && canAddToSelectedList ? (
              <View style={styles.infoBox}>
                <Text style={styles.infoTitle}>Modo añadir a lista</Text>
                <Text style={styles.infoText}>
                  Si añades un producto que ya está en la lista, se aumentará su
                  cantidad en vez de duplicarlo.
                </Text>
              </View>
            ) : null}

            {isAddingToList && !canAddToSelectedList ? (
              <View style={styles.readOnlyBox}>
                <Text style={styles.readOnlyTitle}>Solo visualización</Text>
                <Text style={styles.readOnlyText}>
                  Esta lista está compartida contigo en modo solo lectura.
                  Puedes consultar el catálogo, pero no añadir productos.
                </Text>
              </View>
            ) : null}

            <View style={styles.filtersBox}>
              <Text style={styles.filtersTitle}>Filtros de búsqueda</Text>

              <TextInput
                value={nombre}
                onChangeText={setNombre}
                placeholder="Buscar por nombre"
                placeholderTextColor={Colors.textMuted}
                style={styles.input}
                returnKeyType="search"
                onSubmitEditing={handleSearch}
              />

              <TextInput
                value={marca}
                onChangeText={setMarca}
                placeholder="Marca"
                placeholderTextColor={Colors.textMuted}
                style={styles.input}
                returnKeyType="search"
                onSubmitEditing={handleSearch}
              />

              <View style={styles.twoColumns}>
                <TextInput
                  value={supermercado}
                  onChangeText={setSupermercado}
                  placeholder="Supermercado"
                  placeholderTextColor={Colors.textMuted}
                  style={[styles.input, styles.columnInput]}
                  returnKeyType="search"
                  onSubmitEditing={handleSearch}
                />

                <TextInput
                  value={categoria}
                  onChangeText={setCategoria}
                  placeholder="Categoría"
                  placeholderTextColor={Colors.textMuted}
                  style={[styles.input, styles.columnInput]}
                  returnKeyType="search"
                  onSubmitEditing={handleSearch}
                />
              </View>

              <View style={styles.orderBox}>
                <Text style={styles.orderLabel}>Ordenar por precio</Text>

                <View style={styles.orderButtons}>
                  <TouchableOpacity
                    style={[
                      styles.orderButton,
                      ordenPrecio === "asc" && styles.orderButtonActive,
                    ]}
                    onPress={() => setOrdenPrecio("asc")}
                  >
                    <Text
                      style={[
                        styles.orderButtonText,
                        ordenPrecio === "asc" && styles.orderButtonTextActive,
                      ]}
                    >
                      Menor primero
                    </Text>
                  </TouchableOpacity>

                  <TouchableOpacity
                    style={[
                      styles.orderButton,
                      ordenPrecio === "desc" && styles.orderButtonActive,
                    ]}
                    onPress={() => setOrdenPrecio("desc")}
                  >
                    <Text
                      style={[
                        styles.orderButtonText,
                        ordenPrecio === "desc" && styles.orderButtonTextActive,
                      ]}
                    >
                      Mayor primero
                    </Text>
                  </TouchableOpacity>
                </View>
              </View>

              <View style={styles.filterActions}>
                <TouchableOpacity
                  style={[
                    styles.searchButton,
                    searching && styles.disabledButton,
                  ]}
                  onPress={handleSearch}
                  disabled={searching}
                >
                  <Text style={styles.searchButtonText}>
                    {searching ? "Buscando..." : "Buscar"}
                  </Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={styles.clearButton}
                  onPress={handleClearFilters}
                  disabled={searching}
                >
                  <Text style={styles.clearButtonText}>Limpiar</Text>
                </TouchableOpacity>
              </View>
            </View>

            <View style={styles.resultHeader}>
              <Text style={styles.resultCount}>
                {productos.length === 1
                  ? "1 producto encontrado"
                  : `${productos.length} productos encontrados`}
              </Text>

              {hasFilters || ordenPrecio === "desc" ? (
                <Text style={styles.activeFiltersText}>Filtros activos</Text>
              ) : null}
            </View>
          </View>
        }
        ListEmptyComponent={
          <View style={styles.emptyBox}>
            <Text style={styles.emptyTitle}>No se han encontrado productos.</Text>
            <Text style={styles.emptyText}>
              Prueba a limpiar los filtros o buscar con otros términos.
            </Text>
          </View>
        }
        renderItem={({ item }) => {
          const cantidadEnLista = getCantidadEnLista(item.id_producto);
          const isAdding = addingProductId === item.id_producto;
          const wasLastAdded = lastAddedProductId === item.id_producto;

          return (
            <View style={styles.card}>
              <View style={styles.productRow}>
                <ProductImage
                  uri={item.imagen_url}
                  productName={item.nombre}
                  size={76}
                />

                <View style={styles.productInfo}>
                  <View style={styles.cardTopRow}>
                    <Text style={styles.productName}>{item.nombre}</Text>

                    {cantidadEnLista > 0 ? (
                      <View style={styles.inListBadge}>
                        <Text style={styles.inListBadgeText}>
                          x{cantidadEnLista}
                        </Text>
                      </View>
                    ) : null}
                  </View>

                  <Text style={styles.productMeta}>
                    {item.marca ?? "Sin marca"} · {item.supermercado}
                  </Text>

                  <Text style={styles.productMeta}>
                    {item.categoria ?? "Sin categoría"} ·{" "}
                    {item.unidad_medida ?? "Sin unidad"}
                  </Text>

                  <Text style={styles.price}>
                    {formatEuro(item.precio_unitario)}
                  </Text>
                </View>
              </View>

              {isAddingToList && canAddToSelectedList ? (
                <TouchableOpacity
                  style={[styles.addButton, isAdding && styles.disabledButton]}
                  onPress={() => handleAddProducto(item)}
                  disabled={isAdding}
                >
                  <Text style={styles.addButtonText}>
                    {isAdding
                      ? "Añadiendo..."
                      : cantidadEnLista > 0
                      ? "Sumar otra unidad"
                      : "Añadir"}
                  </Text>
                </TouchableOpacity>
              ) : null}

              {wasLastAdded ? (
                <Text style={styles.addedHint}>Último producto actualizado</Text>
              ) : null}
            </View>
          );
        }}
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
  backButton: {
    marginBottom: 16,
  },
  backButtonText: {
    fontSize: 16,
    fontWeight: "800",
    color: Colors.title,
  },
  headerRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: 12,
    marginBottom: 14,
  },
  headerTextBox: {
    flex: 1,
  },
  title: {
    fontSize: 30,
    fontWeight: "900",
    color: Colors.title,
  },
  subtitle: {
    marginTop: 4,
    color: Colors.textMuted,
    fontSize: 14,
    lineHeight: 20,
  },
  compareButton: {
    backgroundColor: Colors.black,
    paddingVertical: 11,
    paddingHorizontal: 14,
    borderRadius: 14,
  },
  compareButtonText: {
    color: Colors.white,
    fontWeight: "900",
    fontSize: 13,
  },
  infoBox: {
    backgroundColor: Colors.backgroundAlt,
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 16,
    padding: 14,
    marginBottom: 14,
  },
  infoTitle: {
    color: Colors.title,
    fontWeight: "900",
    marginBottom: 4,
  },
  infoText: {
    color: Colors.textMuted,
    lineHeight: 20,
  },
  readOnlyBox: {
    backgroundColor: "#FEF3C7",
    borderWidth: 1,
    borderColor: "#FCD34D",
    borderRadius: 16,
    padding: 14,
    marginBottom: 14,
  },
  readOnlyTitle: {
    color: "#92400E",
    fontWeight: "900",
    marginBottom: 4,
  },
  readOnlyText: {
    color: "#92400E",
    lineHeight: 20,
  },
  filtersBox: {
    backgroundColor: Colors.surface,
    borderRadius: 18,
    padding: 14,
    marginBottom: 14,
    gap: 10,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  filtersTitle: {
    color: Colors.title,
    fontWeight: "900",
    fontSize: 16,
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
  twoColumns: {
    flexDirection: "row",
    gap: 10,
  },
  columnInput: {
    flex: 1,
  },
  orderBox: {
    backgroundColor: Colors.backgroundAlt,
    borderRadius: 14,
    padding: 12,
    gap: 10,
  },
  orderLabel: {
    color: Colors.title,
    fontWeight: "900",
    fontSize: 13,
  },
  orderButtons: {
    flexDirection: "row",
    gap: 8,
  },
  orderButton: {
    flex: 1,
    minHeight: 38,
    borderRadius: 12,
    backgroundColor: Colors.surface,
    borderWidth: 1,
    borderColor: Colors.border,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 10,
  },
  orderButtonActive: {
    backgroundColor: Colors.primary,
    borderColor: Colors.primary,
  },
  orderButtonText: {
    color: Colors.textMuted,
    fontWeight: "900",
    fontSize: 13,
  },
  orderButtonTextActive: {
    color: Colors.white,
  },
  filterActions: {
    flexDirection: "row",
    gap: 10,
  },
  searchButton: {
    flex: 1,
    backgroundColor: Colors.primary,
    paddingVertical: 13,
    borderRadius: 14,
    alignItems: "center",
  },
  searchButtonText: {
    color: Colors.white,
    fontWeight: "900",
    fontSize: 16,
  },
  clearButton: {
    minWidth: 94,
    backgroundColor: Colors.card,
    paddingVertical: 13,
    borderRadius: 14,
    alignItems: "center",
    borderWidth: 1,
    borderColor: Colors.border,
  },
  clearButtonText: {
    color: Colors.title,
    fontWeight: "900",
  },
  resultHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
    gap: 10,
  },
  resultCount: {
    color: Colors.textMuted,
    fontWeight: "700",
  },
  activeFiltersText: {
    color: Colors.primary,
    fontWeight: "900",
    fontSize: 12,
  },
  card: {
    backgroundColor: Colors.surface,
    borderRadius: 18,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: Colors.border,
  },
    productRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 14,
    marginBottom: 12,
  },
  productInfo: {
    flex: 1,
  },
  cardTopRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 10,
  },
  productName: {
    flex: 1,
    fontSize: 18,
    fontWeight: "900",
    color: Colors.title,
    marginBottom: 4,
  },
  inListBadge: {
    backgroundColor: Colors.backgroundAlt,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 999,
  },
  inListBadgeText: {
    color: Colors.primary,
    fontWeight: "900",
    fontSize: 12,
  },
  productMeta: {
    color: Colors.textMuted,
    fontSize: 14,
    marginBottom: 2,
  },
  price: {
    fontSize: 19,
    fontWeight: "900",
    color: Colors.text,
    marginTop: 8,
  },
  addButton: {
    backgroundColor: Colors.black,
    paddingVertical: 12,
    borderRadius: 14,
    alignItems: "center",
  },
  disabledButton: {
    opacity: 0.6,
  },
  addButtonText: {
    color: Colors.white,
    fontWeight: "900",
  },
  addedHint: {
    marginTop: 8,
    color: Colors.success,
    fontWeight: "800",
    textAlign: "center",
  },
  emptyBox: {
    paddingVertical: 44,
    alignItems: "center",
  },
  emptyTitle: {
    color: Colors.title,
    fontWeight: "900",
    fontSize: 17,
    marginBottom: 6,
  },
  emptyText: {
    color: Colors.textMuted,
    fontSize: 14,
    textAlign: "center",
    lineHeight: 20,
  },
});