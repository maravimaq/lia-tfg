import React from "react";
import { Alert, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";

import Screen from "@/src/components/Screen";
import AppInput from "@/src/components/AppInput";
import AppButton from "@/src/components/AppButton";
import { authService } from "@/src/services/auth";
import { Colors } from "@/src/constants/colors";

const schema = z.object({
  email: z.string().email("Introduce un email válido"),
});

type FormData = z.infer<typeof schema>;

export default function ForgotPasswordScreen() {
  const {
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      email: "",
    },
  });

  const onSubmit = async (values: FormData) => {
    try {
      await authService.forgotPassword(values);
      Alert.alert(
        "Solicitud enviada",
        "Si el correo existe, recibirás instrucciones para restablecer tu contraseña."
      );
      router.back();
    } catch (error: any) {
      Alert.alert(
        "Error",
        error?.response?.data?.detail || "No se pudo procesar la solicitud"
      );
    }
  };

  return (
    <Screen>
      <View style={styles.header}>
        <Text style={styles.brand}>LIA</Text>
        <Text style={styles.title}>Recuperar contraseña</Text>
        <Text style={styles.subtitle}>
          Introduce tu email para recibir el enlace de recuperación.
        </Text>
      </View>

      <Controller
        control={control}
        name="email"
        render={({ field: { onChange, value } }) => (
          <AppInput
            placeholder="Correo electrónico"
            autoCapitalize="none"
            keyboardType="email-address"
            value={value}
            onChangeText={onChange}
            error={errors.email?.message}
          />
        )}
      />

      <AppButton
        title="Enviar enlace"
        onPress={handleSubmit(onSubmit)}
        loading={isSubmitting}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    marginTop: 40,
    marginBottom: 24,
    alignItems: "center",
  },
  brand: {
    fontSize: 42,
    fontWeight: "800",
    color: Colors.black,
  },
  title: {
    marginTop: 10,
    fontSize: 18,
    fontWeight: "700",
    color: Colors.text,
  },
  subtitle: {
    marginTop: 8,
    color: Colors.textMuted,
    textAlign: "center",
  },
});