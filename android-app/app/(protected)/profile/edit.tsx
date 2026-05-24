import React from "react";
import { Alert, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";

import Screen from "@/src/components/Screen";
import AppInput from "@/src/components/AppInput";
import AppButton from "@/src/components/AppButton";
import { useAuth } from "@/src/hooks/useAuth";
import { userService } from "@/src/services/user";
import { Colors } from "@/src/constants/colors";

const schema = z.object({
  nombre_usuario: z.string().min(3, "Mínimo 3 caracteres"),
  nombre_completo: z.string().min(3, "Introduce tu nombre completo"),
  email: z.string().email("Introduce un email válido"),
  telefono: z.string().optional(),
});

type FormData = z.infer<typeof schema>;

export default function EditProfileScreen() {
  const { user, signOut } = useAuth();

  const {
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      nombre_usuario: user?.nombre_usuario || "",
      nombre_completo: user?.nombre_completo || "",
      email: user?.email || "",
      telefono: user?.telefono || "",
    },
  });

  const onSubmit = async (values: FormData) => {
    try {
      const oldEmail = user?.email;
      const emailChanged = oldEmail !== values.email;

      await userService.updateMe(values);

      if (emailChanged) {
        await signOut();
        Alert.alert(
          "Correo actualizado",
          "Tu correo se ha actualizado. Inicia sesión de nuevo con el nuevo correo."
        );
        router.replace("/(auth)/sign-in");
        return;
      }

      Alert.alert("Perfil actualizado", "Tus datos se han actualizado correctamente.");
      router.replace("/(protected)/profile");
    } catch (error: any) {
      Alert.alert(
        "Error",
        error?.response?.data?.detail || error?.message || "No se pudo actualizar el perfil"
      );
    }
  };

  return (
    <Screen>
      <View style={styles.header}>
        <Text style={styles.title}>Editar perfil</Text>
        <Text style={styles.subtitle}>Actualiza tu información personal</Text>
      </View>

      <View style={styles.card}>
        <Controller
          control={control}
          name="nombre_usuario"
          render={({ field: { onChange, value } }) => (
            <AppInput
              label="Nombre de usuario"
              value={value}
              onChangeText={onChange}
              error={errors.nombre_usuario?.message}
            />
          )}
        />

        <Controller
          control={control}
          name="nombre_completo"
          render={({ field: { onChange, value } }) => (
            <AppInput
              label="Nombre completo"
              value={value}
              onChangeText={onChange}
              error={errors.nombre_completo?.message}
            />
          )}
        />

        <Controller
          control={control}
          name="email"
          render={({ field: { onChange, value } }) => (
            <AppInput
              label="Correo electrónico"
              value={value}
              onChangeText={onChange}
              autoCapitalize="none"
              keyboardType="email-address"
              error={errors.email?.message}
            />
          )}
        />

        <Controller
          control={control}
          name="telefono"
          render={({ field: { onChange, value } }) => (
            <AppInput
              label="Teléfono"
              value={value}
              onChangeText={onChange}
              keyboardType="phone-pad"
              error={errors.telefono?.message}
            />
          )}
        />
      </View>

      <AppButton
        title="Guardar cambios"
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