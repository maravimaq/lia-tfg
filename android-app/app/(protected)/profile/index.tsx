import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Image,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import * as ImagePicker from "expo-image-picker";
import { router, useFocusEffect } from "expo-router";

import Screen from "@/src/components/Screen";
import ProfileSideMenu from "@/src/components/ProfileSideMenu";
import AppInput from "@/src/components/AppInput";
import AppButton from "@/src/components/AppButton";
import { useAuth } from "@/src/hooks/useAuth";
import { Colors } from "@/src/constants/colors";
import { userService } from "@/src/services/user";
import { DiscoverUserResponse, IncomingFollowRequestItem } from "@/src/types/user";

function getInitials(name?: string) {
  if (!name) return "L";
  return name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function getAvatarFallback(name?: string) {
  return `https://ui-avatars.com/api/?name=${encodeURIComponent(name || "LIA")}&background=7F83F5&color=fff`;
}

export default function ProfileScreen() {
  const { user, refreshProfile, signOut, setUser } = useAuth();
  const [menuVisible, setMenuVisible] = useState(false);
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [users, setUsers] = useState<DiscoverUserResponse[]>([]);
  const [incomingRequests, setIncomingRequests] = useState<IncomingFollowRequestItem[]>([]);
  const [search, setSearch] = useState("");
  const [friendsLoading, setFriendsLoading] = useState(false);
  const [followingUserId, setFollowingUserId] = useState<number | null>(null);
  const [requestActionId, setRequestActionId] = useState<number | null>(null);

  const loadFriendsData = async (query = "") => {
    setFriendsLoading(true);
    try {
      const [discovery, incoming] = await Promise.all([
        userService.discoverUsers(query),
        userService.getIncomingFollowRequests(),
      ]);
      setUsers(discovery);
      setIncomingRequests(incoming);
    } catch (error: any) {
      Alert.alert("Error", error?.response?.data?.detail || "No se pudo cargar la sección de amigos");
    } finally {
      setFriendsLoading(false);
    }
  };

  useEffect(() => {
    refreshProfile().catch(() => undefined);
    loadFriendsData().catch(() => undefined);
  }, []);

  useFocusEffect(
    useCallback(() => {
      loadFriendsData(search).catch(() => undefined);

      const intervalId = setInterval(() => {
        loadFriendsData(search).catch(() => undefined);
      }, 10000);

      return () => clearInterval(intervalId);
    }, [search])
  );

  useEffect(() => {
    setImageUri(user?.avatar_url ?? null);
  }, [user?.avatar_url]);

  useEffect(() => {
    const timeout = setTimeout(() => {
      loadFriendsData(search).catch(() => undefined);
    }, 350);

    return () => clearTimeout(timeout);
  }, [search]);

  const incomingCountLabel = useMemo(() => {
    if (incomingRequests.length === 0) return "Sin solicitudes pendientes";
    return `${incomingRequests.length} solicitud(es) pendiente(s)`;
  }, [incomingRequests.length]);

  const handlePickImage = async () => {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();

    if (!permission.granted) {
      Alert.alert("Permiso requerido", "Debes permitir acceso a tus fotos para cambiar la imagen.");
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["images"],
      allowsEditing: true,
      aspect: [1, 1],
      quality: 0.55,
      base64: true,
    });

    if (!result.canceled && result.assets?.length > 0) {
      const asset = result.assets[0];

      if (!asset.base64) {
        Alert.alert("Error", "No se pudo leer la imagen seleccionada.");
        return;
      }

      const mimeType = asset.mimeType || "image/jpeg";
      const avatarDataUri = `data:${mimeType};base64,${asset.base64}`;

      try {
        setImageUri(avatarDataUri);
        const updatedUser = await userService.updateMe({ avatar_url: avatarDataUri });
        setUser(updatedUser);
        await loadFriendsData(search);
      } catch (error: any) {
        setImageUri(user?.avatar_url ?? null);
        Alert.alert("Error", error?.response?.data?.detail || "No se pudo guardar la imagen de perfil");
      }
    }
  };

  const handleLogout = async () => {
    try {
      await signOut();
      router.replace("/(auth)/sign-in");
    } catch (error) {
      console.log("Error al cerrar sesión:", error);
      router.replace("/(auth)/sign-in");
    }
  };

  const handleDeleteAccount = async () => {
    try {
      await userService.requestAccountAction({ tipo: "eliminacion" });
      await signOut();
      router.replace("/(auth)/sign-in");
    } catch (error: any) {
      Alert.alert("Error", error?.response?.data?.detail || "No se pudo solicitar la eliminación de la cuenta");
    }
  };

  const handleSendFollowRequest = async (targetUserId: number) => {
    try {
      setFollowingUserId(targetUserId);
      await userService.sendFollowRequest(targetUserId);
      await loadFriendsData(search);
    } catch (error: any) {
      Alert.alert("Error", error?.response?.data?.detail || "No se pudo enviar la solicitud");
    } finally {
      setFollowingUserId(null);
    }
  };

  const handleRespondRequest = async (requestId: number, action: "aceptar" | "rechazar") => {
    try {
      setRequestActionId(requestId);
      await userService.respondFollowRequest(requestId, action);
      await loadFriendsData(search);
    } catch (error: any) {
      Alert.alert("Error", error?.response?.data?.detail || "No se pudo procesar la solicitud");
    } finally {
      setRequestActionId(null);
    }
  };

  return (
    <Screen>
      <View style={styles.topBar}>
        <View />
        <Pressable onPress={() => setMenuVisible(true)}>
          <Text style={styles.menuIcon}>☰</Text>
        </Pressable>
      </View>

      <View style={styles.header}>
        <Pressable onPress={handlePickImage} style={styles.avatarWrap}>
          {imageUri ? (
            <Image source={{ uri: imageUri }} style={styles.avatarImage} />
          ) : (
            <View style={styles.avatarFallback}>
              <Text style={styles.avatarText}>{getInitials(user?.nombre_completo)}</Text>
            </View>
          )}
          <View style={styles.editBadge}>
            <Text style={styles.editBadgeText}>✎</Text>
          </View>
        </Pressable>

        <Text style={styles.username}>@{user?.nombre_usuario}</Text>
      </View>

      <View style={styles.tabs}>
        <View style={[styles.tab, styles.tabActive]}>
          <Text style={[styles.tabText, styles.tabTextActive]}>Información Personal</Text>
        </View>

         <Pressable style={styles.tab} onPress={() => router.push("/(protected)/preferences")}>
          <Text style={styles.tabText}>Preferencias</Text>
        </Pressable>

        <View style={styles.tab}>
          <Text style={styles.tabText}>Analíticas</Text>
        </View>
      </View>

      <View style={styles.quickAccess}>
        <Pressable style={styles.quickCard} onPress={() => router.push("/listas")}>
          <Text style={styles.quickIcon}>🛒</Text>
          <View style={styles.quickTextBox}>
            <Text style={styles.quickTitle}>Mis listas</Text>
            <Text style={styles.quickSubtitle}>Crear y gestionar compras</Text>
          </View>
          <Text style={styles.quickArrow}>›</Text>
        </Pressable>

        <Pressable style={styles.quickCard} onPress={() => router.push("/productos")}>
          <Text style={styles.quickIcon}>🏷️</Text>
          <View style={styles.quickTextBox}>
            <Text style={styles.quickTitle}>Catálogo</Text>
            <Text style={styles.quickSubtitle}>Buscar productos y precios</Text>
          </View>
          <Text style={styles.quickArrow}>›</Text>
        </Pressable>
      </View>

      <View style={styles.card}>
        <Text style={styles.label}>Nombre completo:</Text>
        <View style={styles.rowField}>
          <Text style={styles.value}>{user?.nombre_completo || "-"}</Text>
          <Pressable onPress={() => router.push("/(protected)/profile/edit")}>
            <Text style={styles.editIcon}>✎</Text>
          </Pressable>
        </View>

        <Text style={styles.label}>Correo electrónico:</Text>
        <View style={styles.rowField}>
          <Text style={styles.value}>{user?.email || "-"}</Text>
          <Pressable onPress={() => router.push("/(protected)/profile/edit")}>
            <Text style={styles.editIcon}>✎</Text>
          </Pressable>
        </View>

        <Text style={styles.label}>Contraseña:</Text>
        <View style={styles.rowField}>
          <Text style={styles.value}>**************</Text>
          <Pressable onPress={() => router.push("/(protected)/profile/change-password")}>
            <Text style={styles.editIcon}>✎</Text>
          </Pressable>
        </View>

        <View style={styles.separator} />

        <Text style={styles.requestCounter}>{incomingCountLabel}</Text>

        {incomingRequests.length > 0 ? (
          <View style={styles.requestsBox}>
            {incomingRequests.map((request) => (
              <View key={request.id_solicitud_seguimiento} style={styles.requestRow}>
                <Image
                  source={{ uri: request.solicitante.avatar_url || getAvatarFallback(request.solicitante.nombre_completo) }}
                  style={styles.friendAvatar}
                />
                <View style={{ flex: 1 }}>
                  <Text style={styles.friendName}>{request.solicitante.nombre_completo}</Text>
                  <Text style={styles.friendEmail}>@{request.solicitante.nombre_usuario}</Text>
                </View>
                <View style={styles.requestActions}>
                  <AppButton
                    title="Aceptar"
                    variant="secondary"
                    onPress={() => handleRespondRequest(request.id_solicitud_seguimiento, "aceptar")}
                    disabled={requestActionId === request.id_solicitud_seguimiento}
                    style={styles.smallButton}
                  />
                  <AppButton
                    title="Rechazar"
                    variant="ghost"
                    onPress={() => handleRespondRequest(request.id_solicitud_seguimiento, "rechazar")}
                    disabled={requestActionId === request.id_solicitud_seguimiento}
                    style={styles.smallButton}
                  />
                </View>
              </View>
            ))}
          </View>
          ) : null}

        <AppInput
          label="Buscar usuarios"
          placeholder="Por usuario, nombre o correo"
          value={search}
          onChangeText={setSearch}
        />

        {friendsLoading ? (
          <Text style={styles.emptyFriendsText}>Cargando usuarios...</Text>
        ) : users.length === 0 ? (
          <Text style={styles.emptyFriendsText}>No hay usuarios para mostrar.</Text>
        ) : (
          users.map((person) => (
            <View key={person.id_usuario} style={styles.friendRow}>
              <Image
                source={{ uri: person.avatar_url || getAvatarFallback(person.nombre_completo) }}
                style={styles.friendAvatar}
              />
              <Pressable
                style={{ flex: 1 }}
                onPress={() => router.push(`/(protected)/profile/user/${person.id_usuario}`)}
              >
                <Text style={styles.friendName}>{person.nombre_completo}</Text>
                <Text style={styles.friendEmail}>{person.email}</Text>
              </Pressable>

              <AppButton
                title={
                  person.follow_status === "followed"
                    ? "Seguido"
                    : person.follow_status === "pending"
                    ? "Pendiente"
                    : "Seguir"
                }
                variant={person.follow_status === "none" ? "secondary" : "ghost"}
                onPress={() => handleSendFollowRequest(person.id_usuario)}
                disabled={person.follow_status !== "none" || followingUserId === person.id_usuario}
                style={styles.followButton}
              />
            </View>
          ))
        )}
      </View>

      <ProfileSideMenu
        visible={menuVisible}
        onClose={() => setMenuVisible(false)}
        onLogout={handleLogout}
        onDeleteAccount={handleDeleteAccount}
        isAdmin={user?.rol_id === 2}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  topBar: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 8,
  },
  menuIcon: {
    fontSize: 24,
    color: Colors.title,
    fontWeight: "800",
  },
  header: {
    alignItems: "center",
    marginBottom: 16,
  },
  avatarWrap: {
    position: "relative",
    marginBottom: 10,
  },
  avatarImage: {
    width: 108,
    height: 108,
    borderRadius: 54,
  },
  avatarFallback: {
    width: 108,
    height: 108,
    borderRadius: 54,
    backgroundColor: Colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  avatarText: {
    color: Colors.white,
    fontSize: 30,
    fontWeight: "800",
  },
  editBadge: {
    position: "absolute",
    right: 2,
    bottom: 2,
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: Colors.surface,
    borderWidth: 1,
    borderColor: Colors.border,
    alignItems: "center",
    justifyContent: "center",
  },
  editBadgeText: {
    color: Colors.title,
    fontWeight: "800",
  },
  username: {
    fontSize: 16,
    fontWeight: "700",
    color: Colors.textMuted,
  },
  tabs: {
    flexDirection: "row",
    gap: 8,
    marginBottom: 18,
  },
  tab: {
    flex: 1,
    minHeight: 38,
    borderRadius: 20,
    backgroundColor: Colors.card,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 8,
  },
  tabActive: {
    backgroundColor: Colors.black,
  },
  tabText: {
    fontSize: 12,
    color: Colors.text,
    fontWeight: "600",
    textAlign: "center",
  },
  tabTextActive: {
    color: Colors.white,
  },
  quickAccess: {
    gap: 10,
    marginBottom: 18,
  },
  quickCard: {
    minHeight: 74,
    borderRadius: 20,
    backgroundColor: Colors.surface,
    borderWidth: 1,
    borderColor: Colors.border,
    paddingHorizontal: 14,
    paddingVertical: 12,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  quickIcon: {
    fontSize: 24,
  },
  quickTextBox: {
    flex: 1,
  },
  quickTitle: {
    color: Colors.title,
    fontSize: 16,
    fontWeight: "800",
    marginBottom: 2,
  },
  quickSubtitle: {
    color: Colors.textMuted,
    fontSize: 13,
  },
  quickArrow: {
    color: Colors.textMuted,
    fontSize: 28,
    fontWeight: "700",
  },
  card: {
    backgroundColor: "rgba(255,255,255,0.88)",
    borderRadius: 22,
    padding: 18,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  label: {
    color: Colors.title,
    fontSize: 14,
    fontWeight: "700",
    marginTop: 10,
    marginBottom: 6,
  },
  rowField: {
    minHeight: 48,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: Colors.border,
    backgroundColor: Colors.surface,
    paddingHorizontal: 14,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  value: {
    color: Colors.textMuted,
    fontSize: 15,
    flex: 1,
    paddingRight: 10,
  },
  editIcon: {
    fontSize: 20,
    color: Colors.title,
  },
  separator: {
    height: 1,
    backgroundColor: Colors.border,
    marginVertical: 18,
  },
  friendsTitle: {
    fontSize: 16,
    fontWeight: "800",
    color: Colors.title,
    marginBottom: 4,
  },
  requestCounter: {
    marginBottom: 12,
    color: Colors.textMuted,
  },
  requestsBox: {
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 16,
    padding: 10,
    marginBottom: 12,
    backgroundColor: Colors.card,
  },
  requestRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    marginBottom: 10,
  },
  requestActions: {
    flexDirection: "row",
    gap: 6,
  },
  smallButton: {
    minHeight: 36,
    justifyContent: "center",
  },
  emptyFriendsText: {
    textAlign: "center",
    color: Colors.textMuted,
    lineHeight: 22,
    marginVertical: 8,
  },
  friendRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 12,
    gap: 10,
  },
  friendAvatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
  },
  friendName: {
    fontSize: 14,
    fontWeight: "700",
    color: Colors.text,
  },
  friendEmail: {
    fontSize: 12,
    color: Colors.textMuted,
  },
  followButton: {
    minHeight: 36,
    minWidth: 88,
  },
});