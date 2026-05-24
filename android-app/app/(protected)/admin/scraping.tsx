import React, { useEffect, useState } from "react";
import { Alert, Modal, Pressable, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";

import Screen from "@/src/components/Screen";
import AppButton from "@/src/components/AppButton";
import { Colors } from "@/src/constants/colors";
import { useAuth } from "@/src/hooks/useAuth";
import { adminService } from "@/src/services/admin";
import { AdminScrapingOverviewResponse } from "@/src/types/admin";

function getStateLabel(state?: string | null) {
  switch (state) {
    case "ok":
      return "Completado";
    case "parcial":
      return "Completado con avisos";
    case "error":
      return "Error";
    case "en_proceso":
      return "En proceso";
    case "en_cola":
      return "En cola";
    case "cancelado":
      return "Cancelado";
    default:
      return state ?? "-";
  }
}

function getStateBadgeStyle(state?: string | null) {
  switch (state) {
    case "ok":
      return styles.badgeOk;
    case "parcial":
      return styles.badgeWarning;
    case "error":
      return styles.badgeError;
    case "en_proceso":
      return styles.badgeInfo;
    case "en_cola":
    case "cancelado":
      return styles.badgeNeutral;
    default:
      return styles.badgeNeutral;
  }
}

function getStateBadgeTextStyle(state?: string | null) {
  switch (state) {
    case "ok":
      return styles.badgeOkText;
    case "parcial":
      return styles.badgeWarningText;
    case "error":
      return styles.badgeErrorText;
    case "en_proceso":
      return styles.badgeInfoText;
    case "en_cola":
    case "cancelado":
      return styles.badgeNeutralText;
    default:
      return styles.badgeNeutralText;
  }
}

export default function AdminScrapingScreen() {
  const { user } = useAuth();

  const [overview, setOverview] =
    useState<AdminScrapingOverviewResponse | null>(null);

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
      Alert.alert(
        "Error",
        error?.response?.data?.detail || "No se pudo cargar scraping"
      );
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
      Alert.alert(
        "Error",
        error?.response?.data?.detail || "No se pudo ejecutar scraping"
      );
    }
  };

  const cancelScraping = async () => {
    try {
      await adminService.cancelScraping();
      await loadOverview();
    } catch (error: any) {
      Alert.alert(
        "Error",
        error?.response?.data?.detail || "No se pudo cancelar scraping"
      );
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

        <View style={styles.globalStatusRow}>
          <Text style={styles.globalStatusLabel}>Estado general</Text>

          <View
            style={[
              styles.statusBadge,
              getStateBadgeStyle(overview?.ultima_ejecucion_estado),
            ]}
          >
            <Text
              style={[
                styles.statusBadgeText,
                getStateBadgeTextStyle(overview?.ultima_ejecucion_estado),
              ]}
            >
              {getStateLabel(overview?.ultima_ejecucion_estado)}
            </Text>
          </View>
        </View>

        <Text style={styles.lastRunText}>
          Última ejecución: {overview?.ultima_ejecucion_fecha ?? "-"}
        </Text>

        {overview?.fuentes?.map((source) => (
          <View key={source.supermercado} style={styles.sourceCard}>
            <View style={styles.sourceCardHeader}>
              <Text style={styles.sourceName}>{source.supermercado}</Text>

              <View style={[styles.statusBadge, getStateBadgeStyle(source.estado)]}>
                <Text
                  style={[
                    styles.statusBadgeText,
                    getStateBadgeTextStyle(source.estado),
                  ]}
                >
                  {getStateLabel(source.estado)}
                </Text>
              </View>
            </View>

            <Text style={styles.sourceDate}>{source.fecha}</Text>

            <View style={styles.sourceStatsRow}>
              <Text style={styles.sourceStat}>
                Precios: {source.precios_detectados}
              </Text>

              <Text style={styles.sourceStat}>
                Actualizados: {source.productos_actualizados}
              </Text>
            </View>

            {source.warning ? (
              <Text style={styles.warningText}>{source.warning}</Text>
            ) : null}
          </View>
        ))}
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>
          {overview?.en_curso ? "Scraping en curso" : "Scraping Activo"}
        </Text>

        <View style={styles.progressRow}>
          <Text style={styles.progressLabel}>Progreso general:</Text>
          <Text style={styles.progressValue}>
            {overview?.progreso_general ?? 0}%
          </Text>
        </View>

        {overview?.fuentes?.map((source) => (
          <View key={`${source.supermercado}-progress`} style={styles.progressSourceRow}>
            <Text style={styles.progressSourceName}>{source.supermercado}</Text>

            <View style={[styles.statusBadge, getStateBadgeStyle(source.estado)]}>
              <Text
                style={[
                  styles.statusBadgeText,
                  getStateBadgeTextStyle(source.estado),
                ]}
              >
                {getStateLabel(source.estado)}
              </Text>
            </View>
          </View>
        ))}

        <Text style={styles.remaining}>
          Tiempo restante estimado: {overview?.tiempo_restante_segundos ?? 0}s
        </Text>

        {overview?.detalle_error ? (
          <Text
            style={[
              styles.errorText,
              overview.ultima_ejecucion_estado === "parcial" &&
                styles.warningDetailText,
            ]}
          >
            {overview.ultima_ejecucion_estado === "parcial"
              ? `Avisos: ${overview.detalle_error}`
              : `Detalle error: ${overview.detalle_error}`}
          </Text>
        ) : null}

        {overview?.en_curso ? (
          <AppButton
            title="Cancelar Scraping"
            variant="danger"
            onPress={cancelScraping}
            style={{ marginTop: 10 }}
          />
        ) : null}
      </View>

      <AppButton
        title="Forzar Scraping"
        variant="secondary"
        onPress={() => setShowForceModal(true)}
      />

      <Text style={styles.noteTitle}>Nota</Text>
      <Text style={styles.noteText}>
        Esto actualizará los productos y precios desde los supermercados.
      </Text>
      <Text style={styles.noteText}>Puede tardar varios minutos.</Text>

      <Modal
        visible={showForceModal}
        transparent
        animationType="fade"
        onRequestClose={() => setShowForceModal(false)}
      >
        <View style={styles.modalBackdrop}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>¿Ejecutar Scraping?</Text>

            <Text style={styles.modalText}>
              ¿Deseas forzar el scraping de precios?
            </Text>

            <Text style={styles.modalText}>
              Esto puede tardar entre 1 y 3 minutos y consumirá recursos.
            </Text>

            <View style={styles.modalActions}>
              <AppButton
                title="Cancelar"
                variant="ghost"
                onPress={() => setShowForceModal(false)}
                style={{ flex: 1 }}
              />

              <AppButton
                title="Ejecutar"
                variant="danger"
                onPress={forceScraping}
                style={{ flex: 1 }}
              />
            </View>
          </View>
        </View>
      </Modal>
    </Screen>
  );
}

