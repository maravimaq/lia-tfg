import React, { useMemo, useState } from "react";
import {
  Alert,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Link, router } from "expo-router";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";

import Screen from "@/src/components/Screen";
import AppInput from "@/src/components/AppInput";
import AppButton from "@/src/components/AppButton";
import LogoHeader from "@/src/components/LogoHeader";
import LegalModal from "@/src/components/LegalModal";
import { useAuth } from "@/src/hooks/useAuth";
import { Colors } from "@/src/constants/colors";

const schema = z
  .object({
    nombre_usuario: z.string().min(3, "Mínimo 3 caracteres"),
    nombre_completo: z.string().min(3, "Introduce tu nombre completo"),
    email: z.string().email("Introduce un email válido"),
    telefono: z.string().optional(),
    contrasena: z.string().min(8, "La contraseña debe tener al menos 8 caracteres"),
    confirmarContrasena: z.string().min(8, "Confirma la contraseña"),
  })
  .refine((data) => data.contrasena === data.confirmarContrasena, {
    message: "Las contraseñas no coinciden",
    path: ["confirmarContrasena"],
  });

type FormData = z.infer<typeof schema>;

export default function SignUpScreen() {
  const { signUp } = useAuth();

  const [termsVisible, setTermsVisible] = useState(false);
  const [privacyVisible, setPrivacyVisible] = useState(false);
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [acceptedPrivacy, setAcceptedPrivacy] = useState(false);

  const {
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      nombre_usuario: "",
      nombre_completo: "",
      email: "",
      telefono: "",
      contrasena: "",
      confirmarContrasena: "",
    },
  });

  const termsContent = useMemo(
    () => [
      "1. Finalidad del servicio. LIA es una aplicación pensada para ayudar al usuario a gestionar listas de la compra y otras funciones relacionadas con las compras.",
      "2. Uso responsable. El usuario se compromete a utilizar la aplicación de forma lícita, respetuosa y sin intentar dañar, bloquear o acceder de forma no autorizada a cuentas, datos o servicios.",
      "3. Cuenta de usuario. El usuario es responsable de la veracidad de los datos facilitados en el registro y de mantener la confidencialidad de sus credenciales de acceso.",
      "4. Disponibilidad. Se intentará mantener la aplicación disponible, pero pueden producirse interrupciones temporales por mantenimiento, mejoras técnicas o incidencias no previstas.",
      "5. Cambios en el servicio. Algunas funcionalidades pueden modificarse, mejorarse o retirarse si resulta necesario para el correcto funcionamiento del sistema.",
      "6. Suspensión o cierre de cuenta. La cuenta podrá suspenderse temporalmente en casos de uso fraudulento, suplantación, intento de acceso no autorizado o incumplimiento grave de estas condiciones.",
      "7. Baja voluntaria. El usuario podrá solicitar la desactivación o eliminación de su cuenta a través de las opciones disponibles en la aplicación o por los canales habilitados.",
      "8. Limitación razonable. La aplicación se ofrece como herramienta de apoyo y no garantiza resultados económicos exactos, disponibilidad de productos o precios idénticos a los de terceros.",
      "9. Contacto. Para dudas o incidencias, el usuario podrá utilizar las vías de soporte mostradas en la propia aplicación.",
    ],
    []
  );

  const privacyContent = useMemo(
    () => [
      "1. Datos recogidos. LIA puede tratar datos como nombre de usuario, nombre completo, correo electrónico, teléfono, preferencias de uso y datos estrictamente necesarios para el funcionamiento de la cuenta.",
      "2. Finalidad del tratamiento. Los datos se usan para permitir el acceso a la aplicación, gestionar el perfil del usuario, guardar preferencias y ofrecer las funcionalidades principales del servicio.",
      "3. Minimización. Solo se solicitarán los datos necesarios para prestar el servicio y mejorar la experiencia de uso dentro del alcance del proyecto.",
      "4. Conservación. Los datos se conservarán mientras la cuenta permanezca activa o mientras exista una base legítima para su mantenimiento, y después durante el tiempo imprescindible para atender obligaciones técnicas o legales.",
      "5. Seguridad. Se adoptarán medidas técnicas y organizativas razonables para proteger los datos frente a accesos no autorizados, alteración, pérdida o destrucción.",
      "6. Cesión de datos. Los datos no se venderán ni se cederán a terceros con fines comerciales. Solo podrán comunicarse cuando sea estrictamente necesario para la prestación técnica del servicio o por obligación legal.",
      "7. Derechos del usuario. El usuario puede solicitar el acceso, rectificación, actualización, desactivación o eliminación de sus datos personales según las opciones disponibles en la aplicación.",
      "8. Cookies o tecnologías similares. En caso de utilizarse en determinadas plataformas, se limitarán a lo necesario para el funcionamiento básico, seguridad o mejora técnica del servicio.",
      "9. Cambios en esta política. Si se realizan modificaciones relevantes, se informará al usuario por medios razonables dentro de la propia aplicación.",
    ],
    []
  );

  const onSubmit = async (values: FormData) => {
    if (!acceptedTerms || !acceptedPrivacy) {
      Alert.alert(
        "Consentimiento obligatorio",
        "Debes aceptar los Términos de Servicio y la Política de Privacidad para crear tu cuenta."
      );
      return;
    }

    try {
      await signUp({
        nombre_usuario: values.nombre_usuario,
        nombre_completo: values.nombre_completo,
        email: values.email,
        telefono: values.telefono || undefined,
        contrasena: values.contrasena,
      });

      router.replace("/(protected)/profile");
    } catch (error: any) {
      Alert.alert(
        "Error al registrarte",
        error?.response?.data?.detail || "No se pudo crear la cuenta"
      );
    }
  };

  return (
    <Screen>
      <LogoHeader
        title="Crear una cuenta"
        subtitle="Introduce tus datos para registrarte en la aplicación."
      />

      <View style={styles.card}>
        <Controller
          control={control}
          name="nombre_usuario"
          render={({ field: { onChange, value } }) => (
            <AppInput
              placeholder="Nombre de usuario"
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
              placeholder="Nombre completo"
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
          name="telefono"
          render={({ field: { onChange, value } }) => (
            <AppInput
              placeholder="Teléfono"
              keyboardType="phone-pad"
              value={value}
              onChangeText={onChange}
              error={errors.telefono?.message}
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

        <Controller
          control={control}
          name="confirmarContrasena"
          render={({ field: { onChange, value } }) => (
            <AppInput
              placeholder="Confirmar contraseña"
              secureTextEntry
              value={value}
              onChangeText={onChange}
              error={errors.confirmarContrasena?.message}
            />
          )}
        />

        <View style={styles.checkboxGroup}>
          <Pressable
            style={styles.checkboxRow}
            onPress={() => setAcceptedTerms((prev) => !prev)}
          >
            <View style={[styles.checkbox, acceptedTerms && styles.checkboxActive]}>
              {acceptedTerms ? <Text style={styles.checkmark}>✓</Text> : null}
            </View>

            <Text style={styles.checkboxText}>
              He leído y acepto los{" "}
              <Text style={styles.linkInline} onPress={() => setTermsVisible(true)}>
                Términos de Servicio
              </Text>
            </Text>
          </Pressable>

          <Pressable
            style={styles.checkboxRow}
            onPress={() => setAcceptedPrivacy((prev) => !prev)}
          >
            <View style={[styles.checkbox, acceptedPrivacy && styles.checkboxActive]}>
              {acceptedPrivacy ? <Text style={styles.checkmark}>✓</Text> : null}
            </View>

            <Text style={styles.checkboxText}>
              He leído y acepto la{" "}
              <Text style={styles.linkInline} onPress={() => setPrivacyVisible(true)}>
                Política de Privacidad
              </Text>
            </Text>
          </Pressable>
        </View>

        <AppButton
          title="Crear cuenta"
          onPress={handleSubmit(onSubmit)}
          loading={isSubmitting}
          style={{ marginTop: 10 }}
        />

        <View style={styles.footerRow}>
          <Text style={styles.footerText}>¿Ya tienes una cuenta?</Text>
          <Link href="/(auth)/sign-in" asChild>
            <Text style={styles.footerLink}> Inicia sesión aquí</Text>
          </Link>
        </View>
      </View>

      <LegalModal
        visible={termsVisible}
        title="Términos de Servicio"
        content={termsContent}
        onClose={() => setTermsVisible(false)}
      />

      <LegalModal
        visible={privacyVisible}
        title="Política de Privacidad"
        content={privacyContent}
        onClose={() => setPrivacyVisible(false)}
      />
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
  checkboxGroup: {
    marginTop: 6,
    marginBottom: 10,
    gap: 12,
  },
  checkboxRow: {
    flexDirection: "row",
    alignItems: "flex-start",
  },
  checkbox: {
    width: 22,
    height: 22,
    borderRadius: 7,
    borderWidth: 1.5,
    borderColor: Colors.border,
    backgroundColor: Colors.surface,
    marginTop: 1,
    marginRight: 10,
    alignItems: "center",
    justifyContent: "center",
  },
  checkboxActive: {
    backgroundColor: Colors.primary,
    borderColor: Colors.primary,
  },
  checkmark: {
    color: Colors.white,
    fontWeight: "900",
    fontSize: 13,
  },
  checkboxText: {
    flex: 1,
    color: Colors.textMuted,
    fontSize: 13,
    lineHeight: 20,
  },
  linkInline: {
    color: Colors.primary,
    fontWeight: "800",
    textDecorationLine: "underline",
  },
  dividerWrap: {
    marginTop: 18,
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