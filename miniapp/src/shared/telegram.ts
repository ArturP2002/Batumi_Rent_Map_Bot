/** Bootstrap Telegram Mini App shell: fullscreen + no swipe-to-close. */

type TgWebApp = NonNullable<Window["Telegram"]>["WebApp"];

function tg(): TgWebApp | undefined {
  return window.Telegram?.WebApp;
}

function applySafeAreaVars(app: TgWebApp) {
  const root = document.documentElement;
  const safe = app.safeAreaInset;
  const content = app.contentSafeAreaInset;

  const safeTop = safe?.top ?? 0;
  const safeBottom = safe?.bottom ?? 0;
  const safeLeft = safe?.left ?? 0;
  const safeRight = safe?.right ?? 0;
  const contentTop = content?.top ?? 0;
  const contentBottom = content?.bottom ?? 0;

  root.style.setProperty("--tg-safe-top", `${safeTop}px`);
  root.style.setProperty("--tg-safe-bottom", `${safeBottom}px`);
  root.style.setProperty("--tg-safe-left", `${safeLeft}px`);
  root.style.setProperty("--tg-safe-right", `${safeRight}px`);
  root.style.setProperty("--tg-content-safe-top", `${contentTop}px`);
  root.style.setProperty("--tg-content-safe-bottom", `${contentBottom}px`);

  // Fallback when Telegram reports empty content inset in fullscreen:
  // leave room for the native «Закрыть» / controls row (~44–56px under status bar).
  const fullscreen = Boolean(app.isFullscreen);
  const needsFallback = fullscreen && contentTop < 40;
  root.style.setProperty("--ui-top-gap", needsFallback ? "52px" : "8px");
  root.dataset.tgFullscreen = fullscreen ? "1" : "0";
}

export function initTelegramApp() {
  const app = tg();
  if (!app) return;

  app.ready();
  app.expand();

  // Prevent closing / collapsing the Mini App by swiping down (Bot API 7.7+)
  try {
    app.disableVerticalSwipes?.();
  } catch {
    /* older clients */
  }

  // True fullscreen when supported (Bot API 8.0+)
  try {
    if (!app.isFullscreen) {
      app.requestFullscreen?.();
    }
  } catch {
    /* ignored — expand() already applied */
  }

  try {
    app.setHeaderColor?.("#1f6feb");
    app.setBackgroundColor?.("#f2f5f9");
  } catch {
    /* older clients */
  }

  applySafeAreaVars(app);
  // Insets often arrive a tick after fullscreen engages
  window.setTimeout(() => applySafeAreaVars(app), 50);
  window.setTimeout(() => applySafeAreaVars(app), 300);

  app.onEvent?.("fullscreenChanged", () => {
    if (!app.isFullscreen) {
      app.expand();
      try {
        app.requestFullscreen?.();
      } catch {
        /* ignore */
      }
    }
    applySafeAreaVars(app);
    window.setTimeout(() => applySafeAreaVars(app), 50);
  });

  app.onEvent?.("fullscreenFailed", () => {
    app.expand();
    applySafeAreaVars(app);
  });

  app.onEvent?.("safeAreaChanged", () => applySafeAreaVars(app));
  app.onEvent?.("contentSafeAreaChanged", () => applySafeAreaVars(app));

  app.onEvent?.("viewportChanged", () => {
    app.expand();
    applySafeAreaVars(app);
  });
}
