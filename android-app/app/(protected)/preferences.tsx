import React, { useEffect } from "react";
import {
  Alert,
  Pressable,
  StyleSheet,
  Switch,
  Text,
  View,
} from "react-native";
import { router } from "expo-router";
import { Controller, useForm } from "react-hook-form";

import Screen from "@/src/components/Screen";
import AppButton from "@/src/components/AppButton";
import AppInput from "@/src/components/AppInput";
import { preferencesService } from "@/src/services/preferences";
import { Colors } from "@/src/constants/colors";
import { PreferenciasUpdatePayload } from "@/src/types/preferences";
import { useAuth } from "@/src/hooks/useAuth";

const LANGUAGE_OPTIONS = ["es", "en"] as const;
const WEIGHT_OPTIONS = ["kg", "g", "lb"] as const;
const PRICE_OPTIONS = ["EUR", "USD"] as const;

type OptionChipGroupProps = {
  label: string;
  options: readonly string[];
  selected: string;
  onSelect: (value: string) => void;
};

function OptionChipGroup({ label, options, selected, onSelect }: OptionChipGroupProps) {
  return (
    <View style={styles.fieldGroup}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <View style={styles.chipsWrap}>
        {options.map((option) => {
          const active = option === selected;
          return (
            <Pressable
              key={option}
              onPress={() => onSelect(option)}
              style={[styles.chip, active && styles.chipActive]}
            >
              <Text style={[styles.chipText, active && styles.chipTextActive]}>{option}</Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

type ToggleRowProps = {
  label: string;
  value: boolean;
  onValueChange: (value: boolean) => void;
};

function ToggleRow({ label, value, onValueChange }: ToggleRowProps) {
  return (
    <View style={styles.toggleRow}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <Switch
        value={value}
        onValueChange={onValueChange}
        trackColor={{ false: Colors.border, true: Colors.primary }}
        thumbColor={Colors.white}
      />
    </View>
  );
}

export default function PreferencesScreen() {
  const { signOut } = useAuth();
  const {
    control,
    handleSubmit,
    reset,
    formState: { isSubmitting },
  } = useForm<PreferenciasUpdatePayload>({
    defaultValues: {
      idioma: "es",
      modo_oscuro: false,
      notificaciones: true,
      unidad_peso: "kg",
      unidad_precio: "EUR",
      supermercado_favorito: "",
    },
  });

  useEffect(() => {
    const load = async () => {
      try {
        const prefs = await preferencesService.getMyPreferences();
        reset({
          idioma: prefs.idioma,
          modo_oscuro: prefs.modo_oscuro,
          notificaciones: prefs.notificaciones,
          unidad_peso: prefs.unidad_peso,
          unidad_precio: prefs.unidad_precio,
          supermercado_favorito: prefs.supermercado_favorito ?? "",
        });
      } catch (error: any) {
        Alert.alert(
          "Error",
          error?.response?.data?.detail || "No se pudieron cargar las preferencias"
        );
      }
    };

    load();
  }, [reset]);

  const onSubmit = async (values: PreferenciasUpdatePayload) => {
    try {
      await preferencesService.updateMyPreferences(values);
      await signOut();

      Alert.alert(
        "Preferencias actualizadas",
        "Por seguridad, inicia sesión de nuevo para aplicar los cambios.",
        [{ text: "Aceptar", onPress: () => router.replace("/(auth)/sign-in") }]
      );
    } catch (error: any) {
      Alert.alert(
        "Error",
        error?.response?.data?.detail || "No se pudieron guardar las preferencias"
      );
    }
  };

  return (
    <Screen>
      <View style={styles.header}>
        <Text style={styles.title}>Preferencias</Text>
        <Text style={styles.subtitle}>Configura tu experiencia en la app</Text>
      </View>

      <View style={styles.card}>
        <Controller
          control={control}
          name="supermercado_favorito"
          render={({ field: { onChange, value } }) => (
            <AppInput
              label="Supermercado favorito"
              placeholder="Mercadona"
              value={value ?? ""}
              onChangeText={onChange}
            />
          )}
        />

        <Controller
          control={control}
          name="idioma"
          render={({ field: { onChange, value } }) => (
            <OptionChipGroup
              label="Idioma"
              options={LANGUAGE_OPTIONS}
              selected={value}
              onSelect={onChange}
            />
          )}
        />

        <Controller
          control={control}
          name="unidad_peso"
          render={({ field: { onChange, value } }) => (
            <OptionChipGroup
              label="Unidad de peso"
              options={WEIGHT_OPTIONS}
              selected={value}
              onSelect={onChange}
            />
          )}
        />

        <Controller
          control={control}
          name="unidad_precio"
          render={({ field: { onChange, value } }) => (
            <OptionChipGroup
              label="Moneda"
              options={PRICE_OPTIONS}
              selected={value}
              onSelect={onChange}
            />
          )}
        />

        <Controller
          control={control}
          name="notificaciones"
          render={({ field: { onChange, value } }) => (
            <ToggleRow label="Notificaciones" value={value} onValueChange={onChange} />
          )}
        />

        <Controller
          control={control}
          name="modo_oscuro"
          render={({ field: { onChange, value } }) => (
            <ToggleRow label="Modo oscuro" value={value} onValueChange={onChange} />
          )}
        />
      </View>

      <AppButton
        title="Guardar preferencias"
        onPress={handleSubmit(onSubmit)}
        loading={isSubmitting}
        style={{ marginTop: 18 }}
      />

      <AppButton
        title="Volver"
        variant="ghost"
        onPress={() => router.back()}
        style={{ marginTop: 12 }}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    marginBottom: 22,
  },
  title: {
    fontSize: 28,
    fontWeight: "800",
    color: Colors.title,
  },
  subtitle: {
    marginTop: 6,
    color: Colors.textMuted,
  },
  card: {
    backgroundColor: "rgba(255,255,255,0.88)",
    borderRadius: 24,
    padding: 18,
    borderWidth: 1,
    borderColor: Colors.border,
  },

  fieldGroup: {
    marginBottom: 14,
  },
  fieldLabel: {
    marginBottom: 8,
    color: Colors.title,
    fontSize: 14,
    fontWeight: "600",
  },
  chipsWrap: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  chip: {
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 14,
    paddingVertical: 8,
    paddingHorizontal: 14,
    backgroundColor: Colors.surface,
  },
  chipActive: {
    borderColor: Colors.primary,
    backgroundColor: Colors.softBlue,
  },
  chipText: {
    color: Colors.text,
    fontWeight: "600",
  },
  chipTextActive: {
    color: Colors.title,
  },
  toggleRow: {
    minHeight: 54,
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 16,
    backgroundColor: Colors.surface,
    paddingHorizontal: 14,
    marginBottom: 12,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
});