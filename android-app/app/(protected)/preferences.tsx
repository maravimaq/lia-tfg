import React, { useEffect, useMemo } from "react";
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
import { preferencesService } from "@/src/services/preferences";
import { AppColors } from "@/src/constants/colors";
import { useAppTheme } from "@/src/hooks/useAppTheme";
import { PreferenciasFormValues, PreferenciasUpdatePayload } from "@/src/types/preferences";

const LANGUAGE_OPTIONS = [
  { value: "es", label: "Español" },
  { value: "en", label: "Inglés" },
] as const;

const WEIGHT_OPTIONS = [
  { value: "kg", label: "kg" },
  { value: "g", label: "g" },
  { value: "lb", label: "lb" },
] as const;

const PRICE_OPTIONS = [
  { value: "EUR", label: "EUR" },
  { value: "USD", label: "USD" },
] as const;

const SUPERMARKET_OPTIONS = [
  { value: "", label: "Sin favorito" },
  { value: "Mercadona", label: "Mercadona" },
  { value: "DIA", label: "DIA" },
  { value: "Carrefour", label: "Carrefour" },
  { value: "ALDI", label: "ALDI" },
  { value: "Alcampo", label: "Alcampo" },
] as const;

type Option = {
  value: string;
  label: string;
};

type OptionChipGroupProps = {
  label: string;
  options: readonly Option[];
  selected: string;
  onSelect: (value: string) => void;
  styles: ReturnType<typeof createStyles>;
};

function OptionChipGroup({
  label,
  options,
  selected,
  onSelect,
  styles,
}: OptionChipGroupProps) {
  return (
    <View style={styles.fieldGroup}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <View style={styles.chipsWrap}>
        {options.map((option) => {
          const active = option.value === selected;
          return (
            <Pressable
              key={option.value || "none"}
              onPress={() => onSelect(option.value)}
              style={[styles.chip, active && styles.chipActive]}
            >
              <Text style={[styles.chipText, active && styles.chipTextActive]}>
                {option.label}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

type ToggleRowProps = {
  label: string;
  description?: string;
  value: boolean;
  onValueChange: (value: boolean) => void;
  styles: ReturnType<typeof createStyles>;
  colors: AppColors;
};

function ToggleRow({
  label,
  description,
  value,
  onValueChange,
  styles,
  colors,
}: ToggleRowProps) {
  return (
    <View style={styles.toggleRow}>
      <View style={styles.toggleTextWrap}>
        <Text style={styles.fieldLabelNoMargin}>{label}</Text>
        {description ? <Text style={styles.toggleDescription}>{description}</Text> : null}
      </View>
      <Switch
        value={value}
        onValueChange={onValueChange}
        trackColor={{ false: colors.border, true: colors.primary }}
        thumbColor={colors.white}
      />
    </View>
  );
}

export default function PreferencesScreen() {
  const { colors, isDarkMode, setDarkMode } = useAppTheme();
  const styles = useMemo(
    () => createStyles(colors, isDarkMode),
    [colors, isDarkMode]
  );

  const {
    control,
    handleSubmit,
    reset,
    formState: { isSubmitting },
  } = useForm<PreferenciasFormValues>({
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
    const loadPreferences = async () => {
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
        await setDarkMode(Boolean(prefs.modo_oscuro));
      } catch (error: any) {
        Alert.alert(
          "Error",
          error?.response?.data?.detail || "No se pudieron cargar las preferencias"
        );
      }
    };

    loadPreferences();
  }, [reset, setDarkMode]);

  const onSubmit = async (values: PreferenciasFormValues) => {
    try {
      const selectedSupermarket = values.supermercado_favorito;

      const payload: PreferenciasUpdatePayload = {
        ...values,
        supermercado_favorito: selectedSupermarket ? selectedSupermarket : null,
      };

      const updatedPreferences = await preferencesService.updateMyPreferences(payload);
      await setDarkMode(Boolean(updatedPreferences.modo_oscuro));

      reset({
        idioma: updatedPreferences.idioma,
        modo_oscuro: updatedPreferences.modo_oscuro,
        notificaciones: updatedPreferences.notificaciones,
        unidad_peso: updatedPreferences.unidad_peso,
        unidad_precio: updatedPreferences.unidad_precio,
        supermercado_favorito: updatedPreferences.supermercado_favorito ?? "",
      });

      Alert.alert(
        "Preferencias actualizadas",
        "Tus preferencias se han guardado correctamente."
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
            <OptionChipGroup
              label="Supermercado favorito"
              options={SUPERMARKET_OPTIONS}
              selected={value ?? ""}
              onSelect={onChange}
              styles={styles}
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
              selected={value ?? "es"}
              onSelect={onChange}
              styles={styles}
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
              selected={value ?? "kg"}
              onSelect={onChange}
              styles={styles}
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
              selected={value ?? "EUR"}
              onSelect={onChange}
              styles={styles}
            />
          )}
        />

        <Controller
          control={control}
          name="notificaciones"
          render={({ field: { onChange, value } }) => (
            <ToggleRow
              label="Notificaciones"
              description="Activa o desactiva avisos de la aplicación."
              value={Boolean(value)}
              onValueChange={onChange}
              styles={styles}
              colors={colors}
            />
          )}
        />

        <Controller
          control={control}
          name="modo_oscuro"
          render={({ field: { onChange, value } }) => (
            <ToggleRow
              label="Modo oscuro"
              description="Aplica la preferencia visual a la app."
              value={Boolean(value)}
              onValueChange={onChange}
              styles={styles}
              colors={colors}
            />
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

function createStyles(colors: AppColors, isDarkMode: boolean) {
  return StyleSheet.create({
    header: {
      marginBottom: 22,
    },
    title: {
      fontSize: 28,
      fontWeight: "800",
      color: colors.title,
    },
    subtitle: {
      marginTop: 6,
      color: colors.textMuted,
    },
    card: {
      backgroundColor: isDarkMode ? "rgba(27,32,53,0.94)" : "rgba(255,255,255,0.88)",
      borderRadius: 24,
      padding: 18,
      borderWidth: 1,
      borderColor: colors.border,
    },
    fieldGroup: {
      marginBottom: 14,
    },
    fieldLabel: {
      marginBottom: 8,
      color: colors.title,
      fontSize: 14,
      fontWeight: "600",
    },
    fieldLabelNoMargin: {
      color: colors.title,
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
      borderColor: colors.border,
      borderRadius: 14,
      paddingVertical: 8,
      paddingHorizontal: 14,
      backgroundColor: colors.surface,
    },
    chipActive: {
      borderColor: colors.primary,
      backgroundColor: isDarkMode ? colors.card : colors.softBlue,
    },
    chipText: {
      color: colors.text,
      fontWeight: "600",
    },
    chipTextActive: {
      color: colors.title,
    },
    toggleRow: {
      minHeight: 62,
      borderWidth: 1,
      borderColor: colors.border,
      borderRadius: 16,
      backgroundColor: colors.surface,
      paddingHorizontal: 14,
      paddingVertical: 10,
      marginBottom: 12,
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "space-between",
      gap: 12,
    },
    toggleTextWrap: {
      flex: 1,
    },
    toggleDescription: {
      marginTop: 4,
      color: colors.textMuted,
      fontSize: 12,
    },
  });
}
