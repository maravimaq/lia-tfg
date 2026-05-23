import React from "react";
import {
  Alert,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { router } from "expo-router";

import { Colors } from "@/src/constants/colors";

type Props = {
  visible: boolean;
  onClose: () => void;
  onLogout: () => void;
  isAdmin?: boolean;
};

type MenuItemProps = {
  icon: string;
  label: string;
  onPress: () => void;
  danger?: boolean;
};

function MenuItem({ icon, label, onPress, danger = false }: MenuItemProps) {
  return (
    <Pressable style={styles.item} onPress={onPress}>
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
  isAdmin = false,
}: Props) {
  const goTo = (path: string) => {
    onClose();
    router.push(path as never);
  };

  const showComingSoon = (sectionName: string) => {
    onClose();

    Alert.alert(
      "Próximamente",
      `${sectionName} se implementará más adelante.`
    );
  };

  const confirmLogout = () => {
    Alert.alert("Cerrar sesión", "¿Estás seguro de que quieres cerrar sesión?", [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Cerrar sesión",
        style: "destructive",
        onPress: () => {
          onClose();
          onLogout();
        },
      },
    ]);
  };

  const confirmDelete = () => {
    Alert.alert(
      "Eliminar cuenta",
      "Esta sección se implementará más adelante.",
      [{ text: "Aceptar" }]
    );
  };

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onClose}
    >
      <View style={styles.overlay}>
        <Pressable style={styles.backdrop} onPress={onClose} />

        <View style={styles.panel}>
          <View style={styles.closeRow}>
            <Pressable style={styles.closeButton} onPress={onClose}>
              <Text style={styles.close}>×</Text>
            </Pressable>
          </View>

          <ScrollView
            showsVerticalScrollIndicator={false}
            contentContainerStyle={styles.scrollContent}
          >
            <MenuItem
              icon="⚙"
              label="Configuración Bot Externo"
              onPress={() => showComingSoon("Configuración Bot Externo")}
            />

            <MenuItem
              icon="?"
              label="FAQ"
              onPress={() => showComingSoon("FAQ")}
            />

            <MenuItem
              icon="i"
              label="Sobre LIA"
              onPress={() => showComingSoon("Sobre LIA")}
            />

            <MenuItem
              icon="○"
              label="Ayuda y Soporte"
              onPress={() => showComingSoon("Ayuda y Soporte")}
            />

            <MenuItem
              icon="✉"
              label="Información de Contacto"
              onPress={() => showComingSoon("Información de Contacto")}
            />

            <View style={styles.separator} />

            <MenuItem
              icon="☷"
              label="Mis Listas Pendientes"
              onPress={() => goTo("/listas")}
            />

            <MenuItem
              icon="☷"
              label="Historial de Listas"
              onPress={() => goTo("/historial")}
            />

            <MenuItem
              icon="%"
              label="Comparador Precios"
              onPress={() => goTo("/productos/comparar")}
            />

            {isAdmin ? (
              <MenuItem
                icon="▦"
                label="Panel Admin"
                onPress={() => goTo("/admin")}
              />
            ) : null}

            <MenuItem
              icon="◉"
              label="Mi perfil"
              onPress={() => goTo("/profile")}
            />

            <View style={styles.separator} />

            <MenuItem
              icon="↪"
              label="Cerrar Sesión"
              onPress={confirmLogout}
              danger
            />

            <View style={styles.smallSeparator} />

            <MenuItem
              icon="▢"
              label="Eliminar Cuenta"
              onPress={confirmDelete}
              danger
            />
          </ScrollView>

          <View style={styles.footerBox}>
            <Text style={styles.footer}>© 2025-2026 LIA</Text>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    flexDirection: "row",
    backgroundColor: "rgba(0, 0, 0, 0.12)",
  },
  backdrop: {
    flex: 1,
  },
  panel: {
    width: 220,
    backgroundColor: "#E5E5E5",
    borderLeftWidth: 1,
    borderLeftColor: "#D0D0D0",
    shadowColor: "#000",
    shadowOpacity: 0.18,
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
    color: "#222222",
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
    color: "#222222",
    fontWeight: "700",
    textAlign: "center",
  },
  itemText: {
    flex: 1,
    color: "#2D2D2D",
    fontSize: 15,
    lineHeight: 20,
    textAlign: "right",
    fontWeight: "500",
  },
  dangerText: {
    color: "#E51D2A",
  },
  separator: {
    height: 1,
    backgroundColor: "#CFCFCF",
    marginVertical: 8,
    marginLeft: 58,
    marginRight: 12,
  },
  smallSeparator: {
    height: 1,
    backgroundColor: "#CFCFCF",
    marginVertical: 4,
    marginLeft: 58,
    marginRight: 12,
  },
  footerBox: {
    borderTopWidth: 1,
    borderTopColor: "#CFCFCF",
    paddingTop: 10,
    paddingBottom: 14,
    paddingHorizontal: 12,
  },
  footer: {
    color: "#777777",
    fontSize: 11,
    textAlign: "center",
    fontWeight: "700",
    letterSpacing: 0.4,
  },
});