import { useCallback, useMemo, useState } from "react";
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

import { ProductImage } from "@/src/components/ProductImage";
import { AppColors } from "@/src/constants/colors";
import { useAppTheme } from "@/src/hooks/useAppTheme";
import { productosService } from "@/src/services/productos";
import { Producto } from "@/src/types/producto";

type ProductoComparado = {
  nombre: string;
  productos: Producto[];
};

function formatEuro(value?: string | number | null) {
  const numberValue = Number(value ?? 0);

  if (Number.isNaN(numberValue)) {
    return "0,00 €";
  }

  return `${numberValue.toFixed(2).replace(".", ",")} €`;
}

function normalizeText(value?: string | null) {
  return (value ?? "").trim().toLowerCase();
}

function groupProductosByNombre(productos: Producto[]): ProductoComparado[] {
  const grouped = new Map<string, Producto[]>();

  productos.forEach((producto) => {
    const key = normalizeText(producto.nombre);

    if (!grouped.has(key)) {
      grouped.set(key, []);
    }

    grouped.get(key)?.push(producto);
  });

  return Array.from(grouped.entries()).map(([, productosGrupo]) => {
    const productosOrdenados = [...productosGrupo].sort(
      (a, b) => Number(a.precio_unitario) - Number(b.precio_unitario)
    );

    return {
      nombre: productosOrdenados[0]?.nombre ?? "Producto",
      productos: productosOrdenados,
    };
  });
}

