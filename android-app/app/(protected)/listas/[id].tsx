import { useCallback, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Modal,
  RefreshControl,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { router, useFocusEffect, useLocalSearchParams } from "expo-router";

import { Colors } from "@/src/constants/colors";
import { useAuth } from "@/src/hooks/useAuth";
import { historialService } from "@/src/services/historial";
import { listasService } from "@/src/services/listas";
import {
  ListaCompraDetalle,
  ProductoLista,
  TipoCompartido,
} from "@/src/types/lista";

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

export default function DetalleListaScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { user } = useAuth();

  const listaId = Number(id);

  const [lista, setLista] = useState<ListaCompraDetalle | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const [productoAEliminar, setProductoAEliminar] =
    useState<ProductoLista | null>(null);
  const [deletingProduct, setDeletingProduct] = useState(false);
  const [updatingProductId, setUpdatingProductId] = useState<number | null>(
    null
  );

  const [editingName, setEditingName] = useState(false);
  const [nombreEditado, setNombreEditado] = useState("");
  const [savingName, setSavingName] = useState(false);

  const [deleteListModalVisible, setDeleteListModalVisible] = useState(false);
  const [deletingList, setDeletingList] = useState(false);

  const [shareModalVisible, setShareModalVisible] = useState(false);
  const [shareEmail, setShareEmail] = useState("");
  const [shareTipoCompartido, setShareTipoCompartido] =
    useState<TipoCompartido>("edicion");
  const [sharing, setSharing] = useState(false);

  const [finishListModalVisible, setFinishListModalVisible] = useState(false);
  const [finishingList, setFinishingList] = useState(false);

  const [exitSharedModalVisible, setExitSharedModalVisible] = useState(false);
  const [exitingSharedList, setExitingSharedList] = useState(false);

  const isOwner = useMemo(() => {
    if (!lista || !user) return false;
    return lista.usuario_id === user.id_usuario;
  }, [lista, user]);

  const canModifyProducts = useMemo(() => {
    if (!lista) return false;

    return isOwner || lista.tipo_compartido === "edicion";
  }, [isOwner, lista]);

  const accessLabel = useMemo(() => {
    if (!lista) return "";

    if (isOwner) {
      return "Lista propia";
    }

    if (lista.tipo_compartido === "edicion") {
      return "Lista compartida contigo · con privilegios";
    }

    if (lista.tipo_compartido === "visualizacion") {
      return "Lista compartida contigo · solo visualización";
    }

    return "Lista compartida contigo";
  }, [isOwner, lista]);

  const loadDetalle = useCallback(async () => {
    if (!listaId || Number.isNaN(listaId)) {
      Alert.alert("Error", "Identificador de lista no válido.");
      router.replace("/listas");
      return;
    }

    try {
      const data = await listasService.getDetalle(listaId);
      setLista(data);
      setNombreEditado(data.nombre_lista);
    } catch (error: any) {
      console.error(error);
      Alert.alert(
        "Error",
        error?.response?.data?.detail || "No se ha podido cargar la lista."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [listaId]);

  useFocusEffect(
    useCallback(() => {
      loadDetalle();
    }, [loadDetalle])
  );

  const handleRefresh = () => {
    setRefreshing(true);
    loadDetalle();
  };

  const handleSaveName = async () => {
    if (!lista) return;

    const nombre = nombreEditado.trim();

    if (!nombre) {
      Alert.alert("Campo obligatorio", "La lista necesita un nombre.");
      return;
    }

    if (nombre === lista.nombre_lista) {
      setEditingName(false);
      return;
    }

    try {
      setSavingName(true);

      const listaActualizada = await listasService.update(lista.id_lista, {
        nombre_lista: nombre,
      });

      setLista((prev) =>
        prev
          ? {
            ...prev,
            nombre_lista: listaActualizada.nombre_lista,
            fecha_modificacion: listaActualizada.fecha_modificacion,
            compartida: listaActualizada.compartida,
          }
          : prev
      );

      setEditingName(false);
    } catch (error: any) {
      console.error(error);
      Alert.alert(
        "Error",
        error?.response?.data?.detail || "No se ha podido actualizar la lista."
      );
    } finally {
      setSavingName(false);
    }
  };

  const handleCancelEditName = () => {
    setNombreEditado(lista?.nombre_lista ?? "");
    setEditingName(false);
  };

  const handleDeleteProducto = (productoLista: ProductoLista) => {
    if (!canModifyProducts) {
      Alert.alert(
        "Solo visualización",
        "No tienes permisos para modificar productos en esta lista."
      );
      return;
    }

    setProductoAEliminar(productoLista);
  };

  const confirmarDeleteProducto = async () => {
    if (!productoAEliminar) {
      return;
    }

    try {
      setDeletingProduct(true);

      await listasService.deleteProducto(productoAEliminar.id_producto_lista);
      setProductoAEliminar(null);
      await loadDetalle();
    } catch (error: any) {
      console.error(error);
      Alert.alert(
        "Error",
        error?.response?.data?.detail || "No se ha podido eliminar el producto."
      );
    } finally {
      setDeletingProduct(false);
    }
  };

  const cancelarDeleteProducto = () => {
    if (!deletingProduct) {
      setProductoAEliminar(null);
    }
  };

  const handleIncreaseQuantity = async (productoLista: ProductoLista) => {
    if (!canModifyProducts) {
      Alert.alert(
        "Solo visualización",
        "No tienes permisos para modificar productos en esta lista."
      );
      return;
    }

    try {
      setUpdatingProductId(productoLista.id_producto_lista);

      await listasService.updateProducto(productoLista.id_producto_lista, {
        cantidad: productoLista.cantidad + 1,
      });

      await loadDetalle();
    } catch (error: any) {
      console.error(error);
      Alert.alert(
        "Error",
        error?.response?.data?.detail ||
        "No se ha podido actualizar la cantidad."
      );
    } finally {
      setUpdatingProductId(null);
    }
  };

  const handleDecreaseQuantity = async (productoLista: ProductoLista) => {
    if (!canModifyProducts) {
      Alert.alert(
        "Solo visualización",
        "No tienes permisos para modificar productos en esta lista."
      );
      return;
    }

    if (productoLista.cantidad <= 1) {
      handleDeleteProducto(productoLista);
      return;
    }

    try {
      setUpdatingProductId(productoLista.id_producto_lista);

      await listasService.updateProducto(productoLista.id_producto_lista, {
        cantidad: productoLista.cantidad - 1,
      });

      await loadDetalle();
    } catch (error: any) {
      console.error(error);
      Alert.alert(
        "Error",
        error?.response?.data?.detail ||
        "No se ha podido actualizar la cantidad."
      );
    } finally {
      setUpdatingProductId(null);
    }
  };

  const handleShareList = async () => {
    if (!lista) return;

    const email = shareEmail.trim();

    if (!email) {
      Alert.alert("Campo obligatorio", "Introduce el email del usuario.");
      return;
    }

    try {
      setSharing(true);

      await listasService.compartir(
        lista.id_lista,
        email,
        shareTipoCompartido
      );

      setShareEmail("");
      setShareTipoCompartido("edicion");
      setShareModalVisible(false);
      setLista((prev) => (prev ? { ...prev, compartida: true } : prev));

      Alert.alert(
        "Lista compartida",
        shareTipoCompartido === "edicion"
          ? "El usuario ya puede acceder y modificar productos de esta lista."
          : "El usuario ya puede ver esta lista, pero no modificarla."
      );
    } catch (error: any) {
      console.error(error);
      Alert.alert(
        "Error",
        error?.response?.data?.detail || "No se ha podido compartir la lista."
      );
    } finally {
      setSharing(false);
    }
  };

  const confirmarDeleteLista = async () => {
    if (!lista) return;

    try {
      setDeletingList(true);

      await listasService.delete(lista.id_lista);

      setDeleteListModalVisible(false);
      router.replace("/listas");
    } catch (error: any) {
      console.error(error);
      Alert.alert(
        "Error",
        error?.response?.data?.detail || "No se ha podido eliminar la lista."
      );
    } finally {
      setDeletingList(false);
    }
  };

  const confirmarFinalizarLista = async () => {
    if (!lista) return;

    try {
      setFinishingList(true);

      await historialService.finalizarLista(lista.id_lista);

      setFinishListModalVisible(false);

      Alert.alert(
        "Lista finalizada",
        "La lista se ha guardado correctamente en el historial.",
        [
          {
            text: "Ver historial",
            onPress: () => router.replace("/historial"),
          },
        ]
      );
    } catch (error: any) {
      console.error(error);
      Alert.alert(
        "Error",
        error?.response?.data?.detail || "No se ha podido finalizar la lista."
      );
    } finally {
      setFinishingList(false);
    }
  };

  const confirmarSalirDeCompartidos = async () => {
    if (!lista) return;

    try {
      setExitingSharedList(true);

      await listasService.salirDeCompartidos(lista.id_lista);

      setExitSharedModalVisible(false);

      router.replace("/listas");
    } catch (error: any) {
      console.error(error);
      Alert.alert(
        "Error",
        error?.response?.data?.detail ||
        "No se ha podido eliminar la lista de tus compartidos."
      );
    } finally {
      setExitingSharedList(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={Colors.primary} />
        <Text style={styles.loadingText}>Cargando lista...</Text>
      </View>
    );
  }

  if (!lista) {
    return (
      <View style={styles.center}>
        <Text style={styles.emptyTitle}>No se ha encontrado la lista.</Text>

        <TouchableOpacity
          style={[styles.primaryButton, styles.centerButton]}
          onPress={() => router.replace("/listas")}
        >
          <Text style={styles.primaryButtonText}>Volver</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={lista.productos}
        keyExtractor={(item) => item.id_producto_lista.toString()}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />
        }
        ListHeaderComponent={
          <View>
            <TouchableOpacity
              style={styles.backButton}
              onPress={() => router.replace("/listas")}
            >
              <Text style={styles.backButtonText}>← Volver</Text>
            </TouchableOpacity>

            <View style={styles.headerCard}>
              {editingName ? (
                <View style={styles.editNameBox}>
                  <TextInput
                    value={nombreEditado}
                    onChangeText={setNombreEditado}
                    style={styles.nameInput}
                    placeholder="Nombre de la lista"
                    placeholderTextColor={Colors.textMuted}
                    autoFocus
                    returnKeyType="done"
                    onSubmitEditing={handleSaveName}
                  />

                  <View style={styles.editNameActions}>
                    <TouchableOpacity
                      style={styles.secondarySmallButton}
                      onPress={handleCancelEditName}
                      disabled={savingName}
                    >
                      <Text style={styles.secondarySmallButtonText}>
                        Cancelar
                      </Text>
                    </TouchableOpacity>

                    <TouchableOpacity
                      style={[
                        styles.primarySmallButton,
                        savingName && styles.disabledButton,
                      ]}
                      onPress={handleSaveName}
                      disabled={savingName}
                    >
                      <Text style={styles.primarySmallButtonText}>
                        {savingName ? "Guardando..." : "Guardar"}
                      </Text>
                    </TouchableOpacity>
                  </View>
                </View>
              ) : (
                <View style={styles.titleRow}>
                  <View style={styles.titleBox}>
                    <Text style={styles.title}>{lista.nombre_lista}</Text>
                    <Text style={styles.ownerText}>{accessLabel}</Text>
                  </View>

                  {isOwner ? (
                    <TouchableOpacity
                      style={styles.editButton}
                      onPress={() => setEditingName(true)}
                    >
                      <Text style={styles.editButtonText}>Editar</Text>
                    </TouchableOpacity>
                  ) : null}
                </View>
              )}

              <View style={styles.summaryRow}>
                <View style={styles.summaryItem}>
                  <Text style={styles.summaryLabel}>Total estimado</Text>
                  <Text style={styles.summaryValue}>
                    {formatEuro(lista.total_estimado)}
                  </Text>
                </View>

                <View style={styles.summaryItem}>
                  <Text style={styles.summaryLabel}>Productos</Text>
                  <Text style={styles.summaryValue}>
                    {lista.productos.length}
                  </Text>
                </View>
              </View>

              <Text style={styles.updatedText}>
                Última modificación: {formatDate(lista.fecha_modificacion)}
              </Text>
            </View>

            {canModifyProducts ? (
              <View style={styles.actionGrid}>
                <TouchableOpacity
                  style={styles.primaryButton}
                  onPress={() =>
                    router.push({
                      pathname: "/productos",
                      params: { listaId: lista.id_lista.toString() },
                    })
                  }
                >
                  <Text style={styles.primaryButtonText}>Añadir producto</Text>
                </TouchableOpacity>

                {isOwner ? (
                  <TouchableOpacity
                    style={styles.secondaryButton}
                    onPress={() => setShareModalVisible(true)}
                  >
                    <Text style={styles.secondaryButtonText}>Compartir</Text>
                  </TouchableOpacity>
                ) : null}
              </View>
            ) : (
              <View style={styles.readOnlyBox}>
                <Text style={styles.readOnlyTitle}>Solo visualización</Text>
                <Text style={styles.readOnlyText}>
                  Puedes consultar esta lista, pero no añadir, eliminar ni
                  modificar productos.
                </Text>
              </View>
            )}

            <TouchableOpacity
              style={styles.aiAssistantButton}
              onPress={() =>
                router.push({
                  pathname: "/listas/chatbot",
                  params: {
                    listaId: lista.id_lista.toString(),
                    nombreLista: lista.nombre_lista,
                  },
                })
              }
            >
              <View style={styles.aiAssistantIcon}>
                <Text style={styles.aiAssistantIconText}>IA</Text>
              </View>

              <View style={styles.aiAssistantTextBox}>
                <Text style={styles.aiAssistantTitle}>Asistente de lista</Text>
                <Text style={styles.aiAssistantSubtitle}>
                  Analiza importes, cantidades y posibles ahorros.
                </Text>
              </View>

              <Text style={styles.aiAssistantArrow}>›</Text>
            </TouchableOpacity>

            {isOwner ? (
              <View style={styles.ownerActions}>
                <TouchableOpacity
                  style={[
                    styles.finishButton,
                    finishingList && styles.disabledButton,
                  ]}
                  onPress={() => setFinishListModalVisible(true)}
                  disabled={finishingList}
                >
                  <Text style={styles.finishButtonText}>Finalizar lista</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={styles.dangerOutlineButton}
                  onPress={() => setDeleteListModalVisible(true)}
                >
                  <Text style={styles.dangerOutlineButtonText}>
                    Eliminar lista
                  </Text>
                </TouchableOpacity>
              </View>
            ) : null}

            {!isOwner ? (
              <TouchableOpacity
                style={styles.dangerOutlineButton}
                onPress={() => setExitSharedModalVisible(true)}
                disabled={exitingSharedList}
              >
                <Text style={styles.dangerOutlineButtonText}>
                  Quitar de mis compartidos
                </Text>
              </TouchableOpacity>
            ) : null}

            <Text style={styles.sectionTitle}>Productos de la lista</Text>
          </View>
        }
        ListEmptyComponent={
          <View style={styles.emptyBox}>
            <Text style={styles.emptyTitle}>
              Esta lista todavía no tiene productos.
            </Text>
            <Text style={styles.emptyText}>
              {canModifyProducts
                ? "Pulsa en “Añadir producto” para buscar en el catálogo."
                : "El propietario todavía no ha añadido productos a esta lista."}
            </Text>
          </View>
        }
        renderItem={({ item }) => {
          const isUpdating = updatingProductId === item.id_producto_lista;

          return (
            <View style={styles.card}>
              <View style={styles.productInfo}>
                <Text style={styles.productName}>{item.producto.nombre}</Text>

                <Text style={styles.productMeta}>
                  {item.producto.marca ?? "Sin marca"} ·{" "}
                  {item.producto.supermercado}
                </Text>

                <Text style={styles.productMeta}>
                  Precio unidad: {formatEuro(item.producto.precio_unitario)}
                </Text>

                <Text style={styles.productTotal}>
                  Subtotal: {formatEuro(item.precio_estimado)}
                </Text>
              </View>

              {canModifyProducts ? (
                <View style={styles.actions}>
                  <TouchableOpacity
                    style={[
                      styles.quantityButton,
                      isUpdating && styles.disabledButton,
                    ]}
                    onPress={() => handleDecreaseQuantity(item)}
                    disabled={isUpdating}
                  >
                    <Text style={styles.quantityButtonText}>-</Text>
                  </TouchableOpacity>

                  <Text style={styles.quantity}>{item.cantidad}</Text>

                  <TouchableOpacity
                    style={[
                      styles.quantityButton,
                      isUpdating && styles.disabledButton,
                    ]}
                    onPress={() => handleIncreaseQuantity(item)}
                    disabled={isUpdating}
                  >
                    <Text style={styles.quantityButtonText}>+</Text>
                  </TouchableOpacity>

                  <TouchableOpacity
                    style={styles.deleteButton}
                    onPress={() => handleDeleteProducto(item)}
                    disabled={isUpdating}
                  >
                    <Text style={styles.deleteButtonText}>Eliminar</Text>
                  </TouchableOpacity>
                </View>
              ) : (
                <View style={styles.readOnlyQuantityRow}>
                  <Text style={styles.readOnlyQuantityText}>
                    Cantidad: {item.cantidad}
                  </Text>
                </View>
              )}
            </View>
          );
        }}
      />

      <Modal
        visible={productoAEliminar !== null}
        transparent
        animationType="fade"
        onRequestClose={cancelarDeleteProducto}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>Eliminar producto</Text>

            <Text style={styles.modalText}>
              ¿Quieres eliminar{" "}
              <Text style={styles.modalStrong}>
                {productoAEliminar?.producto.nombre}
              </Text>{" "}
              de la lista?
            </Text>

            <View style={styles.modalActions}>
              <TouchableOpacity
                style={styles.modalCancelButton}
                onPress={cancelarDeleteProducto}
                disabled={deletingProduct}
              >
                <Text style={styles.modalCancelText}>Cancelar</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[
                  styles.modalDeleteButton,
                  deletingProduct && styles.disabledButton,
                ]}
                onPress={confirmarDeleteProducto}
                disabled={deletingProduct}
              >
                <Text style={styles.modalDeleteText}>
                  {deletingProduct ? "Eliminando..." : "Eliminar"}
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      <Modal
        visible={finishListModalVisible}
        transparent
        animationType="fade"
        onRequestClose={() =>
          !finishingList && setFinishListModalVisible(false)
        }
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>Finalizar lista</Text>

            <Text style={styles.modalText}>
              ¿Seguro que quieres finalizar{" "}
              <Text style={styles.modalStrong}>{lista.nombre_lista}</Text>? Se
              guardará una copia con sus productos y total en el historial.
            </Text>

            <View style={styles.modalActions}>
              <TouchableOpacity
                style={styles.modalCancelButton}
                onPress={() => setFinishListModalVisible(false)}
                disabled={finishingList}
              >
                <Text style={styles.modalCancelText}>Cancelar</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[
                  styles.modalPrimaryButton,
                  finishingList && styles.disabledButton,
                ]}
                onPress={confirmarFinalizarLista}
                disabled={finishingList}
              >
                <Text style={styles.modalPrimaryText}>
                  {finishingList ? "Finalizando..." : "Finalizar"}
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      <Modal
        visible={deleteListModalVisible}
        transparent
        animationType="fade"
        onRequestClose={() => !deletingList && setDeleteListModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>Eliminar lista</Text>

            <Text style={styles.modalText}>
              ¿Seguro que quieres eliminar{" "}
              <Text style={styles.modalStrong}>{lista.nombre_lista}</Text>?
              También se eliminarán sus productos.
            </Text>

            <View style={styles.modalActions}>
              <TouchableOpacity
                style={styles.modalCancelButton}
                onPress={() => setDeleteListModalVisible(false)}
                disabled={deletingList}
              >
                <Text style={styles.modalCancelText}>Cancelar</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[
                  styles.modalDeleteButton,
                  deletingList && styles.disabledButton,
                ]}
                onPress={confirmarDeleteLista}
                disabled={deletingList}
              >
                <Text style={styles.modalDeleteText}>
                  {deletingList ? "Eliminando..." : "Eliminar"}
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      <Modal
        visible={exitSharedModalVisible}
        transparent
        animationType="fade"
        onRequestClose={() =>
          !exitingSharedList && setExitSharedModalVisible(false)
        }
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>Quitar de mis compartidos</Text>

            <Text style={styles.modalText}>
              ¿Seguro que quieres quitar{" "}
              <Text style={styles.modalStrong}>{lista.nombre_lista}</Text> de
              tus compartidos? La lista no se eliminará para su propietario.
            </Text>

            <View style={styles.modalActions}>
              <TouchableOpacity
                style={styles.modalCancelButton}
                onPress={() => setExitSharedModalVisible(false)}
                disabled={exitingSharedList}
              >
                <Text style={styles.modalCancelText}>Cancelar</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[
                  styles.modalDeleteButton,
                  exitingSharedList && styles.disabledButton,
                ]}
                onPress={confirmarSalirDeCompartidos}
                disabled={exitingSharedList}
              >
                <Text style={styles.modalDeleteText}>
                  {exitingSharedList ? "Quitando..." : "Quitar"}
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      <Modal
        visible={shareModalVisible}
        transparent
        animationType="fade"
        onRequestClose={() => !sharing && setShareModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>Compartir lista</Text>
            <Text style={styles.modalText}>
              Introduce el email del usuario y elige el tipo de acceso.
            </Text>

            <TextInput
              value={shareEmail}
              onChangeText={setShareEmail}
              placeholder="usuario@email.com"
              placeholderTextColor={Colors.textMuted}
              style={styles.modalInput}
              autoCapitalize="none"
              keyboardType="email-address"
              editable={!sharing}
            />

            <View style={styles.permissionBox}>
              <TouchableOpacity
                style={[
                  styles.permissionOption,
                  shareTipoCompartido === "edicion" &&
                  styles.permissionOptionActive,
                ]}
                onPress={() => setShareTipoCompartido("edicion")}
                disabled={sharing}
              >
                <Text
                  style={[
                    styles.permissionOptionTitle,
                    shareTipoCompartido === "edicion" &&
                    styles.permissionOptionTitleActive,
                  ]}
                >
                  Con privilegios
                </Text>
                <Text style={styles.permissionOptionText}>
                  Puede ver la lista y modificar productos.
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[
                  styles.permissionOption,
                  shareTipoCompartido === "visualizacion" &&
                  styles.permissionOptionActive,
                ]}
                onPress={() => setShareTipoCompartido("visualizacion")}
                disabled={sharing}
              >
                <Text
                  style={[
                    styles.permissionOptionTitle,
                    shareTipoCompartido === "visualizacion" &&
                    styles.permissionOptionTitleActive,
                  ]}
                >
                  Solo visualización
                </Text>
                <Text style={styles.permissionOptionText}>
                  Puede ver la lista, pero no modificarla.
                </Text>
              </TouchableOpacity>
            </View>

            <View style={styles.modalActions}>
              <TouchableOpacity
                style={styles.modalCancelButton}
                onPress={() => setShareModalVisible(false)}
                disabled={sharing}
              >
                <Text style={styles.modalCancelText}>Cancelar</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[
                  styles.modalPrimaryButton,
                  sharing && styles.disabledButton,
                ]}
                onPress={handleShareList}
                disabled={sharing}
              >
                <Text style={styles.modalPrimaryText}>
                  {sharing ? "Compartiendo..." : "Compartir"}
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
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: Colors.background,
    padding: 20,
  },
  centerButton: {
    flex: 0,
    marginTop: 12,
    paddingHorizontal: 24,
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
  headerCard: {
    backgroundColor: Colors.surface,
    borderRadius: 22,
    padding: 18,
    borderWidth: 1,
    borderColor: Colors.border,
    marginBottom: 14,
  },
  titleRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 12,
    alignItems: "flex-start",
  },
  titleBox: {
    flex: 1,
  },
  title: {
    fontSize: 28,
    fontWeight: "900",
    color: Colors.title,
    marginBottom: 4,
  },
  ownerText: {
    color: Colors.textMuted,
    fontWeight: "700",
  },
  editButton: {
    backgroundColor: Colors.card,
    borderWidth: 1,
    borderColor: Colors.border,
    paddingVertical: 9,
    paddingHorizontal: 12,
    borderRadius: 12,
  },
  editButtonText: {
    color: Colors.primary,
    fontWeight: "900",
  },
  editNameBox: {
    gap: 10,
  },
  nameInput: {
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 18,
    fontWeight: "800",
    color: Colors.title,
    backgroundColor: Colors.white,
  },
  editNameActions: {
    flexDirection: "row",
    justifyContent: "flex-end",
    gap: 10,
  },
  primarySmallButton: {
    backgroundColor: Colors.primary,
    borderRadius: 12,
    paddingVertical: 10,
    paddingHorizontal: 14,
  },
  primarySmallButtonText: {
    color: Colors.white,
    fontWeight: "900",
  },
  secondarySmallButton: {
    backgroundColor: Colors.card,
    borderRadius: 12,
    paddingVertical: 10,
    paddingHorizontal: 14,
  },
  secondarySmallButtonText: {
    color: Colors.title,
    fontWeight: "800",
  },
  summaryRow: {
    flexDirection: "row",
    gap: 10,
    marginTop: 18,
    marginBottom: 10,
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
  updatedText: {
    color: Colors.textMuted,
    fontSize: 13,
  },
  actionGrid: {
    flexDirection: "row",
    gap: 10,
    marginBottom: 10,
  },
  primaryButton: {
    flex: 1,
    minHeight: 48,
    backgroundColor: Colors.primary,
    borderRadius: 16,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 14,
  },
  primaryButtonText: {
    color: Colors.white,
    fontSize: 15,
    fontWeight: "900",
  },
  secondaryButton: {
    flex: 1,
    minHeight: 48,
    backgroundColor: Colors.black,
    borderRadius: 16,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 14,
  },
  secondaryButtonText: {
    color: Colors.white,
    fontSize: 15,
    fontWeight: "900",
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
  aiAssistantButton: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    backgroundColor: Colors.surface,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: Colors.border,
    padding: 14,
    marginBottom: 14,
  },
  aiAssistantIcon: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: Colors.backgroundAlt,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  aiAssistantIconText: {
    color: Colors.primary,
    fontSize: 13,
    fontWeight: "900",
  },
  aiAssistantTextBox: {
    flex: 1,
  },
  aiAssistantTitle: {
    color: Colors.title,
    fontSize: 16,
    fontWeight: "900",
    marginBottom: 3,
  },
  aiAssistantSubtitle: {
    color: Colors.textMuted,
    fontSize: 13,
    lineHeight: 18,
  },
  aiAssistantArrow: {
    color: Colors.primary,
    fontSize: 28,
    fontWeight: "900",
  },
  ownerActions: {
    gap: 10,
    marginBottom: 18,
  },
  finishButton: {
    minHeight: 44,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#86EFAC",
    backgroundColor: "#ECFDF5",
    alignItems: "center",
    justifyContent: "center",
  },
  finishButtonText: {
    color: "#166534",
    fontWeight: "900",
  },
  dangerOutlineButton: {
    minHeight: 44,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#FCA5A5",
    backgroundColor: "#FEF2F2",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 18,
  },
  dangerOutlineButtonText: {
    color: "#B91C1C",
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
  },
  productInfo: {
    marginBottom: 12,
  },
  productName: {
    fontSize: 18,
    fontWeight: "900",
    color: Colors.title,
    marginBottom: 4,
  },
  productMeta: {
    fontSize: 14,
    color: Colors.textMuted,
    marginBottom: 2,
  },
  productTotal: {
    fontSize: 15,
    fontWeight: "900",
    color: Colors.text,
    marginTop: 6,
  },
  actions: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  quantityButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: Colors.card,
    borderWidth: 1,
    borderColor: Colors.border,
    alignItems: "center",
    justifyContent: "center",
  },
  quantityButtonText: {
    fontSize: 20,
    fontWeight: "900",
    color: Colors.title,
  },
  quantity: {
    fontSize: 18,
    fontWeight: "900",
    minWidth: 24,
    textAlign: "center",
    color: Colors.title,
  },
  deleteButton: {
    marginLeft: "auto",
    paddingVertical: 9,
    paddingHorizontal: 12,
    borderRadius: 12,
    backgroundColor: "#FEE2E2",
  },
  deleteButtonText: {
    color: "#B91C1C",
    fontWeight: "900",
  },
  readOnlyQuantityRow: {
    backgroundColor: Colors.backgroundAlt,
    borderRadius: 12,
    paddingVertical: 10,
    paddingHorizontal: 12,
    alignSelf: "flex-start",
  },
  readOnlyQuantityText: {
    color: Colors.title,
    fontWeight: "900",
  },
  emptyBox: {
    paddingVertical: 34,
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
    marginBottom: 18,
  },
  modalStrong: {
    fontWeight: "900",
    color: Colors.title,
  },
  modalInput: {
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
    backgroundColor: Colors.white,
    color: Colors.text,
    marginBottom: 18,
  },
  permissionBox: {
    gap: 10,
    marginBottom: 18,
  },
  permissionOption: {
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 14,
    padding: 14,
    backgroundColor: Colors.white,
  },
  permissionOptionActive: {
    borderColor: Colors.primary,
    backgroundColor: Colors.backgroundAlt,
  },
  permissionOptionTitle: {
    color: Colors.title,
    fontWeight: "900",
    marginBottom: 4,
  },
  permissionOptionTitleActive: {
    color: Colors.primary,
  },
  permissionOptionText: {
    color: Colors.textMuted,
    lineHeight: 19,
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
  modalDeleteButton: {
    paddingVertical: 11,
    paddingHorizontal: 16,
    borderRadius: 12,
    backgroundColor: Colors.danger,
  },
  modalDeleteText: {
    color: Colors.white,
    fontWeight: "900",
  },
  modalPrimaryButton: {
    paddingVertical: 11,
    paddingHorizontal: 16,
    borderRadius: 12,
    backgroundColor: Colors.primary,
  },
  modalPrimaryText: {
    color: Colors.white,
    fontWeight: "900",
  },
  disabledButton: {
    opacity: 0.6,
  },
});