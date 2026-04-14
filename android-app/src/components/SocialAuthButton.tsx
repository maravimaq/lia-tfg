import React from "react";
import { Image, Pressable, StyleSheet, Text, View } from "react-native";
import { Colors } from "@/src/constants/colors";

type Props = {
  provider: "google" | "apple";
  label: string;
  onPress: () => void;
};

export default function SocialAuthButton({ provider, label, onPress }: Props) {
  const icon =
    provider === "google"
      ? require("../../assets/icons/google.png")
      : require("../../assets/icons/apple.png");

  return (
    <Pressable style={styles.button} onPress={onPress}>
      <View style={styles.iconWrap}>
        <Image source={icon} style={styles.icon} resizeMode="contain" />
      </View>
      <Text style={styles.text}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    minHeight: 54,
    borderRadius: 16,
    backgroundColor: Colors.surface,
    borderWidth: 1,
    borderColor: Colors.border,
    gap: 10,
    shadowColor: "#A9B6E5",
    shadowOpacity: 0.08,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
  },
  iconWrap: {
    width: 24,
    height: 24,
    alignItems: "center",
    justifyContent: "center",
  },
  icon: {
    width: 62,
    height: 62,
  },
  text: {
    color: Colors.title,
    fontWeight: "700",
    fontSize: 15,
  },
});