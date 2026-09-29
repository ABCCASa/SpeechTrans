import { createContext, useContext } from "react";
import { locales } from "./locales";

export const LanguageContext = createContext(locales.en);

export function useTranslation() {
    return useContext(LanguageContext);
}
