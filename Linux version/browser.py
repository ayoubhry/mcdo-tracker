# browser.py
import random
import os
from playwright.async_api import async_playwright
from js_scripts import JS_HORAIRES, JS_MENU, JS_DEBUG_DOM


async def creer_browser():
    pw = await async_playwright().start()
    
    user_data_dir = os.path.join(os.getcwd(), "uber_user_data")
    
    context = await pw.chromium.launch_persistent_context(
        user_data_dir,
        headless=False,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars",
            "--start-maximized", 
            "--ignore-certificate-errors",
            "--disable-extensions",       # 🚫 Bloque les fenêtres d'extensions fantômes
            "--disable-component-update", # 🚫 Évite les lancements de tâches de fond Chromium
        ],
        no_viewport=True,
        locale="fr-FR",
        timezone_id="Europe/Paris",
        extra_http_headers={"Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"}
    )
    
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        window.navigator.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {} };
    """)
    
    page = context.pages[0] if context.pages else await context.new_page()
    return pw, context, page


async def charger_page(page, url):
    try:
        # Attente plus souple au chargement initial
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    except Exception as e:
        if "ERR_NETWORK_CHANGED" in str(e) or "net::ERR" in str(e):
            await page.wait_for_timeout(1000)
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        else:
            raise e

    await page.wait_for_timeout(1500) # Pause de stabilisation réduite
    for selector in ["h2", "h3", "div[data-testid='store-item']"]:
        try:
            await page.wait_for_selector(selector, timeout=4000)
            print(f"   Contenu detecte ({selector}).")
            return True
        except Exception:
            continue
    print("   Avertissement : aucun contenu detecte dans les delais.")
    return False


async def fermer_cookies(page):
    for sel in [
        "button:has-text('Tout accepter')",
        "button:has-text('Accept all')",
        "#onetrust-accept-btn-handler",
    ]:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=1500):
                await btn.click()
                await page.wait_for_timeout(1000)
                print("   Banniere cookies fermee.")
                return
        except Exception:
            pass


async def scroll_complet(page):
    print("   Chargement du menu (scroll rapide optimisé)...")
    # VITESSE BOOSTÉE : Moins d'itérations, plus grands pas, pauses très courtes
    for _ in range(12): 
        current_scroll = await page.evaluate("window.scrollY")
        distance = random.randint(700, 1100) # Descend plus vite
        
        await page.evaluate(f"window.scrollBy(0, {distance})")
        await page.wait_for_timeout(random.randint(300, 600)) # Pause ultra-courte (0.4s)
        
        h = await page.evaluate("document.body.scrollHeight")
        # Si on a atteint le bas du menu, on stoppe immédiatement sans attendre le chrono
        if current_scroll >= h - 1300:
            break
            
    print("   Fin du scroll.")


async def minimiser_fenetre(page):
    """Minimise la fenêtre Chromium via CDP après le captcha/cookies."""
    try:
        client = await page.context.new_cdp_session(page)
        info = await client.send("Browser.getWindowForTarget")
        await client.send("Browser.setWindowBounds", {
            "windowId": info["windowId"],
            "bounds": {"windowState": "minimized"}
        })
        await client.detach()
        print("   Fenêtre minimisée — scraping en arrière-plan.")
    except Exception as e:
        print(f"   (Impossible de minimiser la fenêtre : {e})")


async def get_horaires(page, jour_en):
    return await page.evaluate(JS_HORAIRES, jour_en)


async def get_menu(page):
    return await page.evaluate(JS_MENU)


async def get_debug_dom(page):
    return await page.evaluate(JS_DEBUG_DOM)
