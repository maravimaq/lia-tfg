export const lightColors = {
  blue: "#80BAF5",
  purple: "#B383F5",
  primary: "#7F83F5",
  cyan: "#81ECF5",
  lightPurple: "#DB7BF4",
  softBlue: "#C1CCF5",

  background: "#F8FAFF",
  backgroundAlt: "#EEF4FF",
  surface: "#FFFFFF",
  card: "#F4F6FD",
  border: "#DCE3F7",

  text: "#20243A",
  textMuted: "#6E7594",
  muted: "#6E7594",
  title: "#2C3154",

  black: "#111111",
  white: "#FFFFFF",

  success: "#2E9E6F",
  danger: "#D9534F",
};

export const darkColors: typeof lightColors = {
  blue: "#80BAF5",
  purple: "#B383F5",
  primary: "#9A9DFF",
  cyan: "#4DD9E6",
  lightPurple: "#C36CF4",
  softBlue: "#2A315F",

  background: "#0F1220",
  backgroundAlt: "#171B2E",
  surface: "#1B2035",
  card: "#232842",
  border: "#343B5F",

  text: "#E7EAF7",
  textMuted: "#A8AEC9",
  muted: "#A8AEC9",
  title: "#FFFFFF",

  black: "#050711",
  white: "#FFFFFF",

  success: "#54C795",
  danger: "#FF6B6B",
};

export type AppColors = typeof lightColors;

export function getColorsForMode(isDarkMode: boolean): AppColors {
  return isDarkMode ? darkColors : lightColors;
}

// Mantiene compatibilidad con pantallas que todavía importan Colors directamente.
// Es la paleta clara por defecto. Las pantallas adaptadas al modo oscuro deben usar useAppTheme().
export const Colors = lightColors;
