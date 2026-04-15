import React from "react";
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Colors } from "@/src/constants/colors";

export default function Screen({
  children,
  scroll = true,
}: {
  children: React.ReactNode;
  scroll?: boolean;
}) {
  const content = (
    <View style={styles.content}>
      <View style={styles.blobTopLeft} />
      <View style={styles.blobTopRight} />
      <View style={styles.blobBottom} />
      {children}
    </View>
  );

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        {scroll ? (
          <ScrollView
            contentContainerStyle={styles.scroll}
            keyboardShouldPersistTaps="handled"
            showsVerticalScrollIndicator={false}
          >
            {content}
          </ScrollView>
        ) : (
          content
        )}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  flex: {
    flex: 1,
  },
  scroll: {
    flexGrow: 1,
  },
  content: {
    flex: 1,
    paddingHorizontal: 22,
    paddingVertical: 20,
    backgroundColor: Colors.background,
    overflow: "hidden",
  },
  blobTopLeft: {
    position: "absolute",
    top: -40,
    left: -40,
    width: 180,
    height: 180,
    borderRadius: 90,
    backgroundColor: Colors.cyan,
    opacity: 0.18,
  },
  blobTopRight: {
    position: "absolute",
    top: 40,
    right: -60,
    width: 180,
    height: 180,
    borderRadius: 90,
    backgroundColor: Colors.lightPurple,
    opacity: 0.15,
  },
  blobBottom: {
    position: "absolute",
    bottom: -80,
    left: 40,
    width: 240,
    height: 240,
    borderRadius: 120,
    backgroundColor: Colors.softBlue,
    opacity: 0.18,
  },
});