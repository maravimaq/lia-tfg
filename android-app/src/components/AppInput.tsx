import React from "react";
import {
  StyleSheet,
  Text,
  TextInput,
  TextInputProps,
  View,
} from "react-native";
import { Colors } from "@/src/constants/colors";

type Props = TextInputProps & {
  label?: string;
  error?: string;
};

export default function AppInput({ label, error, ...props }: Props) {
  return (
    <View style={styles.wrapper}>
      {label ? <Text style={styles.label}>{label}</Text> : null}
      <TextInput
        placeholderTextColor={Colors.textMuted}
        style={[styles.input, error ? styles.inputError : null]}
        {...props}
      />
      {error ? <Text style={styles.error}>{error}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    marginBottom: 14,
  },
  label: {
    marginBottom: 6,
    color: Colors.title,
    fontSize: 14,
    fontWeight: "600",
  },
  input: {
    minHeight: 54,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: Colors.border,
    backgroundColor: Colors.surface,
    paddingHorizontal: 16,
    color: Colors.text,
    fontSize: 15,
    shadowColor: "#A9B6E5",
    shadowOpacity: 0.08,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
  },
  inputError: {
    borderColor: Colors.danger,
  },
  error: {
    marginTop: 6,
    color: Colors.danger,
    fontSize: 12,
  },
});