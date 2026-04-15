import React, { useEffect } from "react";
import { Alert, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import { Controller, useForm } from "react-hook-form";

import Screen from "@/src/components/Screen";
import AppButton from "@/src/components/AppButton";
import AppInput from "@/src/components/AppInput";
import { preferencesService } from "@/src/services/preferences";
import { Colors } from "@/src/constants/colors";
import { PreferenciasUpdatePayload } from "@/src/types/preferences";

export default function PreferencesScreen() {
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
      Alert.alert("Preferencias actualizadas", "Tus preferencias se han guardado correctamente.");
      router.back();
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
          name="unidad_peso"
          render={({ field: { onChange, value } }) => (
            <AppInput
              label="Unidad de peso"
              placeholder="kg"
              value={value}
              onChangeText={onChange}
            />
          )}
        />

        <Controller
          control={control}
          name="unidad_precio"
          render={({ field: { onChange, value } }) => (
            <AppInput
              label="Unidad de precio"
              placeholder="EUR"
              value={value}
              onChangeText={onChange}
            />
          )}
        />

        <Controller
          control={control}
          name="idioma"
          render={({ field: { onChange, value } }) => (
            <AppInput
              label="Idioma"
              placeholder="es"
              value={value}
              onChangeText={onChange}
            />
          )}
        />

        <Controller
          control={control}
          name="notificaciones"
          render={({ field: { onChange, value } }) => (
            <AppInput
              label="Notificaciones"
              placeholder="true / false"
              value={String(value)}
              onChangeText={(text) => onChange(text.toLowerCase() === "true")}
            />
          )}
        />

        <Controller
          control={control}
          name="modo_oscuro"
          render={({ field: { onChange, value } }) => (
            <AppInput
              label="Modo oscuro"
              placeholder="true / false"
              value={String(value)}
              onChangeText={(text) => onChange(text.toLowerCase() === "true")}
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
});