export default function CompararProductosScreen() {
  const [nombre, setNombre] = useState("");
  const [productos, setProductos] = useState<Producto[]>([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const { colors } = useAppTheme();
  const styles = useMemo(() => createStyles(colors), [colors]);

  const productosAgrupados = useMemo(() => {
    return groupProductosByNombre(productos);
  }, [productos]);

  const handleComparar = useCallback(async () => {
    const nombreBusqueda = nombre.trim();

    if (!nombreBusqueda) {
      Alert.alert(
        "Campo obligatorio",
        "Introduce el nombre del producto que quieres comparar."
      );
      return;
    }

    try {
      setLoading(true);
      setHasSearched(true);

      const data = await productosService.comparar(nombreBusqueda);

      setProductos(data);
    } catch (error: any) {
      console.error(error);
      Alert.alert(
        "Error",
        error?.response?.data?.detail ||
        "No se han podido comparar los productos."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [nombre]);

  const handleRefresh = async () => {
    if (!hasSearched) return;

    setRefreshing(true);
    await handleComparar();
  };

  const handleClear = () => {
    setNombre("");
    setProductos([]);
    setHasSearched(false);
  };

  const renderProductoComparado = ({ item }: { item: ProductoComparado }) => {
    const precioMinimo = Math.min(
      ...item.productos.map((producto) => Number(producto.precio_unitario))
    );

    return (
      <View style={styles.resultCard}>
        <Text style={styles.productGroupTitle}>{item.nombre}</Text>

        <View style={styles.divider} />

        {item.productos.map((producto) => {
          const precio = Number(producto.precio_unitario);
          const isCheapest = precio === precioMinimo;

          return (
            <View key={producto.id_producto} style={styles.supermarketRow}>
              <ProductImage
                uri={producto.imagen_url}
                productName={producto.nombre}
                size={56}
              />

              <View style={styles.supermarketInfo}>
                <View style={styles.supermarketTopRow}>
                  <Text style={styles.supermarketName}>
                    {producto.supermercado}
                  </Text>

                  {isCheapest ? (
                    <View style={styles.cheapestBadge}>
                      <Text style={styles.cheapestBadgeText}>Más barato</Text>
                    </View>
                  ) : null}
                </View>

                <Text style={styles.productMeta}>
                  {producto.marca ?? "Sin marca"} ·{" "}
                  {producto.unidad_medida ?? "Sin unidad"}
                </Text>

                <Text style={styles.productPrice}>
                  {formatEuro(producto.precio_unitario)}
                </Text>
              </View>
            </View>
          );
        })}
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <FlatList
        data={productosAgrupados}
        keyExtractor={(item, index) => `${item.nombre}-${index}`}
        renderItem={renderProductoComparado}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            tintColor={colors.primary}
            colors={[colors.primary]}
            progressBackgroundColor={colors.surface}
          />
        }
        ListHeaderComponent={
          <View>
            <View style={styles.topBar}>
              <TouchableOpacity
                style={styles.backButton}
                onPress={() => router.replace("/productos")}              >
                <Text style={styles.backButtonText}>‹</Text>
              </TouchableOpacity>

              <Text style={styles.title}>Comparación de precios</Text>

              <View style={styles.headerSpacer} />
            </View>

            <View style={styles.searchBox}>
              <TextInput
                value={nombre}
                onChangeText={setNombre}
                placeholder="Buscar producto"
                placeholderTextColor={colors.textMuted}
                style={styles.searchInput}
                returnKeyType="search"
                onSubmitEditing={handleComparar}
                editable={!loading}
              />

              <TouchableOpacity
                style={[styles.searchIconButton, loading && styles.disabledButton]}
                onPress={handleComparar}
                disabled={loading}
              >
                <Text style={styles.searchIcon}>⌕</Text>
              </TouchableOpacity>
            </View>

            {hasSearched ? (
              <View style={styles.searchActions}>
                <Text style={styles.sectionSubtitle}>
                  Resultados de tu búsqueda
                </Text>

                <TouchableOpacity onPress={handleClear} disabled={loading}>
                  <Text style={styles.clearText}>Limpiar</Text>
                </TouchableOpacity>
              </View>
            ) : (
              <Text style={styles.sectionSubtitle}>Busca un producto para comparar</Text>
            )}

            {loading ? (
              <View style={styles.loadingBox}>
                <ActivityIndicator size="large" color={colors.primary} />
                <Text style={styles.loadingText}>Comparando precios...</Text>
              </View>
            ) : null}
          </View>
        }
        ListEmptyComponent={
          !loading ? (
            <View style={styles.emptyBox}>
              <Text style={styles.emptyTitle}>
                {hasSearched
                  ? "No se han encontrado resultados."
                  : "Todavía no has buscado ningún producto."}
              </Text>

              <Text style={styles.emptyText}>
                {hasSearched
                  ? "Prueba con otro nombre de producto o una búsqueda más general."
                  : "Escribe el nombre de un producto para comparar su precio entre supermercados."}
              </Text>
            </View>
          ) : null
        }
        contentContainerStyle={styles.listContent}
      />
    </View>
  );
}

const createStyles = (colors: AppColors) => StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    paddingHorizontal: 20,
    paddingTop: 18,
  },
  listContent: {
    paddingBottom: 34,
  },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 18,
  },
  backButton: {
    width: 42,
    height: 42,
    alignItems: "center",
    justifyContent: "center",
  },
  backButtonText: {
    fontSize: 36,
    color: colors.title,
    fontWeight: "600",
    marginTop: -4,
  },
  title: {
    flex: 1,
    textAlign: "center",
    fontSize: 18,
    fontWeight: "900",
    color: colors.title,
  },
  headerSpacer: {
    width: 42,
    height: 42,
  },
  searchBox: {
    alignSelf: "center",
    width: "100%",
    maxWidth: 520,
    minHeight: 48,
    borderRadius: 999,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    flexDirection: "row",
    alignItems: "center",
    paddingLeft: 18,
    paddingRight: 6,
    marginBottom: 14,
  },
  searchInput: {
    flex: 1,
    color: colors.text,
    fontSize: 16,
    paddingVertical: 10,
  },
  searchIconButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: "center",
    justifyContent: "center",
  },
  searchIcon: {
    fontSize: 24,
    color: colors.title,
    fontWeight: "900",
  },
  searchActions: {
    maxWidth: 520,
    width: "100%",
    alignSelf: "center",
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 18,
  },
  sectionSubtitle: {
    textAlign: "center",
    color: colors.textMuted,
    fontSize: 15,
    marginBottom: 18,
  },
  clearText: {
    color: colors.primary,
    fontWeight: "900",
  },
  loadingBox: {
    alignItems: "center",
    marginTop: 18,
    marginBottom: 18,
  },
  loadingText: {
    marginTop: 10,
    color: colors.textMuted,
    fontWeight: "700",
  },
  resultCard: {
    width: "100%",
    maxWidth: 520,
    alignSelf: "center",
    backgroundColor: colors.surface,
    borderRadius: 14,
    padding: 18,
    borderWidth: 1,
    borderColor: colors.border,
    marginBottom: 24,
    shadowColor: "#000",
    shadowOpacity: 0.08,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 3 },
    elevation: 3,
  },
  productGroupTitle: {
    fontSize: 17,
    fontWeight: "900",
    color: colors.title,
    marginBottom: 12,
  },
  divider: {
    height: 1,
    backgroundColor: colors.border,
    marginBottom: 12,
  },
  supermarketRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    marginBottom: 16,
  },
  supermarketInfo: {
    flex: 1,
    marginLeft: 12,
  },
  supermarketTopRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 2,
  },
  supermarketName: {
    fontSize: 16,
    fontWeight: "800",
    color: colors.text,
  },
  productMeta: {
    color: colors.textMuted,
    fontSize: 13,
    marginBottom: 2,
  },
  productPrice: {
    color: colors.title,
    fontSize: 15,
    fontWeight: "900",
  },
  cheapestBadge: {
    backgroundColor: "#ECFDF5",
    borderRadius: 999,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  cheapestBadgeText: {
    color: "#166534",
    fontSize: 11,
    fontWeight: "900",
  },
  emptyBox: {
    width: "100%",
    maxWidth: 520,
    alignSelf: "center",
    backgroundColor: colors.surface,
    borderRadius: 16,
    padding: 22,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: "center",
  },
  emptyTitle: {
    color: colors.title,
    fontWeight: "900",
    fontSize: 17,
    marginBottom: 6,
    textAlign: "center",
  },
  emptyText: {
    color: colors.textMuted,
    textAlign: "center",
    lineHeight: 20,
  },
  disabledButton: {
    opacity: 0.6,
  },
});