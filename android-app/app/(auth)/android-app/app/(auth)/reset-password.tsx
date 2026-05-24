import React, { useEffect } from "react";
import { Alert, Pressable, StyleSheet, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";

import Screen from "@/src/components/Screen";
import AppInput from "@/src/components/AppInput";
import AppButton from "@/src/components/AppButton";
import { Colors } from "@/src/constants/colors";
import { authService } from "@/src/services/auth";

const schema = z
  .object({
    token: z.string().min(1, "Introduce el token de recuperación"),
    nueva_contrasena: z.string().min(8, "La contraseña debe tener al menos 8 caracteres"),
    confirmar_contrasena: z.string().min(8, "Confirma la contraseña"),
  })
  .refine((values) => values.nueva_contrasena === values.confirmar_contrasena, {
    message: "Las contraseñas no coinciden",
    path: ["confirmar_contrasena"],
  });

type FormData = z.infer<typeof schema>;

function goBackToSignIn() {
  if (router.canGoBack()) {
    router.back();
    return;
  }

  router.replace("/(auth)/sign-in");
}

export default function ResetPasswordScreen() {
  const params = useLocalSearchParams<{ token?: string }>();
  const tokenFromParams = typeof params.token === "string" ? params.token : "";

  const {
    control,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      token: tokenFromParams,
      nueva_contrasena: "",
      confirmar_contrasena: "",
    },
  });

  useEffect(() => {
    if (tokenFromParams) {
      setValue("token", tokenFromParams);
    }
  }, [setValue, tokenFromParams]);

  const onSubmit = async (values: FormData) => {
    try {
      await authService.resetPassword({
        token: values.token.trim(),
        nueva_contrasena: values.nueva_contrasena,
      });
      Alert.alert("Contraseña actualizada", "Ya puedes iniciar sesión con tu nueva contraseña.");
      router.replace("/(auth)/sign-in");
    } catch (error: any) {
      Alert.alert("Error", error?.response?.data?.detail || "No se pudo restablecer la contraseña");
    }
  };

  return (
    <Screen>
      <Pressable onPress={goBackToSignIn} style={styles.backButton} hitSlop={10}>
        <Text style={styles.backButtonText}>← Volver</Text>
      </Pressable>

      <View style={styles.header}>
        <Text style={styles.brand}>LIA</Text>
        <Text style={styles.title}>Nueva contraseña</Text>
        <Text style={styles.subtitle}>
          {tokenFromParams
            ? "Introduce y confirma tu nueva contraseña."
            : "Pega el token del correo e introduce tu nueva contraseña."}
        </Text>
      </View>

      {!tokenFromParams ? (
        <Controller
          control={control}
          name="token"
          render={({ field: { onChange, value } }) => (
            <AppInput
              label="Token de recuperación"
              placeholder="Pega aquí el token recibido por email"
              autoCapitalize="none"
              autoCorrect={false}
              value={value}
              onChangeText={onChange}
              error={errors.token?.message}
            />
          )}
        />
      ) : null}

      <Controller
        control={control}
        name="nueva_contrasena"
        render={({ field: { onChange, value } }) => (
          <AppInput
            placeholder="Nueva contraseña"
            secureTextEntry
            value={value}
            onChangeText={onChange}
            error={errors.nueva_contrasena?.message}
          />
        )}
      />

      <Controller
        control={control}
        name="confirmar_contrasena"
        render={({ field: { onChange, value } }) => (
          <AppInput
            placeholder="Confirmar contraseña"
            secureTextEntry
            value={value}
            onChangeText={onChange}
            error={errors.confirmar_contrasena?.message}
          />
        )}
      />

      <AppButton title="Guardar contraseña" onPress={handleSubmit(onSubmit)} loading={isSubmitting} />
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
});