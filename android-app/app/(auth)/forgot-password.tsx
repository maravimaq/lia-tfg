import React, { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
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
type StatusMessage = { type: "success" | "error"; text: string } | null;

function goBackToSignIn() {
  if (router.canGoBack()) {
    router.back();
    return;
  }

  router.replace("/(auth)/sign-in");
}

export default function ForgotPasswordScreen() {
  const [statusMessage, setStatusMessage] = useState<StatusMessage>(null);
  const [sentEmail, setSentEmail] = useState("");

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
    const normalizedEmail = values.email.trim().toLowerCase();
    setStatusMessage(null);

    try {
      const response = await authService.forgotPassword({ email: normalizedEmail });
      setSentEmail(normalizedEmail);
      setStatusMessage({
        type: "success",
        text:
          response?.message ||
          "Si el correo existe, recibirás instrucciones para restablecer tu contraseña.",
      });
    } catch (error: any) {
      setStatusMessage({
        type: "error",
        text:
          error?.response?.data?.detail ||
          error?.message ||
          "No se pudo procesar la solicitud. Comprueba la conexión con el servidor.",
      });
    }
  };

  return (
    <Screen>
      <Pressable onPress={goBackToSignIn} style={styles.backButton} hitSlop={10}>
        <Text style={styles.backButtonText}>← Volver</Text>
      </Pressable>

      <View style={styles.header}>
        <Text style={styles.brand}>LIA</Text>
        <Text style={styles.title}>Recuperar contraseña</Text>
        <Text style={styles.subtitle}>
          {statusMessage?.type === "success"
            ? `Te enviamos una contraseña temporal a ${sentEmail}. Úsala para iniciar sesión y cámbiala dentro de tu perfil.`
            : "Introduce tu email para recibir una contraseña temporal."}
        </Text>
      </View>

      <Controller
        control={control}
        name="email"
        render={({ field: { onChange, value } }) => (
          <AppInput
            placeholder="Correo electrónico"
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="email-address"
            textContentType="emailAddress"
            value={value}
            onChangeText={(text) => {
              setStatusMessage(null);
              onChange(text);
            }}
            error={errors.email?.message}
          />
        )}
      />

      {statusMessage ? (
        <View
          style={[
            styles.messageBox,
            statusMessage.type === "success" ? styles.successBox : styles.errorBox,
          ]}
        >
          <Text
            style={[
              styles.messageText,
              statusMessage.type === "success" ? styles.successText : styles.errorText,
            ]}
          >
            {statusMessage.text}
          </Text>
        </View>
      ) : null}

      <AppButton
        title={isSubmitting ? "Enviando..." : "Enviar contraseña temporal"}
        onPress={handleSubmit(onSubmit)}
        loading={isSubmitting}
      />

      {statusMessage?.type === "success" ? (
        <AppButton
          title="Volver a iniciar sesión"
          variant="ghost"
          onPress={goBackToSignIn}
          style={styles.signInButton}
        />
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  backButton: {
    alignSelf: "flex-start",
    paddingVertical: 8,
    paddingHorizontal: 4,
    marginBottom: 8,
  },
  backButtonText: {
    color: Colors.title,
    fontSize: 16,
    fontWeight: "800",
  },
  header: {
    marginTop: 20,
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
    lineHeight: 22,
  },
  messageBox: {
    borderRadius: 14,
    padding: 12,
    marginBottom: 14,
    borderWidth: 1,
  },
  successBox: {
    backgroundColor: "#eefbf2",
    borderColor: Colors.success,
  },
  errorBox: {
    backgroundColor: "#fff1f2",
    borderColor: Colors.danger,
  },
  messageText: {
    fontSize: 14,
    lineHeight: 20,
    fontWeight: "600",
  },
  successText: {
    color: Colors.success,
  },
  errorText: {
    color: Colors.danger,
  },
  signInButton: {
    marginTop: 10,
  },
});