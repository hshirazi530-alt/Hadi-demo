(function () {
    "use strict";

    if ("serviceWorker" in navigator) {
        window.addEventListener("load", function () {
            navigator.serviceWorker.register("/service-worker.js", { scope: "/" })
                .catch(function (error) {
                    console.error("ثبت سرویس‌ورکر هژیر مارکت انجام نشد:", error);
                });
        });
    }

    var banner = document.querySelector("[data-pwa-install]");
    var installButton = document.querySelector("[data-pwa-install-button]");
    if (!banner || !installButton) return;

    var iosHelp = document.querySelector("[data-pwa-ios-help]");
    var deferredPrompt = null;
    var isStandalone = window.matchMedia("(display-mode: standalone)").matches
        || navigator.standalone === true;
    var isIos = /iPhone|iPad|iPod/i.test(navigator.userAgent)
        || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);

    if (isIos && !isStandalone) banner.hidden = false;

    window.addEventListener("beforeinstallprompt", function (event) {
        event.preventDefault();
        deferredPrompt = event;
        banner.hidden = false;
    });

    window.addEventListener("appinstalled", function () {
        deferredPrompt = null;
        banner.hidden = true;
    });

    installButton.addEventListener("click", async function () {
        if (!deferredPrompt) {
            if (isIos && iosHelp && typeof iosHelp.showModal === "function") {
                iosHelp.showModal();
            }
            return;
        }

        var promptEvent = deferredPrompt;
        deferredPrompt = null;
        try {
            await promptEvent.prompt();
            await promptEvent.userChoice;
            banner.hidden = true;
        } catch (error) {
            console.error("فرایند نصب اپلیکیشن کامل نشد:", error);
        }
    });

    var closeButton = document.querySelector("[data-pwa-install-close]");
    if (closeButton) {
        closeButton.addEventListener("click", function () {
            banner.hidden = true;
        });
    }

    var helpCloseButton = document.querySelector("[data-pwa-ios-close]");
    if (helpCloseButton && iosHelp) {
        helpCloseButton.addEventListener("click", function () {
            iosHelp.close();
        });
        iosHelp.addEventListener("click", function (event) {
            if (event.target === iosHelp) iosHelp.close();
        });
    }
})();
