import React, { useEffect, useState } from "react";
import { Alert, Image, StyleSheet, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";

import Screen from "@/src/components/Screen";
import AppButton from "@/src/components/AppButton";
import { Colors } from "@/src/constants/colors";
import { userService } from "@/src/services/user";
import { UserResponse } from "@/src/types/user";

function getAvatarFallback(name?: string) {
  return `https://ui-avatars.com/api/?name=${encodeURIComponent(name || "LIA")}&background=7F83F5&color=fff`;
}

export default function PublicProfileScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [profile, setProfile] = useState<UserResponse | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        if (!id) return;
        const data = await userService.getPublicProfile(Number(id));
        setProfile(data);
      } catch (error: any) {
        Alert.alert("Error", error?.response?.data?.detail || "No se pudo cargar el perfil");
      }
    };

    load();
  }, [id]);

  return (
    <Screen>
      <View style={styles.header}>
        <Text style={styles.title}>Perfil público</Text>
      </View>

      <View style={styles.card}>
        <Image
          source={{ uri: profile?.avatar_url || getAvatarFallback(profile?.nombre_completo) }}
          style={styles.avatar}
        />
        <Text style={styles.name}>{profile?.nombre_completo || "-"}</Text>
        <Text style={styles.username}>@{profile?.nombre_usuario || "-"}</Text>
        <Text style={styles.email}>{profile?.email || "-"}</Text>
      </View>

      <AppButton title="Volver" variant="ghost" onPress={() => router.back()} style={{ marginTop: 12 }} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    marginBottom: 20,
  },
  title: {
    fontSize: 28,
    fontWeight: "800",
    color: Colors.title,
  },
  card: {
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 20,
    padding: 20,
    alignItems: "center",
    backgroundColor: Colors.surface,
  },
  avatar: {
    width: 90,
    height: 90,
    borderRadius: 45,
    marginBottom: 10,
  },
  name: {
    fontSize: 18,
    fontWeight: "800",
    color: Colors.title,
  },
  username: {
    marginTop: 4,
    color: Colors.textMuted,
  },
  email: {
    marginTop: 10,
    color: Colors.text,
  },
});
