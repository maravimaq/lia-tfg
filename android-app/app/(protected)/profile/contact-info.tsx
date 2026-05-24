import React from "react";
import { Linking, Pressable, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";

import Screen from "@/src/components/Screen";
import AppButton from "@/src/components/AppButton";
import { Colors } from "@/src/constants/colors";

export default function ContactInfoScreen() {
  return (
    <Screen>
      <Text style={styles.title}>Información de Contacto</Text>

      <View style={styles.card}>
        <Text style={styles.label}>Dirección</Text>
        <Text style={styles.value}>Av. Reina Mercedes, s/n, 41012 Sevilla</Text>

        <Text style={styles.label}>Teléfono</Text>
        <Pressable onPress={() => Linking.openURL("tel:+34600123456")}>
          <Text style={styles.link}>+34 600 123 456</Text>
        </Pressable>

        <Text style={styles.label}>Email</Text>
        <Pressable onPress={() => Linking.openURL("mailto:contacto@liaapp.com")}>
          <Text style={styles.link}>contacto@liaapp.com</Text>
        </Pressable>

        <Text style={styles.label}>Web</Text>
        <Pressable onPress={() => Linking.openURL("https://liaapp.com")}>
          <Text style={styles.link}>www.liaapp.com</Text>
        </Pressable>
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
  label: { fontWeight: "700", color: Colors.title, marginTop: 10 },
  value: { color: Colors.text },
  link: { color: Colors.primary, marginTop: 4 },
});
