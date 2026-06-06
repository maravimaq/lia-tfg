import React, { useEffect, useMemo, useState } from "react";
import {
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { router } from "expo-router";

import AppButton from "@/src/components/AppButton";
import { AppColors } from "@/src/constants/colors";
import { useAppTheme } from "@/src/hooks/useAppTheme";

type Props = {
  visible: boolean;
  onClose: () => void;
  onLogout: () => void | Promise<void>;
  onDeleteAccount?: () => void | Promise<void>;
  isAdmin?: boolean;
};

type MenuItemProps = {
  icon: string;
  label: string;
  onPress: () => void;
  danger?: boolean;
  disabled?: boolean;
  styles: ReturnType<typeof createStyles>;
};

type ConfirmationAction = "logout" | "delete" | null;

function MenuItem({
  icon,
  label,
  onPress,
  danger = false,
  disabled = false,
  styles,
}: MenuItemProps) {
  return (
    <Pressable
      style={[styles.item, disabled && styles.disabledItem]}
      onPress={onPress}
      disabled={disabled}
      hitSlop={8}
    >
      <View style={styles.iconBox}>
        <Text style={[styles.icon, danger && styles.dangerText]}>{icon}</Text>
      </View>

      <Text style={[styles.itemText, danger && styles.dangerText]}>
        {label}
      </Text>
    </Pressable>
  );
}

export default function ProfileSideMenu({
  visible,
  onClose,
  onLogout,
  onDeleteAccount,
  isAdmin = false,
}: Props) {
  const { colors, isDarkMode } = useAppTheme();
  const styles = useMemo(
    () => createStyles(colors, isDarkMode),
    [colors, isDarkMode]
  );
  const [confirmationAction, setConfirmationAction] =
    useState<ConfirmationAction>(null);
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    if (!visible) {
      setConfirmationAction(null);
      setProcessing(false);
    }
  }, [visible]);

  const closeMenu = () => {
    if (processing) return;
    setConfirmationAction(null);
    onClose();
  };

  const goTo = (path: string) => {
    onClose();
    router.push(path as never);
  };

  const handleConfirmedAction = async () => {
    if (!confirmationAction || processing) return;

    try {
      setProcessing(true);

      const actionToRun = confirmationAction;
      setConfirmationAction(null);
      onClose();

      if (actionToRun === "logout") {
        await onLogout();
        return;
      }

      if (onDeleteAccount) {
        await onDeleteAccount();
        return;
      }

      router.push("/(protected)/profile/account-action" as never);
    } finally {
      setProcessing(false);
    }
  };

  const renderConfirmation = () => {
    const isLogout = confirmationAction === "logout";

    return (
      <View style={styles.confirmationBox}>
        <Text style={styles.confirmationTitle}>
          {isLogout ? "Cerrar sesión" : "Eliminar cuenta"}
        </Text>

        <Text style={styles.confirmationText}>
          {isLogout
            ? "¿Estás seguro de que quieres cerrar sesión?"
            : "¿Estás seguro de que quieres eliminar tu cuenta? Se cerrará tu sesión, la cuenta quedará inactiva y el administrador recibirá la solicitud."}
        </Text>

        <View style={styles.confirmationActions}>
          <AppButton
            title="Cancelar"
            variant="ghost"
            onPress={() => setConfirmationAction(null)}
            disabled={processing}
            style={styles.confirmationButton}
          />

          <AppButton
            title={isLogout ? "Cerrar sesión" : "Eliminar cuenta"}
            variant="danger"
            onPress={handleConfirmedAction}
            loading={processing}
            style={styles.confirmationButton}
          />
        </View>
      </View>
    );
  };

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={closeMenu}
    >
      <View style={styles.overlay}>
        <Pressable
          style={styles.backdrop}
          onPress={closeMenu}
          disabled={processing}
        />

        <View style={styles.panel}>
          <View style={styles.closeRow}>
            <Pressable
              style={styles.closeButton}
              onPress={closeMenu}
              disabled={processing}
              hitSlop={8}
            >
              <Text style={styles.close}>×</Text>
            </Pressable>
          </View>

          {confirmationAction ? (
            renderConfirmation()
          ) : (
            <>
              <ScrollView
                showsVerticalScrollIndicator={false}
                contentContainerStyle={styles.scrollContent}
              >
                <MenuItem
                  icon="⚙"
                  label="Configuración Bot Externo"
                  onPress={() => goTo("/(protected)/profile/bot-config")}
                  styles={styles}
                />

                <MenuItem
                  icon="?"
                  label="FAQ"
                  onPress={() => goTo("/(protected)/profile/faq")}
                  styles={styles}
                />

                <MenuItem
                  icon="i"
                  label="Sobre LIA"
                  onPress={() => goTo("/(protected)/profile/about")}
                  styles={styles}
                />

                <MenuItem
                  icon="○"
                  label="Ayuda y Soporte"
                  onPress={() => goTo("/(protected)/profile/support")}
                  styles={styles}
                />

                <MenuItem
                  icon="✉"
                  label="Información de Contacto"
                  onPress={() => goTo("/(protected)/profile/contact-info")}
                  styles={styles}
                />

                <View style={styles.separator} />

                <MenuItem
                  icon="☷"
                  label="Mis Listas Pendientes"
                  onPress={() => goTo("/listas")}
                  styles={styles}
                />

                <MenuItem
                  icon="☷"
                  label="Historial de Listas"
                  onPress={() => goTo("/historial")}
                  styles={styles}
                />

                <MenuItem
                  icon="%"
                  label="Comparador Precios"
                  onPress={() => goTo("/productos/comparar")}
                  styles={styles}
                />

                {isAdmin ? (
                  <MenuItem
                    icon="▦"
                    label="Panel Admin"
                    onPress={() => goTo("/(protected)/admin")}
                    styles={styles}
                  />
                ) : null}

                <MenuItem
                  icon="◉"
                  label="Mi perfil"
                  onPress={() => goTo("/(protected)/profile")}
                  styles={styles}
                />

                <View style={styles.separator} />

                <MenuItem
                  icon="↪"
                  label="Cerrar Sesión"
                  onPress={() => setConfirmationAction("logout")}
                  danger
                  styles={styles}
                />

                <View style={styles.smallSeparator} />

                <MenuItem
                  icon="▢"
                  label="Eliminar Cuenta"
                  onPress={() => setConfirmationAction("delete")}
                  danger
                  styles={styles}
                />
              </ScrollView>

              <View style={styles.footerBox}>
                <Text style={styles.footer}>© 2025-2026 LIA</Text>
              </View>
            </>
          )}
        </View>
      </View>
    </Modal>
  );
}

