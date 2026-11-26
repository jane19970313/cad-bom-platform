
"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  dictionaries,
  type Locale,
  locales,
} from "@/lib/i18n/translations";

type LocaleContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (value: string) => string;
};

const LocaleContext =
  createContext<LocaleContextValue | null>(null);

const STORAGE_KEY = "cad2bom-locale";

const normalize = (value: string) =>
  value.replace(/\s+/g, " ").trim();

// Case-insensitive dictionary key normalization.
const normalizeKey = (value: string) =>
  normalize(value).toLowerCase();

// Case-insensitive translation lookup.
function translateValue(
  dictionary: Record<string, string> | undefined,
  value: string
): string {
  if (!dictionary) return value;

  const key = normalizeKey(value);

  const matchedKey = Object.keys(dictionary).find(
    (item) => normalizeKey(item) === key
  );

  return matchedKey !== undefined
    ? dictionary[matchedKey]
    : value;
}

type SavedValue = {
  original: string;
  applied: string | null;
};

// Preserve original DOM text and attributes.
const originalText = new WeakMap<Node, SavedValue>();

const originalAttributes = new WeakMap<
  Element,
  Map<string, SavedValue>
>();

const TRANSLATABLE_ATTRIBUTES = [
  "placeholder",
  "title",
  "aria-label",
  "alt",
];

const SKIP_TAGS = [
  "SCRIPT",
  "STYLE",
  "CODE",
  "PRE",
  "TEXTAREA",
  "INPUT",
  "SELECT",
  "OPTION",
  "SVG",
  "MATH",
];

function getSavedValue(
  map: WeakMap<Node, SavedValue>,
  node: Node,
  current: string
): SavedValue {
  let saved = map.get(node);

  if (!saved) {
    saved = {
      original: current,
      applied: null,
    };

    map.set(node, saved);
  } else if (
    saved.applied !== null &&
    current !== saved.applied
  ) {
    // React or another application process changed
    // the DOM. Treat the new content as original.
    saved.original = current;
    saved.applied = null;
  }

  return saved;
}

function getAttributeSavedValue(
  element: Element,
  attr: string,
  current: string
): SavedValue {
  let attributes = originalAttributes.get(element);

  if (!attributes) {
    attributes = new Map();
    originalAttributes.set(element, attributes);
  }

  let saved = attributes.get(attr);

  if (!saved) {
    saved = {
      original: current,
      applied: null,
    };

    attributes.set(attr, saved);
  } else if (
    saved.applied !== null &&
    current !== saved.applied
  ) {
    saved.original = current;
    saved.applied = null;
  }

  return saved;
}

function preserveWhitespace(
  original: string,
  translated: string
) {
  const leading = original.match(/^\s*/)?.[0] ?? "";
  const trailing = original.match(/\s*$/)?.[0] ?? "";

  return `${leading}${translated}${trailing}`;
}

function translateDom(locale: Locale) {
  const dictionary = dictionaries[locale];

  if (!dictionary || typeof document === "undefined") {
    return;
  }

  const isEnglish = locale === "en";

  const translateNode = (node: Node) => {
    // TEXT NODE
    if (node.nodeType === Node.TEXT_NODE) {
      const current = node.nodeValue ?? "";

      if (!current.trim()) return;

      const saved = getSavedValue(
        originalText,
        node,
        current
      );

      const original = saved.original;

      // English restores original source text.
      const translated = isEnglish
        ? original
        : translateValue(dictionary, original);

      const result = isEnglish
        ? original
        : preserveWhitespace(original, translated);

      if (current !== result) {
        saved.applied = result;
        node.nodeValue = result;
      } else {
        saved.applied = result;
      }

      return;
    }

    if (node.nodeType !== Node.ELEMENT_NODE) return;

    const element = node as HTMLElement;

    // Ignore explicitly protected content.
    if (element.closest("[data-i18n-ignore='true']")) {
      return;
    }

    // Translate common accessibility and input attributes.
    for (const attr of TRANSLATABLE_ATTRIBUTES) {
      const current = element.getAttribute(attr);

      if (current === null) continue;

      const saved = getAttributeSavedValue(
        element,
        attr,
        current
      );

      const original = saved.original;

      const translated = isEnglish
        ? original
        : translateValue(dictionary, original);

      if (current !== translated) {
        saved.applied = translated;
        element.setAttribute(attr, translated);
      } else {
        saved.applied = translated;
      }
    }

    // Never translate CAD payloads, source code,
    // form values, or editable content.
    if (
      element.isContentEditable ||
      SKIP_TAGS.includes(element.tagName)
    ) {
      return;
    }

    // Process children.
    for (const child of Array.from(element.childNodes)) {
      translateNode(child);
    }
  };

  translateNode(document.body);
}

export function LocaleProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [locale, setLocaleState] =
    useState<Locale>("en");

  const [ready, setReady] = useState(false);

  // Change language.
  const setLocale = useCallback((next: Locale) => {
    if (!locales.includes(next)) return;

    setLocaleState(next);

    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Storage may be unavailable.
    }
  }, []);

  // Translation helper for React components.
  // Supports case-insensitive English keys.
  const t = useCallback(
    (value: string) => {
      if (locale === "en") return value;

      const dictionary = dictionaries[locale];

      return translateValue(dictionary, value);
    },
    [locale]
  );

  // Restore saved language on startup.
  useEffect(() => {
    try {
      const saved = localStorage.getItem(
        STORAGE_KEY
      );

      if (
        saved &&
        locales.includes(saved as Locale)
      ) {
        setLocaleState(saved as Locale);
      } else {
        const browserLanguage =
          navigator.language
            .slice(0, 2)
            .toLowerCase();

        if (
          locales.includes(
            browserLanguage as Locale
          )
        ) {
          setLocaleState(browserLanguage as Locale);
        }
      }
    } catch {
      // Default to English.
    }

    setReady(true);
  }, []);

  // Apply language and RTL/LTR direction.
  useEffect(() => {
    if (!ready) return;

    const direction = "ltr";

    document.documentElement.lang = locale;
    document.documentElement.dir = direction;

    document.body.dir = direction;

    document.documentElement.dataset.locale =
      locale;

    // Translate or restore all existing content.
    translateDom(locale);

    // Observe dynamically inserted React components.
    const observer = new MutationObserver(() => {
      translateDom(locale);
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true,
      attributes: true,
      attributeFilter: [
        ...TRANSLATABLE_ATTRIBUTES,
      ],
    });

    return () => {
      observer.disconnect();
    };
  }, [locale, ready]);

  const value = useMemo(
    () => ({
      locale,
      setLocale,
      t,
    }),
    [locale, setLocale, t]
  );

  return (
    <LocaleContext.Provider value={value}>
      {children}
    </LocaleContext.Provider>
  );
}

export function useLocale() {
  const context = useContext(LocaleContext);

  if (!context) {
    throw new Error(
      "useLocale must be used inside LocaleProvider"
    );
  }

  return context;
}
