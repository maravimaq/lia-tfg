import React from "react";
import { Alert, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import { Controller, useForm } from "react-hook-form";

import Screen from "@/src/components/Screen";
import AppButton from "@/src/components/AppButton";
import AppInput from "@/src/components/AppInput";
import { Colors } from "@/src/constants/colors";
import { AccountActionRequestPayload } from "@/src/types/user";
import { userService } from "@/src/services/user";

type FormData = {
  motivo: string;
};

export default function AccountActionScreen() {
  const {
    control,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm<FormData>({
    defaultValues: {
      motivo: "",
    },
  });

  const submitRequest = async (tipo: AccountActionRequestPayload["tipo"], motivo: string) => {
    try {
      const payload: AccountActionRequestPayload = {
        tipo,
        motivo: motivo.trim() ? motivo.trim() : undefined,
      };

      const response = await userService.requestAccountAction(payload);
      Alert.alert(
        "Solicitud enviada",
        `Tu solicitud (${response.tipo}) quedó registrada con estado ${response.estado}.`
      );
      router.back();
    } catch (error: any) {
      Alert.alert("Error", error?.response?.data?.detail || "No se pudo enviar la solicitud");
    }
  };

  return (
    <Screen>
      <View style={styles.header}>
        <Text style={styles.title}>Gestión de cuenta</Text>
        <Text style={styles.subtitle}>
          Solicita desactivación temporal o eliminación definitiva de tu cuenta.
        </Text>
      </View>

      <View style={styles.card}>
        <Controller
          control={control}
          name="motivo"
          render={({ field: { onChange, value } }) => (
            <AppInput
              label="Motivo (opcional)"
              placeholder="Cuéntanos por qué deseas esta acción"
              multiline
              numberOfLines={4}
              style={styles.textArea}
              value={value}
              onChangeText={onChange}
            />
          )}
        />

        <AppButton
          title="Solicitar desactivación"
          variant="secondary"
          onPress={handleSubmit(({ motivo }) => submitRequest("desactivacion", motivo))}
          loading={isSubmitting}
          style={{ marginTop: 8 }}
        />

        <AppButton
          title="Solicitar eliminación"
          variant="danger"
          onPress={handleSubmit(({ motivo }) => submitRequest("eliminacion", motivo))}
          loading={isSubmitting}
          style={{ marginTop: 12 }}
        />
      </View>

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
  textArea: {
    minHeight: 110,
    textAlignVertical: "top",
    paddingTop: 12,
  },
});
