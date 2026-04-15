import AsyncStorage from "@react-native-async-storage/async-storage";

const TOKEN_KEY = "lia_access_token";

export const storage = {
  async getToken() {
    return AsyncStorage.getItem(TOKEN_KEY);
  },

  async setToken(token: string) {
    return AsyncStorage.setItem(TOKEN_KEY, token);
  },

  async removeToken() {
    return AsyncStorage.removeItem(TOKEN_KEY);
  },
};