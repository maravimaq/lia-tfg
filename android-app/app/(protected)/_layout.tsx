import { useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Redirect, Stack, router, usePathname } from "expo-router";

import ProfileSideMenu from "@/src/components/ProfileSideMenu";
import { Colors } from "@/src/constants/colors";
import { useAuth } from "@/src/hooks/useAuth";

export default function ProtectedLayout() {
  const { token, loading, user, signOut } = useAuth();
  const pathname = usePathname();

  const [menuVisible, setMenuVisible] = useState(false);

  const isProfileScreen = pathname.startsWith("/profile");

  const handleLogout = async () => {
    try {
      await signOut();
      router.replace("/(auth)/sign-in");
    } catch (error) {
      console.log("Error al cerrar sesión:", error);
      router.replace("/(auth)/sign-in");
    }
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={Colors.primary} />
      </View>
    );
  }

  if (!token) {
    return <Redirect href="/(auth)/sign-in" />;
  }

  return (
    <View style={styles.container}>
      {!isProfileScreen ? (
        <View style={styles.menuBar}>
          <Pressable
            style={styles.menuButton}
            onPress={() => setMenuVisible(true)}
          >
            <Text style={styles.menuIcon}>☰</Text>
          </Pressable>
        </View>
      ) : null}

      <View style={styles.stackContainer}>
        <Stack screenOptions={{ headerShown: false }} />
      </View>

      <ProfileSideMenu
        visible={menuVisible}
        onClose={() => setMenuVisible(false)}
        onLogout={handleLogout}
        isAdmin={user?.rol_id === 2}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  stackContainer: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    backgroundColor: Colors.background,
    alignItems: "center",
    justifyContent: "center",
  },
  menuBar: {
    height: 54,
    backgroundColor: Colors.background,
    alignItems: "flex-end",
    justifyContent: "center",
    paddingRight: 18,
    paddingTop: 6,
    zIndex: 10,
  },
  menuButton: {
    width: 42,
    height: 42,
    borderRadius: 21,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "transparent",
  },
  menuIcon: {
    fontSize: 28,
    color: Colors.title,
    fontWeight: "900",
    lineHeight: 32,
  },
});