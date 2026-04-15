import React from "react";
import { Alert, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";

import Screen from "@/src/components/Screen";
import AppInput from "@/src/components/AppInput";
import AppButton from "@/src/components/AppButton";
import { userService } from "@/src/services/user";
import { useAuth } from "@/src/hooks/useAuth";
import { Colors } from "@/src/constants/colors";

const schema = z
  .object({
    contrasena_actual: z.string().min(1, "Introduce tu contraseña actual"),
    nueva_contrasena: z.string().min(8, "La nueva contraseña debe tener al menos 8 caracteres"),
    confirmarNuevaContrasena: z.string().min(8, "Confirma la nueva contraseña"),
  })
  .refine((data) => data.nueva_contrasena === data.confirmarNuevaContrasena, {
    message: "Las contraseñas no coinciden",
    path: ["confirmarNuevaContrasena"],
  });

type FormData = z.infer<typeof schema>;

export default function ChangePasswordScreen() {
  const { signOut } = useAuth();

  const {
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
    reset,
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      contrasena_actual: "",
      nueva_contrasena: "",
      confirmarNuevaContrasena: "",
    },
  });

  const onSubmit = async (values: FormData) => {
    try {
      await userService.changePassword({
        contrasena_actual: values.contrasena_actual,
        nueva_contrasena: values.nueva_contrasena,
      });

      reset();
      await signOut();

      Alert.alert(
        "Contraseña actualizada",
        "Tu contraseña se ha actualizado. Inicia sesión de nuevo con la nueva contraseña."
      );
      router.replace("/(auth)/sign-in");
    } catch (error: any) {
      Alert.alert(
        "Error",
        error?.response?.data?.detail || error?.message || "No se pudo cambiar la contraseña"
      );
    }
  };

  return (
    <Screen>
      <View style={styles.header}>
        <Text style={styles.title}>Cambiar contraseña</Text>
        <Text style={styles.subtitle}>
          Introduce tu contraseña actual y la nueva contraseña
        </Text>
      </View>

      <View style={styles.card}>
        <Controller
          control={control}
          name="contrasena_actual"
          render={({ field: { onChange, value } }) => (
            <AppInput
              label="Contraseña actual"
              secureTextEntry
              value={value}
              onChangeText={onChange}
              error={errors.contrasena_actual?.message}
            />
          )}
        />

        <Controller
          control={control}
          name="nueva_contrasena"
          render={({ field: { onChange, value } }) => (
            <AppInput
              label="Nueva contraseña"
              secureTextEntry
              value={value}
              onChangeText={onChange}
              error={errors.nueva_contrasena?.message}
            />
          )}
        />

        <Controller
          control={control}
          name="confirmarNuevaContrasena"
          render={({ field: { onChange, value } }) => (
            <AppInput
              label="Confirmar nueva contraseña"
              secureTextEntry
              value={value}
              onChangeText={onChange}
              error={errors.confirmarNuevaContrasena?.message}
            />
          )}
        />
      </View>

      <AppButton
        title="Guardar nueva contraseña"
        onPress={handleSubmit(onSubmit)}
        loading={isSubmitting}
        style={{ marginTop: 18 }}
      />

      <AppButton
        title="Cancelar"
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