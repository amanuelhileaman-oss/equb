import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../services/api';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [groupRoles, setGroupRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentInterface, setCurrentInterface] = useState('MEMBER');
  const [selectedGroupId, setSelectedGroupId] = useState(null);

  const initAuth = async () => {
    try {
      setLoading(true);
      const data = await api.getCurrentUser();
      if (data?.user) {
        setUser(data.user);
        setGroupRoles(data.group_roles || []);
        
        // Auto-select initial interface based on authoritative backend role
        const isOrganizerUser = Boolean(
          data.user?.is_organizer ||
          data.is_organizer ||
          data.user?.has_organizer_profile ||
          data.user?.organizer_profile_summary ||
          data.user?.primary_role === 'ORGANIZER' ||
          data.primary_role === 'ORGANIZER' ||
          data.group_roles?.some(gr => gr.roles.includes('GROUP_ORGANIZER'))
        );
        const isTreasurerUser = Boolean(
          data.user?.is_treasurer ||
          data.is_treasurer ||
          data.user?.primary_role === 'TREASURER' ||
          data.primary_role === 'TREASURER' ||
          data.group_roles?.some(gr => gr.roles.includes('GROUP_TREASURER'))
        );

        if (data.user?.is_platform_admin) {
          setCurrentInterface('SUPER_ADMIN');
        } else if (isOrganizerUser) {
          setCurrentInterface('ORGANIZER');
        } else if (isTreasurerUser) {
          setCurrentInterface('TREASURER');
        } else {
          setCurrentInterface('MEMBER');
        }

        if (data.group_roles?.length > 0) {
          setSelectedGroupId(data.group_roles[0].group_id);
        }
      } else {
        setUser(null);
      }
    } catch (err) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    initAuth();
  }, []);

  const login = async (email, password, mfaCode = '') => {
    const res = await api.login({ email, password, mfa_code: mfaCode });
    if (res?.mfa_required) {
      return res;
    }
    if (res?.csrf_token) {
      window.__CSRF_TOKEN__ = res.csrf_token;
    }
    if (res?.user) {
      setUser(res.user);
      setGroupRoles(res.group_roles || []);

      const isOrganizerUser = Boolean(
        res.user?.is_organizer ||
        res.is_organizer ||
        res.user?.has_organizer_profile ||
        res.user?.organizer_profile_summary ||
        res.user?.primary_role === 'ORGANIZER' ||
        res.primary_role === 'ORGANIZER' ||
        res.group_roles?.some(gr => gr.roles.includes('GROUP_ORGANIZER'))
      );
      const isTreasurerUser = Boolean(
        res.user?.is_treasurer ||
        res.is_treasurer ||
        res.user?.primary_role === 'TREASURER' ||
        res.primary_role === 'TREASURER' ||
        res.group_roles?.some(gr => gr.roles.includes('GROUP_TREASURER'))
      );

      if (res.user?.is_platform_admin) {
        setCurrentInterface('SUPER_ADMIN');
      } else if (isOrganizerUser) {
        setCurrentInterface('ORGANIZER');
      } else if (isTreasurerUser) {
        setCurrentInterface('TREASURER');
      } else {
        setCurrentInterface('MEMBER');
      }

      if (res.group_roles?.length > 0) {
        setSelectedGroupId(res.group_roles[0].group_id);
      }
    }
    return res;
  };

  const register = async (formData) => {
    const res = await api.register(formData);
    return res;
  };

  const logout = async () => {
    try {
      await api.logout();
    } catch (e) {
      console.error(e);
    }
    setUser(null);
    setGroupRoles([]);
    setCurrentInterface('MEMBER');
    setSelectedGroupId(null);
  };

  const hasRole = (roleCode) => {
    if (!user) return false;
    if (roleCode === 'PLATFORM_SUPER_ADMIN') return Boolean(user.is_platform_admin);
    if (roleCode === 'GROUP_ORGANIZER') {
      return Boolean(user.is_organizer || user.has_organizer_profile || user.organizer_profile_summary || user.primary_role === 'ORGANIZER' || groupRoles.some(gr => gr.roles.includes('GROUP_ORGANIZER')));
    }
    if (roleCode === 'GROUP_TREASURER') {
      return Boolean(user.is_treasurer || user.primary_role === 'TREASURER' || groupRoles.some(gr => gr.roles.includes('GROUP_TREASURER')));
    }
    if (!selectedGroupId) {
      return groupRoles.some(gr => gr.roles.includes(roleCode));
    }
    const currentGroup = groupRoles.find(gr => gr.group_id === selectedGroupId);
    return currentGroup?.roles?.includes(roleCode) || false;
  };

  return (
    <AuthContext.Provider value={{
      user,
      setUser,
      groupRoles,
      loading,
      currentInterface,
      setCurrentInterface,
      selectedGroupId,
      setSelectedGroupId,
      login,
      register,
      logout,
      hasRole,
      refreshUser: initAuth
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
