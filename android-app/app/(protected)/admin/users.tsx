import React, { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  View,
} from "react-native";
import { router, useLocalSearchParams } from "expo-router";

import Screen from "@/src/components/Screen";
import AppButton from "@/src/components/AppButton";
import AppInput from "@/src/components/AppInput";
import { Colors } from "@/src/constants/colors";
import { useAuth } from "@/src/hooks/useAuth";
import { adminService } from "@/src/services/admin";
import { AdminUserCreatePayload, AdminUserListItem, AdminUserUpdatePayload } from "@/src/types/admin";

const FETCH_SIZE = 100;

type ModalState =
  | { type: "none" }
  | { type: "create" }
  | { type: "edit"; user: AdminUserListItem }
  | { type: "deactivate"; user: AdminUserListItem }
  | { type: "delete"; user: AdminUserListItem };

export default function AdminUsersScreen() {
  const { user } = useAuth();
  const params = useLocalSearchParams<{ search?: string }>();

  const [users, setUsers] = useState<AdminUserListItem[]>([]);
  const [searchInput, setSearchInput] = useState("");
  const [searchApplied, setSearchApplied] = useState("");
  const [loading, setLoading] = useState(false);
  const [modalState, setModalState] = useState<ModalState>({ type: "none" });

  const handleBack = () => {
    if (router.canGoBack()) {
      router.back();
      return;
    }

    router.replace("/(protected)/admin");
  };

  const [form, setForm] = useState<AdminUserCreatePayload>({
    nombre_usuario: "",
    nombre_completo: "",
    email: "",
    contrasena: "",
    telefono: "",
    rol_nombre: "usuario",
    estado: "activo",
  });

  const modalTitle = useMemo(() => {
    if (modalState.type === "create") return "Crear Usuario";
    if (modalState.type === "edit") return `Editar Usuario: ${modalState.user.nombre_usuario}`;
    if (modalState.type === "deactivate") return `¿Desactivar Usuario: ${modalState.user.nombre_usuario}?`;
    if (modalState.type === "delete") return `¿Eliminar Usuario: ${modalState.user.nombre_usuario}?`;
    return "";
  }, [modalState]);

  const loadUsers = async (search = searchApplied) => {
    try {
      setLoading(true);
      const response = await adminService.listUsers(1, FETCH_SIZE, search || undefined);
      setUsers(response.items);
    } catch (error: any) {
      Alert.alert("Error", error?.response?.data?.detail || "No se pudieron cargar los usuarios");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user?.rol_id !== 2) return;

    const initialSearch = typeof params.search === "string" ? params.search : "";
    setSearchInput(initialSearch);
    setSearchApplied(initialSearch);
    loadUsers(initialSearch);
  }, [user?.rol_id, params.search]);

  const openCreate = () => {
    setForm({
      nombre_usuario: "",
      nombre_completo: "",
      email: "",
      contrasena: "",
      telefono: "",
      rol_nombre: "usuario",
      estado: "activo",
    });
    setModalState({ type: "create" });
  };

  const openEdit = (item: AdminUserListItem) => {
    setForm({
      nombre_usuario: item.nombre_usuario,
      nombre_completo: item.nombre_completo,
      email: item.email,
      contrasena: "",
      telefono: item.telefono || "",
      rol_nombre: item.rol_nombre === "administrador" ? "administrador" : "usuario",
      estado: item.estado === "inactivo" ? "inactivo" : "activo",
    });
    setModalState({ type: "edit", user: item });
  };

  const submitCreate = async () => {
    try {
      await adminService.createUser(form);
      setModalState({ type: "none" });
      await loadUsers(searchApplied);
    } catch (error: any) {
      Alert.alert("Error", error?.response?.data?.detail || "No se pudo crear el usuario");
    }
  };

  const submitEdit = async () => {
    if (modalState.type !== "edit") return;

    const payload: AdminUserUpdatePayload = {
      nombre_usuario: form.nombre_usuario,
      nombre_completo: form.nombre_completo,
      email: form.email,
      telefono: form.telefono,
      rol_nombre: form.rol_nombre,
      estado: form.estado,
    };

    try {
      await adminService.updateUser(modalState.user.id_usuario, payload);
      setModalState({ type: "none" });
      await loadUsers(searchApplied);
    } catch (error: any) {
      Alert.alert("Error", error?.response?.data?.detail || "No se pudo actualizar el usuario");
    }
  };

  const submitDeactivate = async () => {
    if (modalState.type !== "deactivate") return;

    try {
      await adminService.deactivateUser(modalState.user.id_usuario);
      setModalState({ type: "none" });
      await loadUsers(searchApplied);
    } catch (error: any) {
      Alert.alert("Error", error?.response?.data?.detail || "No se pudo desactivar el usuario");
    }
  };

  const submitDelete = async () => {
    if (modalState.type !== "delete") return;

    try {
      await adminService.deleteUser(modalState.user.id_usuario);
      setModalState({ type: "none" });
      await loadUsers(searchApplied);
    } catch (error: any) {
      Alert.alert("Error", error?.response?.data?.detail || "No se pudo eliminar el usuario");
    }
  };

  if (user?.rol_id !== 2) {
    return (
      <Screen>
        <Text style={styles.noAccess}>No tienes permisos para ver esta sección.</Text>
      </Screen>
    );
  }

  return (
    <Screen>
      <View style={styles.headerRow}>
        <Pressable onPress={handleBack}>
          <Text style={styles.back}>←</Text>
        </Pressable>
        <Text style={styles.title}>Gestionar Usuarios</Text>
        <View style={{ width: 16 }} />
      </View>

      <View style={styles.searchRow}>
        <View style={styles.searchWrap}>
          <AppInput
            placeholder="Buscar Usuario"
            value={searchInput}
            onChangeText={setSearchInput}
            style={styles.searchInput}
          />
          <Pressable
            onPress={() => {
              setSearchApplied(searchInput.trim());
              loadUsers(searchInput.trim());
            }}
            style={styles.searchIconButton}
          >
            <Text style={styles.searchIcon}>⌕</Text>
          </Pressable>
        </View>

        <Pressable onPress={openCreate} style={styles.newUserBtn}>
          <Text style={styles.newUserBtnText}>➕ Nuevo Usuario</Text>
        </Pressable>
      </View>

      <View style={styles.tableHeader}>
        <Text style={[styles.th, styles.colName]}>Nombre</Text>
        <Text style={[styles.th, styles.colEmail]}>Email</Text>
        <Text style={[styles.th, styles.colRole]}>Rol</Text>
        <Text style={[styles.th, styles.colActions]}>Acciones</Text>
      </View>

      <ScrollView style={styles.tableBody}>
        {loading ? <Text style={styles.helper}>Cargando...</Text> : null}

        {!loading && users.length === 0 ? <Text style={styles.helper}>No hay usuarios.</Text> : null}

        {users.map((item) => (
          <View key={item.id_usuario} style={styles.tr}>
            <Text style={[styles.td, styles.colName]}>{item.nombre_usuario}</Text>
            <Text style={[styles.td, styles.colEmail]} numberOfLines={1}>{item.email}</Text>
            <Text style={[styles.td, styles.colRole]}>{item.rol_nombre === "administrador" ? "Admin" : "Usuario"}</Text>
            <View style={[styles.actionCell, styles.colActions]}>
              <Pressable onPress={() => openEdit(item)}>
                <Text style={styles.actionEdit}>✎</Text>
              </Pressable>
              {item.estado === "activo" ? (
                <Pressable onPress={() => setModalState({ type: "deactivate", user: item })}>
                  <Text style={styles.actionDeactivate}>⏻</Text>
                </Pressable>
              ) : (
                <Pressable onPress={() => adminService.activateUser(item.id_usuario).then(() => loadUsers(searchApplied))}>
                  <Text style={styles.actionActivate}>↻</Text>
                </Pressable>
              )}
              <Pressable onPress={() => setModalState({ type: "delete", user: item })}>
                <Text style={styles.actionDelete}>🗑</Text>
              </Pressable>
            </View>
          </View>
        ))}
      </ScrollView>

      <Modal visible={modalState.type !== "none"} transparent animationType="fade" onRequestClose={() => setModalState({ type: "none" })}>
        <View style={styles.modalBackdrop}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>{modalTitle}</Text>

            {modalState.type === "deactivate" ? (
              <>
                <Text style={styles.modalInfo}>Esto impedirá que acceda a la aplicación.</Text>
                <Text style={styles.modalInfo}>Puedes reactivarlo en cualquier momento.</Text>
                <View style={styles.modalActions}>
                  <AppButton title="Cancelar" variant="ghost" onPress={() => setModalState({ type: "none" })} style={styles.modalBtn} />
                  <AppButton title="Desactivar" variant="danger" onPress={submitDeactivate} style={styles.modalBtn} />
                </View>
              </>
            ) : null}

            {modalState.type === "delete" ? (
              <>
                <Text style={styles.modalInfo}>Esta acción elimina el usuario y no se puede deshacer.</Text>
                <View style={styles.modalActions}>
                  <AppButton title="Cancelar" variant="ghost" onPress={() => setModalState({ type: "none" })} style={styles.modalBtn} />
                  <AppButton title="Eliminar" variant="danger" onPress={submitDelete} style={styles.modalBtn} />
                </View>
              </>
            ) : null}

            {modalState.type === "create" || modalState.type === "edit" ? (
              <>
                <AppInput
                  label="Nombre de Usuario"
                  value={form.nombre_usuario}
                  onChangeText={(value) => setForm((prev) => ({ ...prev, nombre_usuario: value }))}
                />
                <AppInput
                  label="Email"
                  value={form.email}
                  keyboardType="email-address"
                  autoCapitalize="none"
                  onChangeText={(value) => setForm((prev) => ({ ...prev, email: value }))}
                />
                <AppInput
                  label="Nombre Completo"
                  value={form.nombre_completo}
                  onChangeText={(value) => setForm((prev) => ({ ...prev, nombre_completo: value }))}
                />

                {modalState.type === "create" ? (
                  <AppInput
                    label="Contraseña"
                    value={form.contrasena}
                    secureTextEntry
                    onChangeText={(value) => setForm((prev) => ({ ...prev, contrasena: value }))}
                  />
                ) : null}

                <View style={styles.switchRow}>
                  <Text style={styles.switchLabel}>¿Activo?</Text>
                  <Switch
                    value={form.estado === "activo"}
                    onValueChange={(value) => setForm((prev) => ({ ...prev, estado: value ? "activo" : "inactivo" }))}
                  />
                </View>

                <View style={styles.roleRow}>
                  <Text style={styles.roleLabel}>Rol</Text>
                  <View style={styles.roleActions}>
                    <Pressable
                      style={[styles.roleChip, form.rol_nombre === "usuario" && styles.roleChipActive]}
                      onPress={() => setForm((prev) => ({ ...prev, rol_nombre: "usuario" }))}
                    >
                      <Text style={styles.roleChipText}>Usuario</Text>
                    </Pressable>
                    <Pressable
                      style={[styles.roleChip, form.rol_nombre === "administrador" && styles.roleChipActive]}
                      onPress={() => setForm((prev) => ({ ...prev, rol_nombre: "administrador" }))}
                    >
                      <Text style={styles.roleChipText}>Admin</Text>
                    </Pressable>
                  </View>
                </View>

                <View style={styles.modalActions}>
                  <AppButton title="Cancelar" variant="ghost" onPress={() => setModalState({ type: "none" })} style={styles.modalBtn} />
                  <AppButton
                    title={modalState.type === "create" ? "Crear" : "Editar"}
                    onPress={modalState.type === "create" ? submitCreate : submitEdit}
                    style={styles.modalBtn}
                  />
                </View>
              </>
            ) : null}
          </View>
        </View>
      </Modal>
    </Screen>
  );
}