const styles = StyleSheet.create({
  noAccess: {
    color: Colors.text,
    marginTop: 20,
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 8,
  },
  back: {
    fontSize: 28,
    color: Colors.title,
  },
  title: {
    fontSize: 26,
    fontWeight: "800",
    color: Colors.title,
  },
  card: {
    backgroundColor: Colors.card,
    borderWidth: 1,
    borderColor: Colors.textMuted,
    borderRadius: 18,
    padding: 14,
    marginBottom: 12,
  },
  cardTitle: {
    color: Colors.title,
    fontSize: 28,
    fontWeight: "800",
    textAlign: "center",
    marginBottom: 14,
  },
  globalStatusRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
    gap: 12,
  },
  globalStatusLabel: {
    color: Colors.text,
    fontWeight: "800",
    fontSize: 15,
  },
  lastRunText: {
    color: Colors.textMuted,
    textAlign: "center",
    marginBottom: 12,
    fontWeight: "700",
  },
  sourceCard: {
    backgroundColor: Colors.background,
    borderRadius: 14,
    padding: 12,
    borderWidth: 1,
    borderColor: Colors.textMuted,
    marginBottom: 10,
  },
  sourceCardHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 6,
    gap: 12,
  },
  sourceName: {
    flex: 1,
    color: Colors.text,
    fontWeight: "800",
    fontSize: 15,
  },
  sourceDate: {
    color: Colors.textMuted,
    fontSize: 13,
    marginBottom: 4,
  },
  sourceStatsRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 10,
    marginTop: 6,
  },
  sourceStat: {
    color: Colors.text,
    fontSize: 13,
    fontWeight: "700",
  },
  warningText: {
    color: "#92400E",
    marginTop: 8,
    fontSize: 13,
    fontWeight: "700",
    lineHeight: 18,
  },
  progressRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 10,
  },
  progressLabel: {
    color: Colors.text,
    fontWeight: "700",
  },
  progressValue: {
    color: Colors.title,
    fontWeight: "800",
  },
  progressSourceRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
    gap: 10,
  },
  progressSourceName: {
    flex: 1,
    color: Colors.text,
    fontWeight: "700",
  },
  remaining: {
    marginTop: 8,
    color: Colors.text,
    textAlign: "center",
    fontWeight: "700",
  },
  errorText: {
    marginTop: 8,
    color: Colors.danger,
    fontWeight: "600",
    lineHeight: 19,
  },
  warningDetailText: {
    color: "#92400E",
  },
  statusBadge: {
    borderRadius: 999,
    paddingVertical: 5,
    paddingHorizontal: 10,
    alignSelf: "flex-start",
  },
  statusBadgeText: {
    fontSize: 12,
    fontWeight: "900",
  },
  badgeOk: {
    backgroundColor: "#ECFDF5",
  },
  badgeOkText: {
    color: "#166534",
  },
  badgeWarning: {
    backgroundColor: "#FEF3C7",
  },
  badgeWarningText: {
    color: "#92400E",
  },
  badgeError: {
    backgroundColor: "#FEE2E2",
  },
  badgeErrorText: {
    color: "#B91C1C",
  },
  badgeInfo: {
    backgroundColor: "#DBEAFE",
  },
  badgeInfoText: {
    color: "#1D4ED8",
  },
  badgeNeutral: {
    backgroundColor: "#E5E7EB",
  },
  badgeNeutralText: {
    color: "#374151",
  },
  noteTitle: {
    marginTop: 12,
    textAlign: "center",
    color: Colors.title,
    fontSize: 24,
    fontWeight: "800",
  },
  noteText: {
    textAlign: "center",
    color: Colors.text,
    marginTop: 2,
  },
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
  modalTitle: {
    color: Colors.title,
    fontSize: 34,
    fontWeight: "700",
    marginBottom: 12,
  },
  modalText: {
    color: Colors.text,
    marginBottom: 8,
    fontSize: 20,
  },
  modalActions: {
    flexDirection: "row",
    gap: 8,
    marginTop: 8,
  },
});