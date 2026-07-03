import axios from "axios";
import constants from "./constants";

const api = axios.create({
  baseURL: constants.BASE_URL,
  timeout: 12000,
});

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config || {};
    const isNetworkStartupError = !error.response && !config.__arkaiosNoRetry;
    config.__arkaiosRetryCount = config.__arkaiosRetryCount || 0;

    if (isNetworkStartupError && config.__arkaiosRetryCount < 10) {
      config.__arkaiosRetryCount += 1;
      await wait(1000);
      return api(config);
    }

    return Promise.reject(error);
  }
);

export default api;

export const API_KEY_HEADER = {
  headers: {
    'Authorization': 'Api-Key ' + constants.API_KEY,
  }
}
