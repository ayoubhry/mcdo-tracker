#!/usr/bin/env python3
"""
api_server.py — Serveur Flask qui expose :
  GET  /restaurants          → liste des restaurants (restaurants.json)
  POST /scrape               → lance le scraping d'un restaurant et retourne le menu
  GET  /                     → sert index.html
  GET  /<fichier statique>   → sert les assets

Usage : python3 api_server.py
"""

import asyncio
import datetime
import json
import threading
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Import du moteur de scraping
import sys
sys.path.insert(0, str(Path(__file__).parent))
from browser import creer_browser, charger_page, fermer_cookies, minimiser_fenetre, scroll_complet
from browser import get_horaires, get_menu
from js_scripts import JS_DEBUG_DOM

STATIC_DIR = Path(__file__).parent

JOURS_EN = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
JOURS_FR = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"]

# Correspondance id restaurant → URL UberEats
STORE_URLS = {
    "fr_caen_centre":       "https://www.ubereats.com/fr/store/mcdonalds-caen-centre/xJPVGkgwTbu1r2uwqYqcsA",
    "fr_caen_cote_de_nacre":"https://www.ubereats.com/fr/store/mcdonalds-caen-cote-de-nacre/sDU71dHwStOZcQSKa8vAVg",
    "fr_herouville":        "https://www.ubereats.com/fr/store/mcdonalds-caen-herouville/ewHlMy56SoGzk-fHOrL7Lg",
    "fr_ouistreham":        "https://www.ubereats.com/fr/store/mcdonalds-ouistreham/HNLRmj14S7ygt_QlIldwnQ",
    "fr_rots":              "https://www.ubereats.com/fr/store/mcdonalds-rots/QduIuD80Xw2tVLXmjuDsEA",
    "fr_ifs":               "https://www.ubereats.com/fr/store/mcdonalds-ifs/L39cOkbJTfuD_jETjIIrsA",
    "fr_mondeville":        "https://www.ubereats.com/fr/store/mcdonalds-caen-mondeville/b76iDxPwQ4imZ2iO8rSHSw",
}

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="")
CORS(app)


# ── Routes statiques ──────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")

@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)


# ── API restaurants ───────────────────────────────────────────────────────────

@app.route("/restaurants")
def restaurants():
    data = json.loads((STATIC_DIR / "restaurants.json").read_text())
    return jsonify(data)


# ── API scraping ──────────────────────────────────────────────────────────────

def run_scrape(store_id: str) -> dict:
    """Exécute le scraping dans un event loop dédié (thread-safe)."""

    url = STORE_URLS.get(store_id)
    if not url:
        return {"error": f"Restaurant '{store_id}' inconnu."}

    async def _scrape():
        pw, context, page = await creer_browser()
        try:
            await charger_page(page, url)

            # Gestion anti-bot simple (pas de résolution humaine en mode GUI)
            try:
                await page.wait_for_selector("h3", timeout=20000)
            except Exception:
                pass

            await fermer_cookies(page)
            await minimiser_fenetre(page)
            await page.wait_for_timeout(1500)
            await scroll_complet(page)

            jour_idx  = datetime.datetime.today().weekday()
            horaires  = await get_horaires(page, JOURS_EN[jour_idx])
            jour_fr   = JOURS_FR[jour_idx]
            menu      = await get_menu(page)

            return {
                "horaires": horaires,
                "jour":     jour_fr,
                "menu":     menu,
                "error":    None,
            }
        except Exception as e:
            return {"error": str(e)}
        finally:
            await context.close()
            await pw.stop()

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_scrape())
    finally:
        loop.close()


@app.route("/scrape", methods=["POST"])
def scrape():
    body     = request.get_json(silent=True) or {}
    store_id = body.get("store_id", "")
    if not store_id:
        return jsonify({"error": "Paramètre 'store_id' manquant."}), 400

    result = run_scrape(store_id)
    return jsonify(result)


# ── État global du scraping en arrière-plan ───────────────────────────────────
_scrape_state = {
    "running":  False,
    "done":     [],    # [ { store_id, menu, horaires, jour, error } ]
    "current":  None,  # store_id en cours de scraping
    "finished": False,
}
_scrape_lock = threading.Lock()


def _background_scrape_all():
    """Lance le scraping séquentiel dans un thread dédié."""
    store_ids = list(STORE_URLS.keys())

    with _scrape_lock:
        _scrape_state["running"]  = True
        _scrape_state["done"]     = []
        _scrape_state["current"]  = None
        _scrape_state["finished"] = False

    for sid in store_ids:
        with _scrape_lock:
            _scrape_state["current"] = sid

        result = run_scrape(sid)

        with _scrape_lock:
            _scrape_state["done"].append({
                "store_id": sid,
                "menu":     result.get("menu"),
                "horaires": result.get("horaires"),
                "jour":     result.get("jour"),
                "error":    result.get("error"),
            })

    with _scrape_lock:
        _scrape_state["running"]  = False
        _scrape_state["current"]  = None
        _scrape_state["finished"] = True


@app.route("/scrape-all-start", methods=["POST"])
def scrape_all_start():
    """Démarre le scraping en arrière-plan (idempotent)."""
    with _scrape_lock:
        if _scrape_state["running"]:
            return jsonify({"status": "already_running"})

    t = threading.Thread(target=_background_scrape_all, daemon=True)
    t.start()
    return jsonify({"status": "started"})


@app.route("/scrape-all-status")
def scrape_all_status():
    """Retourne l'état courant du scraping (polling)."""
    with _scrape_lock:
        return jsonify({
            "running":  _scrape_state["running"],
            "current":  _scrape_state["current"],
            "done":     list(_scrape_state["done"]),
            "finished": _scrape_state["finished"],
        })


if __name__ == "__main__":
    print("\n" + "="*55)
    print("  McDo Caen — Interface Graphique")
    print("  Ouvre http://localhost:5000 dans ton navigateur")
    print("="*55 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
