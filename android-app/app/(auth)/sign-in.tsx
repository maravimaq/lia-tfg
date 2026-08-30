import React from "react";
import { Alert, StyleSheet, Text, View } from "react-native";
import { Link, router } from "expo-router";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";

import Screen from "@/src/components/Screen";
import AppInput from "@/src/components/AppInput";
import AppButton from "@/src/components/AppButton";
import LogoHeader from "@/src/components/LogoHeader";
import { useAuth } from "@/src/hooks/useAuth";
import { Colors } from "@/src/constants/colors";

const schema = z.object({
  email: z.string().email("Introduce un email válido"),
  contrasena: z.string().min(8, "La contraseña debe tener al menos 8 caracteres"),
});

type FormData = z.infer<typeof schema>;

export default function SignInScreen() {
  const { signIn } = useAuth();

  const {
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      email: "",
      contrasena: "",
    },
  });

  const onSubmit = async (values: FormData) => {
    try {
      await signIn(values);
      router.replace("/(protected)/profile");
    } catch (error: any) {
      Alert.alert(
        "Error al iniciar sesión",
        error?.response?.data?.detail || "No se pudo iniciar sesión"
      );
    }
  };

  return (
    <Screen>
      <LogoHeader
        title="Iniciar sesión"
        subtitle="Accede a tu cuenta para gestionar tus compras y listas."
      />

      <View style={styles.card}>
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

        <Controller
          control={control}
          name="contrasena"
          render={({ field: { onChange, value } }) => (
            <AppInput
              placeholder="Contraseña"
              secureTextEntry
              value={value}
              onChangeText={onChange}
              error={errors.contrasena?.message}
            />
          )}
        />

        <Link href="/(auth)/forgot-password" asChild>
          <Text style={styles.forgot}>¿Has olvidado tu contraseña?</Text>
        </Link>

        <AppButton
          title="Iniciar sesión"
          onPress={handleSubmit(onSubmit)}
          loading={isSubmitting}
          style={{ marginTop: 10 }}
        />

        <View style={styles.footerRow}>
          <Text style={styles.footerText}>¿No tienes una cuenta?</Text>
          <Link href="/(auth)/sign-up" asChild>
            <Text style={styles.footerLink}> Regístrate aquí</Text>
          </Link>
        </View>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "rgba(255,255,255,0.82)",
    borderRadius: 28,
    padding: 20,
    borderWidth: 1,
    borderColor: Colors.border,
    shadowColor: "#A9B6E5",
    shadowOpacity: 0.1,
    shadowRadius: 14,
    shadowOffset: { width: 0, height: 6 },
  },
  forgot: {
    color: Colors.textMuted,
    textAlign: "center",
    marginTop: 4,
    marginBottom: 4,
  },
  dividerWrap: {
    marginTop: 26,
    marginBottom: 16,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  divider: {
    flex: 1,
    height: 1,
    backgroundColor: Colors.border,
  },
  dividerText: {
    color: Colors.textMuted,
    fontSize: 13,
  },
  socialRow: {
    flexDirection: "row",
    gap: 12,
  },
  socialItem: {
    flex: 1,
  },
  footerRow: {
    marginTop: 24,
    flexDirection: "row",
    justifyContent: "center",
    flexWrap: "wrap",
  },
  footerText: {
    color: Colors.textMuted,
  },
  footerLink: {
    color: Colors.primary,
    fontWeight: "800",
  },
});