import React, { useMemo } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { AppColors } from "@/src/constants/colors";
import { useAppTheme } from "@/src/hooks/useAppTheme";

export default function Screen({
  children,
  scroll = true,
}: {
  children: React.ReactNode;
  scroll?: boolean;
}) {
  const { colors, isDarkMode } = useAppTheme();
  const styles = useMemo(
    () => createStyles(colors, isDarkMode),
    [colors, isDarkMode]
  );

  const content = (
    <View style={styles.content}>
      <View style={styles.blobTopLeft} />
      <View style={styles.blobTopRight} />
      <View style={styles.blobBottom} />
      {children}
    </View>
  );

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        {scroll ? (
          <ScrollView
            contentContainerStyle={styles.scroll}
            keyboardShouldPersistTaps="handled"
            showsVerticalScrollIndicator={false}
          >
            {content}
          </ScrollView>
        ) : (
          content
        )}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function createStyles(colors: AppColors, isDarkMode: boolean) {
  return StyleSheet.create({
    safe: {
      flex: 1,
      backgroundColor: colors.background,
    },
    flex: {
      flex: 1,
    },
    scroll: {
      flexGrow: 1,
    },
    content: {
      flex: 1,
      paddingHorizontal: 22,
      paddingVertical: 20,
      backgroundColor: colors.background,
      overflow: "hidden",
    },
    blobTopLeft: {
      position: "absolute",
      top: -40,
      left: -40,
      width: 180,
      height: 180,
      borderRadius: 90,
      backgroundColor: colors.cyan,
      opacity: isDarkMode ? 0.09 : 0.18,
    },
    blobTopRight: {
      position: "absolute",
      top: 40,
      right: -60,
      width: 180,
      height: 180,
      borderRadius: 90,
      backgroundColor: colors.lightPurple,
      opacity: isDarkMode ? 0.1 : 0.15,
    },
    blobBottom: {
      position: "absolute",
      bottom: -80,
      left: 40,
      width: 240,
      height: 240,
      borderRadius: 120,
      backgroundColor: colors.softBlue,
      opacity: isDarkMode ? 0.14 : 0.18,
    },
  });
}
