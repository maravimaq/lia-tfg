import React, { useEffect, useState } from "react";
import {
  Alert,
  Image,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import * as ImagePicker from "expo-image-picker";
import { router } from "expo-router";

import Screen from "@/src/components/Screen";
import ProfileSideMenu from "@/src/components/ProfileSideMenu";
import { useAuth } from "@/src/hooks/useAuth";
import { Colors } from "@/src/constants/colors";
import { profileImageStorage } from "@/src/lib/profileImage";

const commonFriends: {
  id: number;
  name: string;
  email: string;
  avatar: string;
}[] = [];

function getInitials(name?: string) {
  if (!name) return "L";
  return name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export default function ProfileScreen() {
  const { user, refreshProfile, signOut } = useAuth();
  const [menuVisible, setMenuVisible] = useState(false);
  const [imageUri, setImageUri] = useState<string | null>(null);

  useEffect(() => {
    refreshProfile().catch(() => undefined);

    profileImageStorage.get().then((uri) => {
      if (uri) setImageUri(uri);
    });
  }, []);

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
      quality: 0.8,
    });

    if (!result.canceled && result.assets?.length > 0) {
      const uri = result.assets[0].uri;
      setImageUri(uri);
      await profileImageStorage.set(uri);
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

        <Pressable style={styles.tab} onPress={() => router.push("/(protected)/profile/preferences")}>
          <Text style={styles.tabText}>Preferencias</Text>
        </Pressable>

        <View style={styles.tab}>
          <Text style={styles.tabText}>Analíticas</Text>
        </View>
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

        <Text style={styles.friendsTitle}>Amigos</Text>

        {commonFriends.length === 0 ? (
          <View style={styles.emptyFriendsBox}>
            <Text style={styles.emptyFriendsText}>
              Todavía no tienes amigos o contactos en común para mostrar.
            </Text>
          </View>
        ) : (
          commonFriends.map((friend) => (
            <View key={friend.id} style={styles.friendRow}>
              <Image source={{ uri: friend.avatar }} style={styles.friendAvatar} />
              <View>
                <Text style={styles.friendName}>{friend.name}</Text>
                <Text style={styles.friendEmail}>{friend.email}</Text>
              </View>
            </View>
          ))
        )}
      </View>

      <ProfileSideMenu
        visible={menuVisible}
        onClose={() => setMenuVisible(false)}
        onLogout={handleLogout}
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
    marginBottom: 12,
  },
  emptyFriendsBox: {
    minHeight: 90,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: Colors.border,
    backgroundColor: Colors.surface,
    padding: 16,
    alignItems: "center",
    justifyContent: "center",
  },
  emptyFriendsText: {
    textAlign: "center",
    color: Colors.textMuted,
    lineHeight: 22,
  },
  friendRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 12,
  },
  friendAvatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    marginRight: 12,
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
});