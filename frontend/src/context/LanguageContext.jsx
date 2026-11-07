import React, { createContext, useContext, useState, useEffect } from 'react';
import { translations } from '../i18n/translations';

export const AVAILABLE_LANGUAGES = [
  { code: 'en', label: 'English', native: 'English', short: 'EN' },
  { code: 'am', label: 'Amharic', native: 'አማርኛ', short: 'አማ' },
  { code: 'om', label: 'Afaan Oromoo', native: 'Afaan Oromoo', short: 'ORO' },
  { code: 'ti', label: 'Tigrinya', native: 'ትግርኛ', short: 'ትግ' }
];

const LanguageContext = createContext();

export function LanguageProvider({ children }) {
  const [language, setLanguageState] = useState(() => {
    const saved = localStorage.getItem('equb_lang');
    return ['en', 'am', 'om', 'ti'].includes(saved) ? saved : 'en';
  });

  const setLanguage = (newLang) => {
    if (['en', 'am', 'om', 'ti'].includes(newLang)) {
      setLanguageState(newLang);
      localStorage.setItem('equb_lang', newLang);
    }
  };

  const toggleLanguage = () => {
    const order = ['en', 'am', 'om', 'ti'];
    const nextIdx = (order.indexOf(language) + 1) % order.length;
    setLanguage(order[nextIdx]);
  };

  const t = (key) => {
    return translations[language]?.[key] || translations['en']?.[key] || key;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, toggleLanguage, t, availableLanguages: AVAILABLE_LANGUAGES }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
}
