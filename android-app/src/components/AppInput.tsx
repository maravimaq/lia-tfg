import React, { useMemo } from "react";
import {
  StyleSheet,
  Text,
  TextInput,
  TextInputProps,
  View,
} from "react-native";

import { AppColors } from "@/src/constants/colors";
import { useAppTheme } from "@/src/hooks/useAppTheme";

type Props = TextInputProps & {
  label?: string;
  error?: string;
};

export default function AppInput({ label, error, style, ...props }: Props) {
  const { colors, isDarkMode } = useAppTheme();
  const styles = useMemo(
    () => createStyles(colors, isDarkMode),
    [colors, isDarkMode]
  );

  return (
    <View style={styles.wrapper}>
      {label ? <Text style={styles.label}>{label}</Text> : null}
      <TextInput
        placeholderTextColor={colors.textMuted}
        style={[styles.input, error ? styles.inputError : null, style]}
        {...props}
      />
      {error ? <Text style={styles.error}>{error}</Text> : null}
    </View>
  );
}

function createStyles(colors: AppColors, isDarkMode: boolean) {
  return StyleSheet.create({
    wrapper: {
      marginBottom: 14,
    },
    label: {
      marginBottom: 6,
      color: colors.title,
      fontSize: 14,
      fontWeight: "600",
    },
    input: {
      minHeight: 54,
      borderRadius: 16,
      borderWidth: 1,
      borderColor: colors.border,
      backgroundColor: colors.surface,
      paddingHorizontal: 16,
      color: colors.text,
      fontSize: 15,
      shadowColor: isDarkMode ? "#000000" : "#A9B6E5",
      shadowOpacity: isDarkMode ? 0.18 : 0.08,
      shadowRadius: 10,
      shadowOffset: { width: 0, height: 4 },
    },
    inputError: {
      borderColor: colors.danger,
    },
    error: {
      marginTop: 6,
      color: colors.danger,
      fontSize: 12,
    },
  });
}
