import React, { useEffect, useState } from "react";
import { Alert, Pressable, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";

import Screen from "@/src/components/Screen";
import AppButton from "@/src/components/AppButton";
import ProfileSideMenu from "@/src/components/ProfileSideMenu";
import { Colors } from "@/src/constants/colors";
import { useAuth } from "@/src/hooks/useAuth";
import { adminService } from "@/src/services/admin";
import { AdminDashboardResponse, AdminScrapingOverviewResponse } from "@/src/types/admin";

function initials(name?: string) {
  if (!name) return "AD";
  return name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export default function AdminDashboardScreen() {
  const { user, signOut } = useAuth();
  const [dashboard, setDashboard] = useState<AdminDashboardResponse | null>(null);
  const [scraping, setScraping] = useState<AdminScrapingOverviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [menuVisible, setMenuVisible] = useState(false);

  const handleLogout = async () => {
    try {
      await signOut();
    } finally {
      router.replace("/(auth)/sign-in");
    }
  };

  useEffect(() => {
    if (user?.rol_id !== 2) return;

    const load = async () => {
      try {
        setLoading(true);
        const [dashboardData, scrapingData] = await Promise.all([
          adminService.getDashboard(),
          adminService.getScrapingOverview(),
        ]);
        setDashboard(dashboardData);
        setScraping(scrapingData);
      } catch (error: any) {
        Alert.alert("Error", error?.response?.data?.detail || "No se pudo cargar el dashboard admin");
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [user?.rol_id]);

  useEffect(() => {
    if (user?.rol_id !== 2) return;
    const intervalId = setInterval(async () => {
      try {
        const scrapingData = await adminService.getScrapingOverview();
        setScraping(scrapingData);
      } catch {
        // Evitamos alertas en bucle durante el polling.
      }
    }, 5000);
    return () => clearInterval(intervalId);
  }, [user?.rol_id]);

  if (user?.rol_id !== 2) {
    return (
      <Screen>
        <View style={styles.notAllowedCard}>
          <Text style={styles.notAllowedTitle}>Acceso restringido</Text>
          <Text style={styles.notAllowedText}>Solo administradores pueden entrar al panel.</Text>
          <AppButton title="Volver" onPress={() => router.replace("/(protected)/profile")} />
        </View>
      </Screen>
    );
  }

  return (
    <Screen>
      <View style={styles.topBar}>
        <View />
        <Pressable onPress={() => setMenuVisible(true)}>
          <Text style={styles.menuIcon}>☰</Text>
        </Pressable>
      </View>

      <View style={styles.profileHeader}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>{initials(user?.nombre_completo)}</Text>
        </View>
        <Text style={styles.username}>@{user?.nombre_usuario}</Text>
      </View>

      <View style={styles.titleWrap}>
        <Text style={styles.title}>Panel de Administración</Text>
      </View>

      <View style={styles.statsRow}>
        <View style={styles.statBox}>
          <Text style={styles.statLabel}>Usuarios Registrados</Text>
          <Text style={styles.statValue}>{dashboard?.total_usuarios ?? 0}</Text>
        </View>
        <View style={styles.statBox}>
          <Text style={styles.statLabel}>Listas Creadas</Text>
          <Text style={styles.statValue}>{dashboard?.total_listas ?? 0}</Text>
        </View>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Último scraping ejecutado</Text>
        <View style={styles.rowBetween}>
          <Text style={styles.label}>Fecha:</Text>
          <Text style={styles.value}>{scraping?.ultima_ejecucion_fecha || "-"}</Text>
        </View>
        <View style={styles.rowBetween}>
          <Text style={styles.label}>Estado:</Text>
          <Text style={styles.value}>{scraping?.ultima_ejecucion_estado || "-"}</Text>
        </View>
        <View style={styles.rowBetween}>
          <Text style={styles.label}>Progreso:</Text>
          <Text style={styles.value}>{scraping?.progreso_general ?? 0}%</Text>
        </View>
        <View style={styles.rowBetween}>
          <Text style={styles.label}>Tiempo restante:</Text>
          <Text style={styles.value}>{scraping?.tiempo_restante_segundos ?? 0}s</Text>
        </View>

        {scraping?.detalle_error ? (
          <Text style={styles.globalErrorText}>Detalle error: {scraping.detalle_error}</Text>
        ) : null}

        <View style={styles.sourceHeader}>
          <Text style={[styles.sourceHeaderText, styles.sourceColStore]}>Supermercado</Text>
          <Text style={[styles.sourceHeaderText, styles.sourceColState]}>Estado</Text>
          <Text style={[styles.sourceHeaderText, styles.sourceColCount]}>Precios</Text>
          <Text style={[styles.sourceHeaderText, styles.sourceColCount]}>Actualizados</Text>
        </View>

        {scraping?.fuentes?.length ? (
          scraping.fuentes.map((source) => (
            <View key={`${source.supermercado}-dashboard`} style={styles.sourceRow}>
              <View style={styles.sourceMainRow}>
                <Text style={[styles.sourceCell, styles.sourceColStore]}>{source.supermercado}</Text>
                <Text style={[styles.sourceCell, styles.sourceColState]}>{source.estado}</Text>
                <Text style={[styles.sourceCell, styles.sourceColCount]}>{source.precios_detectados}</Text>
                <Text style={[styles.sourceCell, styles.sourceColCount]}>{source.productos_actualizados}</Text>
              </View>

              {source.warning ? (
                <Text style={styles.sourceWarning}>⚠ {source.warning}</Text>
              ) : null}
              {source.detalle_error ? (
                <Text style={styles.sourceError}>✖ {source.detalle_error}</Text>
              ) : null}
              <Text style={styles.sourceDate}>Fecha fuente: {source.fecha}</Text>
            </View>
          ))
        ) : (
          <Text style={styles.sourceDate}>Sin datos de fuentes todavía.</Text>
        )}
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Actividad Reciente</Text>
        {dashboard?.actividad_reciente?.length ? (
          dashboard.actividad_reciente.map((item, index) => (
            <Text key={`${item}-${index}`} style={styles.activityLine}>{item}</Text>
          ))
        ) : (
          <Text style={styles.activityLine}>Sin actividad reciente.</Text>
        )}
      </View>

      {loading ? <Text style={styles.loadingText}>Cargando...</Text> : null}

      <View style={styles.actionsRow}>
        <AppButton
          title="Gestionar Usuarios"
          variant="secondary"
          onPress={() => router.push("/(protected)/admin/users")}
          style={styles.actionButton}
        />
        <AppButton
          title="Gestionar Scraping"
          variant="secondary"
          onPress={() => router.push("/(protected)/admin/scraping")}
          style={styles.actionButton}
        />
      </View>

      <ProfileSideMenu
        visible={menuVisible}
        onClose={() => setMenuVisible(false)}
        onLogout={handleLogout}
        isAdmin={user?.rol_id === 2}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  topBar: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 8,
  },
  menuIcon: {
    fontSize: 24,
    color: Colors.title,
    fontWeight: "800",
  },
  profileHeader: { alignItems: "center", marginBottom: 8 },
  avatar: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: Colors.softBlue,
    justifyContent: "center",
    alignItems: "center",
  },
  avatarText: { fontSize: 28, color: Colors.title, fontWeight: "800" },
  username: { marginTop: 8, color: Colors.textMuted, fontSize: 16 },
  titleWrap: {
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: Colors.border,
    paddingVertical: 8,
    marginBottom: 12,
  },
  title: { textAlign: "center", fontSize: 32, fontWeight: "800", color: Colors.title },
  statsRow: { flexDirection: "row", gap: 8, marginBottom: 12 },
  statBox: {
    flex: 1,
    backgroundColor: Colors.surface,
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 12,
    padding: 12,
    alignItems: "center",
  },
  statLabel: { fontWeight: "700", color: Colors.text, textAlign: "center" },
  statValue: { marginTop: 8, fontSize: 36, fontWeight: "800", color: Colors.black },
  card: {
    backgroundColor: Colors.card,
    borderWidth: 1,
    borderColor: Colors.textMuted,
    borderRadius: 18,
    padding: 14,
    marginBottom: 12,
  },
  cardTitle: { fontSize: 32, color: Colors.title, fontWeight: "800", marginBottom: 8, textAlign: "center" },
  rowBetween: { flexDirection: "row", justifyContent: "space-between", marginBottom: 6 },
  label: { color: Colors.text, fontWeight: "600" },
  value: { color: Colors.text },
  globalErrorText: { color: Colors.danger, marginTop: 8, marginBottom: 8, fontWeight: "600" },
  sourceHeader: {
    flexDirection: "row",
    marginTop: 8,
    marginBottom: 6,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
    paddingBottom: 4,
  },
  sourceHeaderText: { color: Colors.title, fontWeight: "800", fontSize: 12 },
  sourceRow: {
    marginBottom: 8,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
    paddingBottom: 8,
  },
  sourceMainRow: { flexDirection: "row" },
  sourceCell: { color: Colors.text, fontSize: 12 },
  sourceColStore: { flex: 1.2 },
  sourceColState: { flex: 1 },
  sourceColCount: { flex: 0.8, textAlign: "right" },
  sourceWarning: { color: "#9a6b00", marginTop: 4, fontSize: 12 },
  sourceError: { color: Colors.danger, marginTop: 2, fontSize: 12 },
  sourceDate: { color: Colors.textMuted, marginTop: 2, fontSize: 12 },
  activityLine: { color: Colors.text, marginBottom: 4 },
  loadingText: { color: Colors.textMuted, textAlign: "center", marginBottom: 8 },
  actionsRow: { flexDirection: "row", gap: 8 },
  actionButton: { flex: 1 },
  notAllowedCard: {
    marginTop: 48,
    backgroundColor: Colors.surface,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: Colors.border,
    padding: 18,
  },
  notAllowedTitle: { color: Colors.title, fontSize: 24, fontWeight: "800", marginBottom: 6 },
  notAllowedText: { color: Colors.text, marginBottom: 12 },
});