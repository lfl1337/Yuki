import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "./locales/en.json";
import de from "./locales/de.json";
import tr from "./locales/tr.json";
import ja from "./locales/ja.json";
import fr from "./locales/fr.json";
import es from "./locales/es.json";
import it from "./locales/it.json";

export const LANGUAGES: Record<string, string> = {
  en: "English",
  de: "Deutsch",
  tr: "Türkçe",
  ja: "日本語",
  fr: "Français",
  es: "Español",
  it: "Italiano",
};

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    de: { translation: de },
    tr: { translation: tr },
    ja: { translation: ja },
    fr: { translation: fr },
    es: { translation: es },
    it: { translation: it },
  },
  lng: "en",
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

export default i18n;
