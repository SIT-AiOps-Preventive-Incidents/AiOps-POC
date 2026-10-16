// Lightweight bilingual helper. No key files: a string is written inline as t("English", "ไทย"), and the
// right one is chosen by the current locale, reactively (the store's prefs.locale drives it). English is the
// default and the fallback, so a page that has not been translated yet still reads correctly.
import { computed } from "vue";
import { useUiStore } from "@/stores/ui";

export const LOCALES = [
  { value: "en", label: "EN", name: "English" },
  { value: "th", label: "ไทย", name: "ไทย" },
];

export function useI18n() {
  const ui = useUiStore();
  const locale = computed(() => (ui.prefs.locale === "th" ? "th" : "en"));
  const t = (en, th) => (locale.value === "th" && th != null ? th : en);
  const setLocale = (l) => ui.setPref("locale", l);
  const toggle = () => setLocale(locale.value === "th" ? "en" : "th");
  return { locale, t, setLocale, toggle };
}
