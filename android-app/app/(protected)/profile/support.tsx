import React from "react";
import { Linking, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";

import Screen from "@/src/components/Screen";
import AppButton from "@/src/components/AppButton";
import { Colors } from "@/src/constants/colors";

export default function SupportScreen() {
  return (
    <Screen>
      <Text style={styles.title}>Ayuda y Soporte</Text>
      <View style={styles.card}>
        <Text style={styles.label}>Soporte Técnico</Text>
        <Text style={styles.link} onPress={() => Linking.openURL("tel:+34123456789")}>+34 123 45 67 89</Text>

        <Text style={styles.label}>Enviar correo</Text>
        <Text style={styles.link} onPress={() => Linking.openURL("mailto:soporte@liaapp.com")}>soporte@liaapp.com</Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.label}>Problemas frecuentes</Text>
        <Text style={styles.item}>• No se guardan mis listas.</Text>
        <Text style={styles.item}>• Error al sincronizar con el bot.</Text>
        <Text style={styles.item}>• Fallo al iniciar sesión.</Text>
      </View>

      <AppButton title="Volver" variant="ghost" onPress={() => router.back()} style={{ marginTop: 12 }} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 24, fontWeight: "800", color: Colors.title, marginBottom: 16 },
  card: {
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 18,
    padding: 16,
    backgroundColor: Colors.surface,
    marginBottom: 12,
  },
  label: { fontWeight: "800", color: Colors.title, marginBottom: 6 },
  link: { color: Colors.primary, marginBottom: 10 },
  item: { color: Colors.textMuted, marginBottom: 4 },
});
