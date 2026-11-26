"use client";

import { Globe2 } from "lucide-react";
import { localeLabels, locales, type Locale } from "@/lib/i18n/translations";
import { useLocale } from "./locale-provider";

export default function LanguageSwitcher({ compact = false }: { compact?: boolean }) {
  const { locale, setLocale } = useLocale();
  return (
    <label data-i18n-ignore="true" className={`inline-flex items-center gap-2 rounded-xl border border-slate-300/20 bg-slate-900/90 px-3 py-2 text-sm text-slate-100 shadow-lg ${compact ? "" : ""}`}>
      <Globe2 size={16} className="shrink-0 text-cyan-300" />
      <span className="sr-only">Language</span>
      <select
        aria-label="Language"
        value={locale}
        onChange={(event) => setLocale(event.target.value as Locale)}
        className="max-w-[145px] cursor-pointer bg-transparent text-sm font-medium text-inherit outline-none [&>option]:bg-slate-900 [&>option]:text-white"
      >
        {locales.map((item) => <option key={item} value={item}>{localeLabels[item]}</option>)}
      </select>
    </label>
  );
}
