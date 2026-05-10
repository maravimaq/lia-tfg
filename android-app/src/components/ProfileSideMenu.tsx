import React, { useEffect, useState } from "react";
import {
  Modal,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { router } from "expo-router";

import AppButton from "@/src/components/AppButton";
import { Colors } from "@/src/constants/colors";

type Props = {
  visible: boolean;
  onClose: () => void;
  onLogout: () => void | Promise<void>;
  onDeleteAccount?: () => void | Promise<void>;
  isAdmin?: boolean;
};

type MenuItemProps = {
  label: string;
  onPress: () => void;
  danger?: boolean;
  disabled?: boolean;
};

type ConfirmationAction = "logout" | "delete" | null;

function MenuItem({ label, onPress, danger = false, disabled = false }: MenuItemProps) {
  return (
    <Pressable
      style={[styles.item, disabled && styles.disabledItem]}
      onPress={onPress}
      disabled={disabled}
      hitSlop={8}
    >
      <Text style={[styles.itemText, danger && styles.dangerText]}>{label}</Text>
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
  const [confirmationAction, setConfirmationAction] = useState<ConfirmationAction>(null);
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

      router.push("/(protected)/profile/account-action");
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
        <Pressable style={styles.backdrop} onPress={closeMenu} disabled={processing} />
        <View style={styles.panel}>
          <View style={styles.header}>
            <Text style={styles.title}>Menú</Text>
            <Pressable onPress={closeMenu} disabled={processing} hitSlop={8}>
              <Text style={styles.close}>✕</Text>
            </Pressable>
          </View>

          {confirmationAction ? (
            renderConfirmation()
          ) : (
            <>
              <MenuItem
                label="Configuración Bot Externo"
                onPress={() => {
                  onClose();
                  router.push("/(protected)/profile/bot-config");
                }}
              />

              <MenuItem
                label="FAQ"
                onPress={() => {
                  onClose();
                  router.push("/(protected)/profile/faq");
                }}
              />

              <MenuItem
                label="Sobre LIA"
                onPress={() => {
                  onClose();
                  router.push("/(protected)/profile/about");
                }}
              />

              <MenuItem
                label="Ayuda y Soporte"
                onPress={() => {
                  onClose();
                  router.push("/(protected)/profile/support");
                }}
              />

              <MenuItem
                label="Información de Contacto"
                onPress={() => {
                  onClose();
                  router.push("/(protected)/profile/contact-info");
                }}
              />

              {isAdmin ? (
                <MenuItem
                  label="Panel de administración"
                  onPress={() => {
                    onClose();
                    router.push("/(protected)/admin");
                  }}
                />
              ) : null}

              <MenuItem
                label="Mi perfil"
                onPress={() => {
                  onClose();
                  router.push("/(protected)/profile");
                }}
              />

              <View style={styles.separator} />

              <MenuItem
                label="Cerrar sesión"
                onPress={() => setConfirmationAction("logout")}
                danger
              />

              <MenuItem
                label="Eliminar cuenta"
                onPress={() => setConfirmationAction("delete")}
                danger
              />

              <Text style={styles.footer}>© 2025-2026 LIA</Text>
            </>
          )}
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    flexDirection: "row",
    backgroundColor: "rgba(0,0,0,0.18)",
  },
  backdrop: {
    flex: 1,
  },
  panel: {
    width: 290,
    backgroundColor: Colors.surface,
    paddingTop: 20,
    paddingHorizontal: 18,
    borderLeftWidth: 1,
    borderLeftColor: Colors.border,
    shadowColor: "#A9B6E5",
    shadowOpacity: 0.15,
    shadowRadius: 10,
    shadowOffset: { width: -4, height: 0 },
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 18,
  },
  title: {
    fontSize: 22,
    fontWeight: "800",
    color: Colors.title,
  },
  close: {
    fontSize: 24,
    color: Colors.text,
    fontWeight: "700",
  },
  item: {
    paddingVertical: 12,
  },
  disabledItem: {
    opacity: 0.5,
  },
  itemText: {
    fontSize: 16,
    color: Colors.text,
    fontWeight: "600",
  },
  dangerText: {
    color: Colors.danger,
  },
  separator: {
    marginTop: 8,
    marginBottom: 8,
    height: 1,
    backgroundColor: Colors.border,
  },
  confirmationBox: {
    borderRadius: 18,
    borderWidth: 1,
    borderColor: Colors.border,
    backgroundColor: Colors.card,
    padding: 14,
  },
  confirmationTitle: {
    color: Colors.title,
    fontSize: 20,
    fontWeight: "800",
    marginBottom: 8,
  },
  confirmationText: {
    color: Colors.text,
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
    marginTop: 20,
    color: Colors.textMuted,
    fontSize: 12,
    textAlign: "center",
  },
});