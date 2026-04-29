import React, { useEffect, useState } from "react";
import { Alert, Modal, Pressable, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";

import Screen from "@/src/components/Screen";
import AppButton from "@/src/components/AppButton";
import { Colors } from "@/src/constants/colors";
import { useAuth } from "@/src/hooks/useAuth";
import { adminService } from "@/src/services/admin";
import { AdminScrapingOverviewResponse } from "@/src/types/admin";

export default function AdminScrapingScreen() {
  const { user } = useAuth();
  const [overview, setOverview] = useState<AdminScrapingOverviewResponse | null>(null);
  const [showForceModal, setShowForceModal] = useState(false);

  const handleBack = () => {
    if (router.canGoBack()) {
      router.back();
      return;
    }

    router.replace("/(protected)/admin");
  };

  const loadOverview = async () => {
    try {
      const data = await adminService.getScrapingOverview();
      setOverview(data);
    } catch (error: any) {
      Alert.alert("Error", error?.response?.data?.detail || "No se pudo cargar scraping");
    }
  };

  useEffect(() => {
    if (user?.rol_id !== 2) return;
    loadOverview();
  }, [user?.rol_id]);

  useEffect(() => {
    if (user?.rol_id !== 2) return;

    const intervalId = setInterval(() => {
      loadOverview();
    }, 5000);

    return () => clearInterval(intervalId);
  }, [user?.rol_id]);

  const forceScraping = async () => {
    try {
      await adminService.forceScraping();
      setShowForceModal(false);
      await loadOverview();
    } catch (error: any) {
      Alert.alert("Error", error?.response?.data?.detail || "No se pudo ejecutar scraping");
    }
  };

  const cancelScraping = async () => {
    try {
      await adminService.cancelScraping();
      await loadOverview();
    } catch (error: any) {
      Alert.alert("Error", error?.response?.data?.detail || "No se pudo cancelar scraping");
    }
  };

  if (user?.rol_id !== 2) {
    return (
      <Screen>
        <Text style={styles.noAccess}>No tienes permisos para esta sección.</Text>
      </Screen>
    );
  }

  return (
    <Screen>
      <View style={styles.headerRow}>
        <Pressable onPress={handleBack}>
          <Text style={styles.back}>←</Text>
        </Pressable>
        <Text style={styles.title}>Gestionar Scraping</Text>
        <View style={{ width: 16 }} />
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Última ejecución</Text>
        {overview?.fuentes?.map((source) => (
          <View key={source.supermercado} style={styles.sourceRow}>
            <Text style={styles.sourceName}>{source.supermercado}:</Text>
            <Text style={styles.sourceState}>{source.estado}</Text>
            <Text style={styles.sourceDate}>{source.fecha}</Text>
          </View>
        ))}
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>{overview?.en_curso ? "Scraping en curso" : "Scraping Activo"}</Text>
        <View style={styles.progressRow}>
          <Text style={styles.progressLabel}>Progreso general:</Text>
          <Text style={styles.progressValue}>{overview?.progreso_general ?? 0}%</Text>
        </View>

        {overview?.fuentes?.map((source) => (
          <View key={`${source.supermercado}-progress`} style={styles.sourceRow}>
            <Text style={styles.sourceName}>{source.supermercado}:</Text>
            <Text style={styles.sourceDate}>{source.estado}</Text>
          </View>
        ))}

        <Text style={styles.remaining}>Tiempo restante estimado: {overview?.tiempo_restante_segundos ?? 0}s</Text>
        {overview?.detalle_error ? (
          <Text style={styles.errorText}>Detalle error: {overview.detalle_error}</Text>
        ) : null}

        {overview?.en_curso ? (
          <AppButton title="Cancelar Scraping" variant="danger" onPress={cancelScraping} style={{ marginTop: 10 }} />
        ) : null}
      </View>

      <AppButton title="Forzar Scraping" variant="secondary" onPress={() => setShowForceModal(true)} />

      <Text style={styles.noteTitle}>Nota</Text>
      <Text style={styles.noteText}>Esto actualizará los productos y precios desde los supermercados.</Text>
      <Text style={styles.noteText}>Puede tardar varios minutos.</Text>

      <Modal visible={showForceModal} transparent animationType="fade" onRequestClose={() => setShowForceModal(false)}>
        <View style={styles.modalBackdrop}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>¿Ejecutar Scraping?</Text>
            <Text style={styles.modalText}>¿Deseas forzar el scraping de precios?</Text>
            <Text style={styles.modalText}>Esto puede tardar entre 1 y 3 minutos y consumirá recursos.</Text>

            <View style={styles.modalActions}>
              <AppButton title="Cancelar" variant="ghost" onPress={() => setShowForceModal(false)} style={{ flex: 1 }} />
              <AppButton title="Ejecutar" variant="danger" onPress={forceScraping} style={{ flex: 1 }} />
            </View>
          </View>
        </View>
      </Modal>
    </Screen>
  );
}

const styles = StyleSheet.create({
  noAccess: { color: Colors.text, marginTop: 20 },
  headerRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: 8 },
  back: { fontSize: 28, color: Colors.title },
  title: { fontSize: 26, fontWeight: "800", color: Colors.title },
  card: {
    backgroundColor: Colors.card,
    borderWidth: 1,
    borderColor: Colors.textMuted,
    borderRadius: 18,
    padding: 14,
    marginBottom: 12,
  },
  cardTitle: { color: Colors.title, fontSize: 30, fontWeight: "800", textAlign: "center", marginBottom: 10 },
  sourceRow: { flexDirection: "row", marginBottom: 6 },
  sourceName: { flex: 1.3, color: Colors.text },
  sourceState: { flex: 1, color: Colors.text },
  sourceDate: { flex: 1.1, color: Colors.text },
  progressRow: { flexDirection: "row", justifyContent: "space-between", marginBottom: 8 },
  progressLabel: { color: Colors.text, fontWeight: "700" },
  progressValue: { color: Colors.title, fontWeight: "800" },
  remaining: { marginTop: 8, color: Colors.text, textAlign: "center", fontWeight: "700" },
  errorText: { marginTop: 8, color: Colors.danger, fontWeight: "600" },
  noteTitle: { marginTop: 12, textAlign: "center", color: Colors.title, fontSize: 24, fontWeight: "800" },
  noteText: { textAlign: "center", color: Colors.text, marginTop: 2 },
  modalBackdrop: {
    flex: 1,
    justifyContent: "center",
    backgroundColor: "rgba(0,0,0,0.35)",
    paddingHorizontal: 18,
  },
  modalCard: {
    backgroundColor: "#d8d8de",
    borderRadius: 24,
    borderWidth: 1,
    borderColor: Colors.textMuted,
    padding: 16,
  },
  modalTitle: { color: Colors.title, fontSize: 36, fontWeight: "700", marginBottom: 12 },
  modalText: { color: Colors.text, marginBottom: 8, fontSize: 20 },
  modalActions: { flexDirection: "row", gap: 8, marginTop: 8 },
});
