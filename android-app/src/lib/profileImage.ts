import AsyncStorage from "@react-native-async-storage/async-storage";

const PROFILE_IMAGE_KEY = "lia_profile_image";

export const profileImageStorage = {
  async get() {
    return AsyncStorage.getItem(PROFILE_IMAGE_KEY);
  },

  async set(uri: string) {
    return AsyncStorage.setItem(PROFILE_IMAGE_KEY, uri);
  },

  async remove() {
    return AsyncStorage.removeItem(PROFILE_IMAGE_KEY);
  },
};