import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Linking,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { router } from "expo-router";

import AppButton from "@/src/components/AppButton";
import Screen from "@/src/components/Screen";
import { AppColors } from "@/src/constants/colors";
import { useAppTheme } from "@/src/hooks/useAppTheme";
import { externalBotService } from "@/src/services/externalBot";
import {
  ExternalBotBindingStatusResponse,
  ExternalBotLinkCodeResponse,
  ExternalBotMessageResponse,
  TelegramBotInfoResponse,
} from "@/src/types/externalBot";

export default function BotConfigScreen() {
  const { colors, isDarkMode } = useAppTheme();
  const styles = useMemo(() => createStyles(colors, isDarkMode), [colors, isDarkMode]);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [creatingCode, setCreatingCode] = useState(false);
  const [botInfo, setBotInfo] = useState<TelegramBotInfoResponse | null>(null);
  const [bindingStatus, setBindingStatus] = useState<ExternalBotBindingStatusResponse | null>(null);
  const [linkCode, setLinkCode] = useState<ExternalBotLinkCodeResponse | null>(null);
  const [messages, setMessages] = useState<ExternalBotMessageResponse[]>([]);

  const loadData = useCallback(async () => {
    const [info, status, botMessages] = await Promise.all([
      externalBotService.getTelegramBotInfo(),
      externalBotService.getBindingStatus("telegram"),
      externalBotService.getMessages("telegram", 10),
    ]);

    setBotInfo(info);
    setBindingStatus(status);
    setMessages(botMessages);
  }, []);

  useEffect(() => {
    const init = async () => {
      try {
        await loadData();
      } catch (error: any) {
        Alert.alert("Error", error?.response?.data?.detail || "No se pudo cargar el bot externo");
      } finally {
        setLoading(false);
      }
    };

    init();
  }, [loadData]);

  const onRefresh = async () => {
    try {
      setRefreshing(true);
      await loadData();
    } catch (error: any) {
      Alert.alert("Error", error?.response?.data?.detail || "No se pudo actualizar el estado");
    } finally {
      setRefreshing(false);
    }
  };

  const generateCode = async () => {
    try {
      setCreatingCode(true);
      const code = await externalBotService.createLinkCode("telegram");
      setLinkCode(code);
      await loadData();
    } catch (error: any) {
      Alert.alert("Error", error?.response?.data?.detail || "No se pudo generar el código");
    } finally {
      setCreatingCode(false);
    }
  };

  const openTelegram = async () => {
    if (!botInfo?.username) {
      Alert.alert("Bot no disponible", "No se ha podido obtener el usuario del bot de Telegram.");
      return;
    }

    const url = `https://t.me/${botInfo.username}`;
    const canOpen = await Linking.canOpenURL(url);
    if (!canOpen) {
      Alert.alert("No se pudo abrir Telegram", `Abre Telegram y busca @${botInfo.username}`);
      return;
    }

    await Linking.openURL(url);
  };

  const expirationLabel = linkCode
    ? new Date(linkCode.fecha_expiracion).toLocaleString("es-ES", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : null;

  if (loading) {
    return (
      <Screen>
        <View style={styles.centerBox}>
          <ActivityIndicator color={colors.primary} />
          <Text style={styles.mutedText}>Cargando bot externo...</Text>
        </View>
      </Screen>
    );
  }

  return (
    <Screen>
      <View style={styles.headerRow}>
        <Pressable onPress={() => router.back()} style={styles.backButton}>
          <Text style={styles.backText}>← Volver</Text>
        </Pressable>
      </View>

      <View style={styles.header}>
        <Text style={styles.title}>Bot Externo</Text>
        <Text style={styles.subtitle}>Conecta LIA con un bot real de Telegram.</Text>
      </View>

      <View style={styles.card}>
        <View style={styles.rowBetween}>
          <View>
            <Text style={styles.sectionTitle}>Estado de Telegram</Text>
            <Text style={styles.mutedText}>
              {botInfo?.configured
                ? `Bot configurado${botInfo.username ? `: @${botInfo.username}` : ""}`
                : "Falta configurar TELEGRAM_BOT_TOKEN en el backend"}
            </Text>
          </View>
          <View style={[styles.badge, botInfo?.configured ? styles.badgeOk : styles.badgeWarn]}>
            <Text style={styles.badgeText}>{botInfo?.configured ? "Activo" : "Sin token"}</Text>
          </View>
        </View>

        <View style={styles.separator} />

        <View style={styles.rowBetween}>
          <View style={styles.flexOne}>
            <Text style={styles.sectionTitle}>Vinculación de cuenta</Text>
            <Text style={styles.mutedText}>
              {bindingStatus?.vinculado
                ? `Vinculado con Telegram ID ${bindingStatus.external_user_id}`
                : "Tu usuario de LIA aún no está vinculado con Telegram."}
            </Text>
          </View>
          <View style={[styles.badge, bindingStatus?.vinculado ? styles.badgeOk : styles.badgeNeutral]}>
            <Text style={styles.badgeText}>{bindingStatus?.vinculado ? "Vinculado" : "Pendiente"}</Text>
          </View>
        </View>
      </View>

      <View style={styles.card}>
        <Text style={styles.sectionTitle}>1. Genera un código</Text>
        <Text style={styles.mutedText}>
          El código dura unos minutos y sirve para enlazar tu usuario de LIA con tu chat de Telegram.
        </Text>

        <AppButton
          title="Generar código de vinculación"
          onPress={generateCode}
          loading={creatingCode}
          disabled={!botInfo?.configured}
          style={styles.buttonTop}
        />

        {linkCode && (
          <View style={styles.codeBox}>
            <Text style={styles.codeLabel}>Mensaje que debes enviar al bot:</Text>
            <Text selectable style={styles.codeText}>{`/start ${linkCode.codigo}`}</Text>
            <Text style={styles.mutedText}>Caduca: {expirationLabel}</Text>
          </View>
        )}
      </View>

      <View style={styles.card}>
        <Text style={styles.sectionTitle}>2. Abre Telegram</Text>
        <Text style={styles.mutedText}>
          Busca el bot, pulsa iniciar y envía el mensaje con el código. Después vuelve aquí y refresca.
        </Text>

        <AppButton
          title={botInfo?.username ? `Abrir @${botInfo.username}` : "Abrir Telegram"}
          onPress={openTelegram}
          variant="secondary"
          disabled={!botInfo?.configured}
          style={styles.buttonTop}
        />
      </View>

      <AppButton
        title="Actualizar estado"
        onPress={onRefresh}
        loading={refreshing}
        variant="ghost"
        style={{ marginBottom: 12 }}
      />

      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Comandos disponibles</Text>
        <Text style={styles.command}>crear lista Compra semanal</Text>
        <Text style={styles.command}>añadir leche</Text>
        <Text style={styles.command}>comparar arroz</Text>
        <Text style={styles.command}>mis listas</Text>
        <Text style={styles.command}>cancelar</Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Últimos mensajes</Text>
        {messages.length === 0 ? (
          <Text style={styles.mutedText}>Todavía no hay mensajes guardados.</Text>
        ) : (
          messages.map((message) => (
            <View key={message.id_mensaje_bot} style={styles.messageItem}>
              <Text style={styles.messageDirection}>
                {message.direccion === "incoming" ? "Usuario" : "LIA"}
              </Text>
              <Text style={styles.messageText}>{message.texto}</Text>
            </View>
          ))
        )}
      </View>
    </Screen>
  );
}

function createStyles(colors: AppColors, isDarkMode: boolean) {
  return StyleSheet.create({
    headerRow: {
      marginBottom: 8,
    },
    backButton: {
      alignSelf: "flex-start",
      paddingVertical: 8,
    },
    backText: {
      color: colors.title,
      fontWeight: "800",
    },
    header: {
      marginBottom: 18,
    },
    title: {
      color: colors.title,
      fontSize: 28,
      fontWeight: "900",
    },
    subtitle: {
      color: colors.textMuted,
      marginTop: 6,
      fontSize: 14,
    },
    card: {
      backgroundColor: isDarkMode ? colors.surface : "rgba(255,255,255,0.9)",
      borderWidth: 1,
      borderColor: colors.border,
      borderRadius: 22,
      padding: 18,
      marginBottom: 14,
    },
    rowBetween: {
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "space-between",
      gap: 14,
    },
    flexOne: {
      flex: 1,
    },
    sectionTitle: {
      color: colors.title,
      fontSize: 16,
      fontWeight: "900",
      marginBottom: 6,
    },
    mutedText: {
      color: colors.textMuted,
      fontSize: 14,
      lineHeight: 20,
    },
    separator: {
      height: 1,
      backgroundColor: colors.border,
      marginVertical: 14,
    },
    badge: {
      borderRadius: 999,
      paddingHorizontal: 12,
      paddingVertical: 7,
    },
    badgeOk: {
      backgroundColor: "rgba(46, 158, 111, 0.18)",
    },
    badgeWarn: {
      backgroundColor: "rgba(217, 83, 79, 0.16)",
    },
    badgeNeutral: {
      backgroundColor: isDarkMode ? colors.card : colors.softBlue,
    },
    badgeText: {
      color: colors.title,
      fontSize: 12,
      fontWeight: "900",
    },
    buttonTop: {
      marginTop: 14,
    },
    codeBox: {
      marginTop: 14,
      borderWidth: 1,
      borderColor: colors.primary,
      backgroundColor: isDarkMode ? colors.card : colors.backgroundAlt,
      borderRadius: 18,
      padding: 14,
    },
    codeLabel: {
      color: colors.textMuted,
      fontSize: 13,
      marginBottom: 6,
    },
    codeText: {
      color: colors.title,
      fontSize: 24,
      fontWeight: "900",
      letterSpacing: 1,
      marginBottom: 6,
    },
    command: {
      color: colors.text,
      backgroundColor: isDarkMode ? colors.card : colors.backgroundAlt,
      borderRadius: 12,
      paddingVertical: 8,
      paddingHorizontal: 12,
      marginTop: 8,
      fontWeight: "700",
    },
    messageItem: {
      borderTopWidth: 1,
      borderTopColor: colors.border,
      paddingTop: 10,
      marginTop: 10,
    },
    messageDirection: {
      color: colors.primary,
      fontWeight: "900",
      marginBottom: 4,
    },
    messageText: {
      color: colors.text,
      lineHeight: 20,
    },
    centerBox: {
      flex: 1,
      minHeight: 300,
      alignItems: "center",
      justifyContent: "center",
      gap: 12,
    },
  });
}
