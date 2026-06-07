import React, { useMemo } from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleProp,
  StyleSheet,
  Text,
  ViewStyle,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";

import { AppColors } from "@/src/constants/colors";
import { useAppTheme } from "@/src/hooks/useAppTheme";

type Props = {
  title: string;
  onPress: () => void;
  loading?: boolean;
  disabled?: boolean;
  variant?: "primary" | "secondary" | "ghost" | "danger";
  style?: StyleProp<ViewStyle>;
};

export default function AppButton({
  title,
  onPress,
  loading = false,
  disabled = false,
  variant = "primary",
  style,
}: Props) {
  const { colors, isDarkMode } = useAppTheme();
  const styles = useMemo(
    () => createStyles(colors, isDarkMode),
    [colors, isDarkMode]
  );
  const isDisabled = disabled || loading;

  if (variant === "primary") {
    return (
      <Pressable onPress={onPress} disabled={isDisabled} style={[style, isDisabled && styles.disabled]}>
        <LinearGradient
          colors={[colors.blue, colors.primary, colors.lightPurple]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 0 }}
          style={styles.gradientButton}
        >
          {loading ? (
            <ActivityIndicator color={colors.white} />
          ) : (
            <Text style={styles.primaryText}>{title}</Text>
          )}
        </LinearGradient>
      </Pressable>
    );
  }

  return (
    <Pressable
      onPress={onPress}
      disabled={isDisabled}
      style={[
        styles.base,
        variant === "secondary" && styles.secondary,
        variant === "ghost" && styles.ghost,
        variant === "danger" && styles.danger,
        style,
        isDisabled && styles.disabled,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={variant === "ghost" ? colors.primary : colors.white} />
      ) : (
        <Text
          style={[
            styles.text,
            variant === "ghost" && styles.ghostText,
          ]}
        >
          {title}
        </Text>
      )}
    </Pressable>
  );
}

function createStyles(colors: AppColors, isDarkMode: boolean) {
  return StyleSheet.create({
    base: {
      minHeight: 54,
      borderRadius: 18,
      alignItems: "center",
      justifyContent: "center",
      paddingHorizontal: 16,
    },
    gradientButton: {
      minHeight: 54,
      borderRadius: 18,
      alignItems: "center",
      justifyContent: "center",
      paddingHorizontal: 16,
    },
    secondary: {
      backgroundColor: isDarkMode ? colors.card : colors.softBlue,
      borderWidth: isDarkMode ? 1 : 0,
      borderColor: colors.border,
    },
    ghost: {
      backgroundColor: "transparent",
    },
    danger: {
      backgroundColor: colors.danger,
    },
    disabled: {
      opacity: 0.6,
    },
    text: {
      color: colors.white,
      fontSize: 16,
      fontWeight: "700",
    },
    primaryText: {
      color: colors.white,
      fontSize: 16,
      fontWeight: "800",
      letterSpacing: 0.2,
    },
    ghostText: {
      color: colors.primary,
      fontWeight: "700",
    },
  });
}
