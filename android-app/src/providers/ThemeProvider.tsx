import AsyncStorage from "@react-native-async-storage/async-storage";
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  AppColors,
  getColorsForMode,
} from "@/src/constants/colors";
import { preferencesService } from "@/src/services/preferences";

const THEME_STORAGE_KEY = "lia_theme_mode";

type ThemeContextType = {
  isDarkMode: boolean;
  colors: AppColors;
  setDarkMode: (enabled: boolean) => Promise<void>;
  refreshThemeFromPreferences: () => Promise<void>;
};

const ThemeContext = createContext<ThemeContextType | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [isDarkMode, setIsDarkMode] = useState(false);

  const persistDarkMode = useCallback(async (enabled: boolean) => {
    setIsDarkMode(enabled);
    await AsyncStorage.setItem(THEME_STORAGE_KEY, enabled ? "dark" : "light");
  }, []);

  useEffect(() => {
    const loadCachedTheme = async () => {
      try {
        const storedTheme = await AsyncStorage.getItem(THEME_STORAGE_KEY);
        if (storedTheme === "dark") {
          setIsDarkMode(true);
        }
      } catch (error) {
        console.log("No se pudo cargar el tema guardado:", error);
      }
    };

    loadCachedTheme();
  }, []);

  const refreshThemeFromPreferences = useCallback(async () => {
    try {
      const preferences = await preferencesService.getMyPreferences();
      await persistDarkMode(Boolean(preferences.modo_oscuro));
    } catch (error) {
      console.log("No se pudo sincronizar el tema con preferencias:", error);
    }
  }, [persistDarkMode]);

  const colors = useMemo(
    () => getColorsForMode(isDarkMode),
    [isDarkMode]
  );

  const value = useMemo(
    () => ({
      isDarkMode,
      colors,
      setDarkMode: persistDarkMode,
      refreshThemeFromPreferences,
    }),
    [colors, isDarkMode, persistDarkMode, refreshThemeFromPreferences]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useThemeContext() {
  const context = useContext(ThemeContext);

  if (!context) {
    throw new Error("useThemeContext debe usarse dentro de ThemeProvider");
  }

  return context;
}
