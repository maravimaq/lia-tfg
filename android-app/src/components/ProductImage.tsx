import { useEffect, useMemo, useState } from "react";
import {
  Image,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { AppColors } from "@/src/constants/colors";
import { useAppTheme } from "@/src/hooks/useAppTheme";

type ProductImageProps = {
  uri?: string | null;
  productName?: string;
  size?: number;
};

export function ProductImage({
  uri,
  productName = "Producto",
  size = 72,
}: ProductImageProps) {
  const { colors } = useAppTheme();
  const styles = useMemo(() => createStyles(colors), [colors]);

  const [hasError, setHasError] = useState(false);

  const imageUri = uri?.trim() || null;

  useEffect(() => {
    setHasError(false);
  }, [imageUri]);

  if (!imageUri || hasError) {
    return (
      <View
        style={[
          styles.container,
          {
            width: size,
            height: size,
          },
        ]}
        accessibilityLabel={`Sin imagen para ${productName}`}
      >
        <Text style={styles.placeholderIcon}>▧</Text>
      </View>
    );
  }

  return (
    <View
      style={[
        styles.container,
        {
          width: size,
          height: size,
        },
      ]}
    >
      <Image
        source={{ uri: imageUri }}
        style={styles.image}
        resizeMode="contain"
        onError={() => setHasError(true)}
        accessibilityLabel={`Imagen de ${productName}`}
      />
    </View>
  );
}

const createStyles = (colors: AppColors) =>
  StyleSheet.create({
    container: {
      borderRadius: 12,
      backgroundColor: colors.surface,
      borderWidth: 1,
      borderColor: colors.border,
      overflow: "hidden",
      alignItems: "center",
      justifyContent: "center",
    },
    image: {
      width: "100%",
      height: "100%",
    },
    placeholderIcon: {
      fontSize: 24,
      color: colors.textMuted,
      fontWeight: "700",
    },
  });