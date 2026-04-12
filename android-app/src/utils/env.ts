const LOCAL_IP = "TU_IP_LOCAL";

export const API_BASE_URL = __DEV__
  ? `http://${LOCAL_IP}:8000`
  : "https://api.lia.com";
  export const API_TIMEOUT = 10000;