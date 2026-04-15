import React from "react";
import {
  Modal,
  Pressable,
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
};

type MenuItemProps = {
  label: string;
  onPress: () => void;
  danger?: boolean;
};

function MenuItem({ label, onPress, danger = false }: MenuItemProps) {
  return (
    <Pressable style={styles.item} onPress={onPress}>
      <Text style={[styles.itemText, danger && styles.dangerText]}>{label}</Text>
    </Pressable>
  );
}

export default function ProfileSideMenu({
  visible,
  onClose,
  onLogout,
}: Props) {
  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onClose}
    >
      <View style={styles.overlay}>
        <Pressable style={styles.backdrop} onPress={onClose} />
        <View style={styles.panel}>
          <View style={styles.header}>
            <Text style={styles.title}>Menú</Text>
            <Pressable onPress={onClose}>
              <Text style={styles.close}>✕</Text>
            </Pressable>
          </View>

          <MenuItem
            label="Configuración Bot Externo"
            onPress={() => {
              onClose();
            }}
          />

          <MenuItem
            label="FAQ"
            onPress={() => {
              onClose();
            }}
          />

          <MenuItem
            label="Sobre LIA"
            onPress={() => {
              onClose();
            }}
          />

          <MenuItem
            label="Ayuda y Soporte"
            onPress={() => {
              onClose();
            }}
          />

          <MenuItem
            label="Información de Contacto"
            onPress={() => {
              onClose();
            }}
          />

          <MenuItem
            label="Mis listas pendientes"
            onPress={() => {
              onClose();
            }}
          />

          <MenuItem
            label="Historial de listas"
            onPress={() => {
              onClose();
            }}
          />

          <MenuItem
            label="Comparador de precios"
            onPress={() => {
              onClose();
            }}
          />

          <MenuItem
            label="Listas compartidas"
            onPress={() => {
              onClose();
            }}
          />

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
            onPress={() => {
              onClose();
              onLogout();
            }}
            danger
          />

          <MenuItem
            label="Eliminar cuenta"
            onPress={() => {
              onClose();
            }}
            danger
          />

          <Text style={styles.footer}>© 2025-2026 LIA</Text>
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
  footer: {
    marginTop: 20,
    color: Colors.textMuted,
    fontSize: 12,
    textAlign: "center",
  },
});