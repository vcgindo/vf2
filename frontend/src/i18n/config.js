/* eslint-disable import/no-named-as-default-member */
/* eslint-disable no-undef */
import i18n from "i18next";
import { initReactI18next } from "react-i18next";

i18n.use(initReactI18next).init({
  fallbackLng: "en",
  lng: "en",
  resources: {
    en: {
      translations: require("./locales/en/translations.json"),
    },
    es: {
      translations: require("./locales/es/translations.json"),
    },
    ja: {
      translations: require("./locales/ja/translations.json"),
    },
  },
  ns: ["translations"],
  defaultNS: "translations",
});

i18n.languages = ["en", "es", "ja"];

export default i18n;
