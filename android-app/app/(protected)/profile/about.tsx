import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";

import Screen from "@/src/components/Screen";
import AppButton from "@/src/components/AppButton";
import { Colors } from "@/src/constants/colors";

export default function AboutScreen() {
  return (
    <Screen>
      <Text style={styles.title}>Sobre LIA</Text>
      <View style={styles.card}>
        <Text style={styles.brand}>LIA</Text>
        <Text style={styles.description}>Tu asistente inteligente para hacer la compra más fácil.</Text>
        <Text style={styles.section}>Equipo</Text>
        <Text style={styles.person}>María del Mar Ávila — Frontend, UI/UX</Text>
        <Text style={styles.person}>Juan del Junco Obregón — Backend, IA y scraping</Text>
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
  },
  brand: { fontSize: 44, fontWeight: "900", textAlign: "center", color: Colors.title },
  description: { textAlign: "center", color: Colors.text, marginTop: 4, marginBottom: 14 },
  section: { fontWeight: "800", color: Colors.title, marginBottom: 6 },
  person: { color: Colors.textMuted, marginBottom: 6 },
});
