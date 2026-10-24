import { useEffect, useState, useCallback } from 'react';

declare global {
  interface Window {
    Telegram?: {
      WebApp?: any;
    };
  }
}

export interface TMAStartAppTarget {
  accountId: string;
  peerId: number;
}

export function useTelegram() {
  const [isTMA, setIsTMA] = useState(false);
  const [startAppTarget, setStartAppTarget] = useState<TMAStartAppTarget | null>(null);

  useEffect(() => {
    const tg = window.Telegram?.WebApp;
    if (tg && tg.initData) {
      setIsTMA(true);
      try {
        tg.ready();
        tg.expand();
        tg.setHeaderColor('#17212b');
        tg.setBackgroundColor('#0e1621');
      } catch (err) {
        console.warn('Could not apply TMA theme params:', err);
      }

      // Check startapp deep link parameter: format 'chat_{accountId}_{peerId}'
      const startParam =
        tg.initDataUnsafe?.start_param ||
        new URLSearchParams(window.location.search).get('startapp') ||
        new URLSearchParams(window.location.search).get('tgWebAppStartParam');

      if (startParam && startParam.startsWith('chat_')) {
        const parts = startParam.split('_');
        if (parts.length >= 3) {
          const accountId = parts[1];
          const peerId = parseInt(parts[2], 10);
          if (accountId && !isNaN(peerId)) {
            setStartAppTarget({ accountId, peerId });
          }
        }
      }
    }
  }, []);

  const triggerHaptic = useCallback(
    (style: 'light' | 'medium' | 'heavy' | 'success' | 'error' = 'medium') => {
      try {
        const haptic = window.Telegram?.WebApp?.HapticFeedback;
        if (!haptic) return;

        if (style === 'success' || style === 'error') {
          haptic.notificationOccurred(style);
        } else {
          haptic.impactOccurred(style);
        }
      } catch (err) {
        // Suppress outside Telegram webview
      }
    },
    []
  );

  const setBackButton = useCallback(
    (visible: boolean, onClick?: () => void) => {
      try {
        const bb = window.Telegram?.WebApp?.BackButton;
        if (!bb) return;

        if (visible) {
          bb.show();
          if (onClick) {
            bb.onClick(onClick);
          }
        } else {
          bb.hide();
        }
      } catch (err) {
        // Suppress
      }
    },
    []
  );

  return {
    isTMA,
    tgUser: window.Telegram?.WebApp?.initDataUnsafe?.user,
    startAppTarget,
    triggerHaptic,
    setBackButton,
  };
}

export function getAvatarGradientClass(id: number | string): string {
  let num = 0;
  if (typeof id === 'number') {
    num = Math.abs(id);
  } else {
    for (let i = 0; i < id.length; i++) {
      num = (num << 5) - num + id.charCodeAt(i);
      num |= 0;
    }
    num = Math.abs(num);
  }
  return `tg-avatar-${num % 7}`;
}

export function getInitials(name: string): string {
  if (!name) return '?';
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return name.slice(0, 2).toUpperCase();
}
