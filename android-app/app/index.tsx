import { Redirect } from "expo-router";
import { ActivityIndicator, View } from "react-native";
import { useAuth } from "@/src/hooks/useAuth";
import { Colors } from "@/src/constants/colors";

export default function Index() {
  const { token, loading } = useAuth();

  if (loading) {
    return (
      <View
        style={{
          flex: 1,
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: Colors.background,
        }}
      >
        <ActivityIndicator color={Colors.primary} size="large" />
      </View>
    );
  }

  if (token) {
    return <Redirect href="/(protected)/profile" />;
  }

  return <Redirect href="/(auth)/sign-in" />;
}