import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Redirect, Stack, router, usePathname } from "expo-router";
import { StatusBar } from "expo-status-bar";

import ProfileSideMenu from "@/src/components/ProfileSideMenu";
import { AppColors } from "@/src/constants/colors";
import { useAuth } from "@/src/hooks/useAuth";
import { useAppTheme } from "@/src/hooks/useAppTheme";

export default function ProtectedLayout() {
  const { token, loading, user, signOut } = useAuth();
  const { colors, isDarkMode, refreshThemeFromPreferences, setDarkMode } = useAppTheme();
  const pathname = usePathname();

  const [menuVisible, setMenuVisible] = useState(false);
  const styles = createStyles(colors);

  const isProfileScreen = pathname.startsWith("/profile");

  useEffect(() => {
    if (token) {
      refreshThemeFromPreferences().catch(() => undefined);
      return;
    }

    setDarkMode(false).catch(() => undefined);
  }, [token, refreshThemeFromPreferences, setDarkMode]);

  const handleLogout = async () => {
    try {
      await signOut();
      await setDarkMode(false);
      router.replace("/(auth)/sign-in");
    } catch (error) {
      console.log("Error al cerrar sesión:", error);
      router.replace("/(auth)/sign-in");
    }
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <StatusBar style={isDarkMode ? "light" : "dark"} />
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  if (!token) {
    return <Redirect href="/(auth)/sign-in" />;
  }

  return (
    <View style={styles.container}>
      <StatusBar style={isDarkMode ? "light" : "dark"} />

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

function createStyles(colors: AppColors) {
  return StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: colors.background,
    },
    stackContainer: {
      flex: 1,
    },
    loadingContainer: {
      flex: 1,
      backgroundColor: colors.background,
      alignItems: "center",
      justifyContent: "center",
    },
    menuBar: {
      height: 54,
      backgroundColor: colors.background,
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
      color: colors.title,
      fontWeight: "900",
      lineHeight: 32,
    },
  });
}
