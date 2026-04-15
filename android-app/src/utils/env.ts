const LOCAL_IP = "192.168.0.19";

export const API_BASE_URL = __DEV__
  ? `http://127.0.0.1:8000`
  : "https://api.lia.com";
  export const API_TIMEOUT = 10000;