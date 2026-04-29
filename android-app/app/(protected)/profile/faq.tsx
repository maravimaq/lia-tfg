import React, { useMemo, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";

import Screen from "@/src/components/Screen";
import AppInput from "@/src/components/AppInput";
import AppButton from "@/src/components/AppButton";
import { Colors } from "@/src/constants/colors";

const FAQ_ITEMS = [
  {
    q: "¿Cómo puedo compartir mi lista de la compra?",
    a: "Desde una lista, pulsa Compartir y selecciona el canal.",
  },
  {
    q: "¿Cómo conecto el bot de WhatsApp o Telegram?",
    a: "Abre Configuración Bot Externo y pega tu token.",
  },
  {
    q: "¿Cómo puedo ver mis analíticas?",
    a: "Desde tu perfil entra en la pestaña Analíticas.",
  },
];

export default function FaqScreen() {
  const [query, setQuery] = useState("");

  const filtered = useMemo(
    () =>
      FAQ_ITEMS.filter(
        (item) =>
          item.q.toLowerCase().includes(query.toLowerCase()) ||
          item.a.toLowerCase().includes(query.toLowerCase())
      ),
    [query]
  );

  return (
    <Screen>
      <Text style={styles.title}>Preguntas Frecuentes</Text>
      <AppInput placeholder="Escribe tu pregunta" value={query} onChangeText={setQuery} />

      <View style={styles.list}>
        {filtered.map((item) => (
          <View key={item.q} style={styles.item}>
            <Text style={styles.q}>{item.q}</Text>
            <Text style={styles.a}>{item.a}</Text>
          </View>
        ))}
      </View>

      <AppButton title="Volver" variant="ghost" onPress={() => router.back()} style={{ marginTop: 12 }} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 24, fontWeight: "800", color: Colors.title, marginBottom: 16 },
  list: { gap: 10 },
  item: {
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 14,
    padding: 12,
    backgroundColor: Colors.surface,
  },
  q: { fontWeight: "700", color: Colors.text },
  a: { color: Colors.textMuted, marginTop: 4 },
});
