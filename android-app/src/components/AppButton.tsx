import React from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  ViewStyle,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { Colors } from "@/src/constants/colors";

type Props = {
  title: string;
  onPress: () => void;
  loading?: boolean;
  disabled?: boolean;
  variant?: "primary" | "secondary" | "ghost" | "danger";
  style?: ViewStyle;
};

export default function AppButton({
  title,
  onPress,
  loading = false,
  disabled = false,
  variant = "primary",
  style,
}: Props) {
  const isDisabled = disabled || loading;

  if (variant === "primary") {
    return (
      <Pressable onPress={onPress} disabled={isDisabled} style={[style, isDisabled && styles.disabled]}>
        <LinearGradient
          colors={[Colors.blue, Colors.primary, Colors.lightPurple]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 0 }}
          style={styles.gradientButton}
        >
          {loading ? (
            <ActivityIndicator color={Colors.white} />
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
        <ActivityIndicator color={variant === "ghost" ? Colors.primary : Colors.white} />
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

const styles = StyleSheet.create({
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
    backgroundColor: Colors.softBlue,
  },
  ghost: {
    backgroundColor: "transparent",
  },
  danger: {
    backgroundColor: Colors.danger,
  },
  disabled: {
    opacity: 0.6,
  },
  text: {
    color: Colors.white,
    fontSize: 16,
    fontWeight: "700",
  },
  primaryText: {
    color: Colors.white,
    fontSize: 16,
    fontWeight: "800",
    letterSpacing: 0.2,
  },
  ghostText: {
    color: Colors.primary,
    fontWeight: "700",
  },
});