const styles = StyleSheet.create({
  noAccess: { color: Colors.text, marginTop: 20 },
  headerRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: 8 },
  back: { fontSize: 28, color: Colors.title },
  title: { fontSize: 26, fontWeight: "800", color: Colors.title },
  searchRow: { flexDirection: "row", gap: 8, marginBottom: 10 },
  searchWrap: { flex: 1, position: "relative" },
  searchInput: { paddingRight: 40 },
  searchIconButton: { position: "absolute", right: 10, top: 17 },
  searchIcon: { fontSize: 20, color: Colors.text },
  newUserBtn: {
    minWidth: 130,
    borderRadius: 12,
    backgroundColor: Colors.black,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 10,
  },
  newUserBtnText: { color: Colors.white, fontWeight: "800", fontSize: 14 },
  tableHeader: {
    flexDirection: "row",
    borderWidth: 1,
    borderColor: Colors.textMuted,
    backgroundColor: Colors.card,
    paddingVertical: 8,
    paddingHorizontal: 6,
    borderTopLeftRadius: 10,
    borderTopRightRadius: 10,
  },
  tableBody: {
    minHeight: 260,
    maxHeight: 420,
    borderWidth: 1,
    borderTopWidth: 0,
    borderColor: Colors.textMuted,
    borderBottomLeftRadius: 10,
    borderBottomRightRadius: 10,
    backgroundColor: Colors.surface,
  },
  tr: {
    flexDirection: "row",
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
    alignItems: "center",
    paddingVertical: 8,
    paddingHorizontal: 6,
  },
  th: { fontSize: 12, fontWeight: "800", color: Colors.title },
  td: { fontSize: 12, color: Colors.text },
  colName: { flex: 1.3 },
  colEmail: { flex: 2 },
  colRole: { flex: 1 },
  colActions: { flex: 1.1 },
  actionCell: { flexDirection: "row", justifyContent: "space-around" },
  actionEdit: { color: Colors.title, fontSize: 18 },
  actionDeactivate: { color: Colors.danger, fontSize: 18 },
  actionActivate: { color: Colors.success, fontSize: 18 },
  actionDelete: { color: Colors.danger, fontSize: 18 },
  helper: { textAlign: "center", color: Colors.textMuted, marginTop: 10 },
  modalBackdrop: {
    flex: 1,
    justifyContent: "center",
    backgroundColor: "rgba(0,0,0,0.35)",
    paddingHorizontal: 18,
  },
  modalCard: {
    backgroundColor: "#d8d8de",
    borderRadius: 24,
    borderWidth: 1,
    borderColor: Colors.textMuted,
    padding: 16,
  },
  modalTitle: { color: Colors.title, fontSize: 36, fontWeight: "700", marginBottom: 12 },
  modalInfo: { color: Colors.text, marginBottom: 8, fontSize: 22 },
  modalActions: { flexDirection: "row", gap: 8, marginTop: 8 },
  modalBtn: { flex: 1 },
  switchRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 12 },
  switchLabel: { color: Colors.text, fontWeight: "700" },
  roleRow: { marginBottom: 10 },
  roleLabel: { color: Colors.text, fontWeight: "700", marginBottom: 6 },
  roleActions: { flexDirection: "row", gap: 8 },
  roleChip: {
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 10,
    paddingVertical: 8,
    paddingHorizontal: 12,
    backgroundColor: Colors.surface,
  },
  roleChipActive: { backgroundColor: Colors.softBlue, borderColor: Colors.primary },
  roleChipText: { color: Colors.title, fontWeight: "700" },
});