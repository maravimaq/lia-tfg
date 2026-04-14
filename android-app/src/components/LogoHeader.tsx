import React from "react";
import { Image, StyleSheet, Text, View } from "react-native";
import { Colors } from "@/src/constants/colors";

type Props = {
  title: string;
  subtitle?: string;
};

export default function LogoHeader({ title, subtitle }: Props) {
  return (
    <View style={styles.container}>
      <Image
        source={require("../../assets/images/lia-logo.png")}
        style={styles.logo}
        resizeMode="contain"
      />
      <Text style={styles.brand}>LIA</Text>
      <Text style={styles.title}>{title}</Text>
      {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: "center",
    marginTop: 18,
    marginBottom: 24,
  },
  logo: {
    width: 306,
    height: 306,
    marginBottom: 8,
  },
  brand: {
    fontSize: 34,
    fontWeight: "900",
    color: Colors.title,
    letterSpacing: 1,
  },
  title: {
    marginTop: 8,
    fontSize: 22,
    fontWeight: "800",
    color: Colors.primary,
  },
  subtitle: {
    marginTop: 8,
    textAlign: "center",
    color: Colors.text,
    fontSize: 15,
    lineHeight: 22,
    paddingHorizontal: 10,
  },
});