function createStyles(colors: AppColors, isDarkMode: boolean) {
  return StyleSheet.create({
    overlay: {
      flex: 1,
      flexDirection: "row",
      backgroundColor: isDarkMode ? "rgba(0, 0, 0, 0.42)" : "rgba(0, 0, 0, 0.12)",
    },
    backdrop: {
      flex: 1,
    },
    panel: {
      width: 220,
      backgroundColor: colors.surface,
      borderLeftWidth: 1,
      borderLeftColor: colors.border,
      shadowColor: "#000",
      shadowOpacity: isDarkMode ? 0.34 : 0.18,
      shadowRadius: 10,
      shadowOffset: { width: -3, height: 0 },
      elevation: 8,
    },
    closeRow: {
      alignItems: "flex-end",
      paddingTop: 14,
      paddingRight: 14,
      paddingBottom: 6,
    },
    closeButton: {
      width: 34,
      height: 34,
      alignItems: "center",
      justifyContent: "center",
    },
    close: {
      fontSize: 36,
      color: colors.title,
      fontWeight: "700",
      lineHeight: 36,
    },
    scrollContent: {
      paddingBottom: 12,
    },
    item: {
      minHeight: 48,
      paddingRight: 12,
      paddingLeft: 12,
      flexDirection: "row",
      alignItems: "center",
    },
    iconBox: {
      width: 42,
      alignItems: "center",
      justifyContent: "center",
      marginRight: 8,
    },
    icon: {
      fontSize: 28,
      color: colors.title,
      fontWeight: "700",
      textAlign: "center",
    },
    disabledItem: {
      opacity: 0.5,
    },
    itemText: {
      flex: 1,
      color: colors.text,
      fontSize: 15,
      lineHeight: 20,
      textAlign: "right",
      fontWeight: "500",
    },
    dangerText: {
      color: colors.danger,
    },
    separator: {
      height: 1,
      backgroundColor: colors.border,
      marginVertical: 8,
      marginLeft: 58,
      marginRight: 12,
    },
    smallSeparator: {
      height: 1,
      backgroundColor: colors.border,
      marginVertical: 4,
      marginLeft: 58,
      marginRight: 12,
    },
    footerBox: {
      borderTopWidth: 1,
      borderTopColor: colors.border,
      paddingTop: 10,
      paddingBottom: 14,
      paddingHorizontal: 12,
    },
    confirmationBox: {
      margin: 12,
      borderRadius: 18,
      borderWidth: 1,
      borderColor: colors.border,
      backgroundColor: colors.card,
      padding: 14,
    },
    confirmationTitle: {
      color: colors.title,
      fontSize: 20,
      fontWeight: "800",
      marginBottom: 8,
    },
    confirmationText: {
      color: colors.text,
      fontSize: 14,
      lineHeight: 20,
      marginBottom: 14,
    },
    confirmationActions: {
      gap: 8,
    },
    confirmationButton: {
      minHeight: 46,
    },
    footer: {
      color: colors.textMuted,
      fontSize: 11,
      textAlign: "center",
      fontWeight: "700",
      letterSpacing: 0.4,
    },
  });
}
