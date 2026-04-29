import React, { useEffect } from "react";
import { Alert, Pressable, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import { Controller, useForm } from "react-hook-form";

import Screen from "@/src/components/Screen";
import AppButton from "@/src/components/AppButton";
import AppInput from "@/src/components/AppInput";
import { Colors } from "@/src/constants/colors";
import { BotConfigUpdatePayload } from "@/src/types/user";
import { userService } from "@/src/services/user";

const PLATFORM_OPTIONS = ["telegram", "whatsapp"] as const;
const STATUS_OPTIONS = ["activo", "inactivo"] as const;

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

export default function BotConfigScreen() {
  const {
    control,
    handleSubmit,
    reset,
    formState: { isSubmitting },
  } = useForm<BotConfigUpdatePayload>({
    defaultValues: {
      plataforma: "telegram",
      token: "",
      estado: "inactivo",
    },
  });

  useEffect(() => {
    const load = async () => {
      try {
        const config = await userService.getMyBotConfig();
        reset({
          plataforma: config.plataforma,
          token: config.token ?? "",
          estado: config.estado,
        });
      } catch (error: any) {
        Alert.alert("Error", error?.response?.data?.detail || "No se pudo cargar la configuración");
      }
    };

    load();
  }, [reset]);

  const onSubmit = async (values: BotConfigUpdatePayload) => {
    try {
      await userService.updateMyBotConfig(values);
      Alert.alert("Configuración guardada", "Se actualizó la integración del bot externo.");
      router.back();
    } catch (error: any) {
      Alert.alert("Error", error?.response?.data?.detail || "No se pudo guardar la configuración");
    }
  };

  return (
    <Screen>
      <View style={styles.header}>
        <Text style={styles.title}>Bot Externo</Text>
        <Text style={styles.subtitle}>Conecta tu bot para automatizar tareas.</Text>
      </View>

      <View style={styles.card}>
        <Controller
          control={control}
          name="plataforma"
          render={({ field: { onChange, value } }) => (
            <OptionChipGroup
              label="Plataforma"
              options={PLATFORM_OPTIONS}
              selected={value}
              onSelect={onChange}
            />
          )}
        />

        <Controller
          control={control}
          name="estado"
          render={({ field: { onChange, value } }) => (
            <OptionChipGroup
              label="Estado"
              options={STATUS_OPTIONS}
              selected={value}
              onSelect={onChange}
            />
          )}
        />

        <Controller
          control={control}
          name="token"
          render={({ field: { onChange, value } }) => (
            <AppInput
              label="Token del bot"
              placeholder="Pega aquí el token"
              autoCapitalize="none"
              value={value ?? ""}
              onChangeText={onChange}
            />
          )}
        />
      </View>

      <AppButton
        title="Guardar configuración"
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
});
