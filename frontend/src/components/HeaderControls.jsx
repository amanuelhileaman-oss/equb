import React, { useState, useRef, useEffect } from 'react';
import { useTheme } from '../context/ThemeContext';
import { useLanguage, AVAILABLE_LANGUAGES } from '../context/LanguageContext';
import { Sun, Moon, Monitor, Globe, ChevronDown, Check } from 'lucide-react';
import './HeaderControls.css';

export function HeaderControls({ className = '' }) {
  const { theme, setTheme } = useTheme();
  const { language, setLanguage, t } = useLanguage();

  const [themeDropdownOpen, setThemeDropdownOpen] = useState(false);
  const [langDropdownOpen, setLangDropdownOpen] = useState(false);

  const themeRef = useRef(null);
  const langRef = useRef(null);

  // Close dropdowns when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (themeRef.current && !themeRef.current.contains(event.target)) {
        setThemeDropdownOpen(false);
      }
      if (langRef.current && !langRef.current.contains(event.target)) {
        setLangDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('touchstart', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('touchstart', handleClickOutside);
    };
  }, []);

  const getThemeIcon = () => {
    if (theme === 'light') return <Sun size={16} className="theme-icon-sun" />;
    if (theme === 'dark') return <Moon size={16} className="theme-icon-moon" />;
    return <Monitor size={16} className="theme-icon-system" />;
  };

  const getThemeLabel = () => {
    if (theme === 'light') return t('themeLight') || 'Light';
    if (theme === 'dark') return t('themeDark') || 'Dark';
    return t('themeSystem') || 'System';
  };

  const getCurrentLangObject = () => {
    return AVAILABLE_LANGUAGES.find(l => l.code === language) || AVAILABLE_LANGUAGES[0];
  };

  const getFlag = (code) => {
    return code === 'en' ? '🇬🇧' : '🇪🇹';
  };

  return (
    <div className={`header-controls-wrap ${className}`}>
      {/* ===============================================================
          1. THEME SELECTOR DROPDOWN (Light, Dark, System)
          =============================================================== */}
      <div className="header-control-dropdown-container" ref={themeRef}>
        <button
          type="button"
          className="header-control-trigger theme-trigger"
          onClick={() => {
            setThemeDropdownOpen(!themeDropdownOpen);
            setLangDropdownOpen(false);
          }}
          aria-label={t('selectTheme') || 'Select Theme'}
          title={t('selectTheme') || 'Select Theme'}
        >
          {getThemeIcon()}
          <span className="control-label">{getThemeLabel()}</span>
          <ChevronDown size={14} className={`control-chevron ${themeDropdownOpen ? 'open' : ''}`} />
        </button>

        {themeDropdownOpen && (
          <div className="header-control-menu animate-pop-in">
            <div className="header-control-menu-header">
              {t('theme') || 'Theme'}
            </div>
            
            <button
              type="button"
              className={`header-control-menu-item ${theme === 'light' ? 'active' : ''}`}
              onClick={() => {
                setTheme('light');
                setThemeDropdownOpen(false);
              }}
            >
              <div className="menu-item-left">
                <Sun size={16} className="theme-icon-sun" />
                <span>{t('themeLight') || 'Light'}</span>
              </div>
              {theme === 'light' && <Check size={14} className="menu-item-check" />}
            </button>

            <button
              type="button"
              className={`header-control-menu-item ${theme === 'dark' ? 'active' : ''}`}
              onClick={() => {
                setTheme('dark');
                setThemeDropdownOpen(false);
              }}
            >
              <div className="menu-item-left">
                <Moon size={16} className="theme-icon-moon" />
                <span>{t('themeDark') || 'Dark'}</span>
              </div>
              {theme === 'dark' && <Check size={14} className="menu-item-check" />}
            </button>

            <button
              type="button"
              className={`header-control-menu-item ${theme === 'system' ? 'active' : ''}`}
              onClick={() => {
                setTheme('system');
                setThemeDropdownOpen(false);
              }}
            >
              <div className="menu-item-left">
                <Monitor size={16} className="theme-icon-system" />
                <span>{t('themeSystem') || 'System'}</span>
              </div>
              {theme === 'system' && <Check size={14} className="menu-item-check" />}
            </button>
          </div>
        )}
      </div>

      {/* ===============================================================
          2. LANGUAGE SELECTOR DROPDOWN (4 Languages: EN, AM, OM, TI)
          =============================================================== */}
      <div className="header-control-dropdown-container" ref={langRef}>
        <button
          type="button"
          className="header-control-trigger lang-trigger"
          onClick={() => {
            setLangDropdownOpen(!langDropdownOpen);
            setThemeDropdownOpen(false);
          }}
          aria-label={t('selectLanguage') || 'Select Language'}
          title={t('selectLanguage') || 'Select Language'}
        >
          <span className="lang-flag">{getFlag(language)}</span>
          <span className="control-label">{getCurrentLangObject().short}</span>
          <ChevronDown size={14} className={`control-chevron ${langDropdownOpen ? 'open' : ''}`} />
        </button>

        {langDropdownOpen && (
          <div className="header-control-menu animate-pop-in">
            <div className="header-control-menu-header">
              {t('language') || 'Language'}
            </div>
            
            {AVAILABLE_LANGUAGES.map((lang) => {
              const isSelected = language === lang.code;
              return (
                <button
                  key={lang.code}
                  type="button"
                  className={`header-control-menu-item ${isSelected ? 'active' : ''}`}
                  onClick={() => {
                    setLanguage(lang.code);
                    setLangDropdownOpen(false);
                  }}
                >
                  <div className="menu-item-left">
                    <span className="lang-flag">{getFlag(lang.code)}</span>
                    <div className="lang-names">
                      <span className="lang-native">{lang.native}</span>
                      <span className="lang-english">{lang.label}</span>
                    </div>
                  </div>
                  {isSelected && <Check size={14} className="menu-item-check" />}
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
export default HeaderControls;

