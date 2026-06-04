# js_scripts.py

# ── Horaires ──────────────────────────────────────────────────────────────────
JS_HORAIRES = """
(jourCible) => {
    var scripts = Array.from(document.querySelectorAll('script[type="application/ld+json"]'));
    for (var i = 0; i < scripts.length; i++) {
        try {
            var data = JSON.parse(scripts[i].innerText);
            var hours = data.openingHoursSpecification;
            if (!hours && data["@graph"]) {
                var r = data["@graph"].find(function(x) {
                    return x["@type"] === "FastFoodRestaurant" || x["@type"] === "Restaurant";
                });
                if (r) hours = r.openingHoursSpecification;
            }
            if (hours) {
                for (var j = 0; j < hours.length; j++) {
                    var days = hours[j].dayOfWeek;
                    if (typeof days === "string") days = [days];
                    if (days.some(function(d) { return d.indexOf(jourCible) !== -1; })) {
                        return "Ouvert de " + hours[j].opens + " a " + hours[j].closes;
                    }
                }
            }
        } catch(e) {}
    }
    return "Horaires indisponibles";
}
"""

# ── Menu complet ───────────────────────────────────────────────────────────────
JS_MENU = """
() => {
    var menu = {};
    var categorie = "Sans categorie";

    // Badges UberEats à ignorer comme nom de produit
    var reBadge = /^le n[°oº]\s*\d+|^nouveau|^promo|^populaire|^exclus|^offre/i;
    // Détection de prix : "12,50 €" ou "€ 12" etc.
    var rePrix  = /\d+[,.]\d+\s*€|€\s*\d+|\d+\s*€/;

    var selecteur = "h3, li[data-testid], li[class*='MenuItem'], li[class*='menuItem'], " +
                    "div[data-testid*='item'], div[class*='MenuItem'], div[class*='menuItem']";
    var tous = Array.from(document.querySelectorAll(selecteur));

    // ── Éliminer les éléments imbriqués dans un autre élément déjà sélectionné ──
    // Cause principale des doublons : li parent + div enfant tous les deux matchés
    var noeuds = tous.filter(function(el) {
        if (el.tagName === "H3") return true;
        return !tous.some(function(autre) {
            return autre !== el && autre.tagName !== "H3" && autre.contains(el);
        });
    });

    // Fallback si aucun élément-produit trouvé
    if (noeuds.filter(function(n){ return n.tagName !== "H3"; }).length === 0) {
        noeuds = Array.from(document.querySelectorAll("h3, section li, ul li"));
    }

    for (var i = 0; i < noeuds.length; i++) {
        var noeud = noeuds[i];

        // --- Titre de catégorie ---
        if (noeud.tagName === "H3") {
            var titre = (noeud.textContent || "").trim();
            if (titre.length > 0) {
                categorie = titre;
                if (!menu[categorie]) menu[categorie] = [];
            }
            continue;
        }

        if (!menu[categorie]) menu[categorie] = [];

        var lignes = (noeud.innerText || "").split("\\n")
            .map(function(l){ return l.trim(); })
            .filter(function(l){ return l.length > 0; });

        // --- Prix : première ligne qui correspond au pattern prix ---
        var prix = "Prix non affiche";
        for (var j = 0; j < lignes.length; j++) {
            if (rePrix.test(lignes[j])) { prix = lignes[j]; break; }
        }

        // --- Nom : priorité au DOM (h4 ou classes sémantiques) ---
        var nom = "";
        var nomEl = noeud.querySelector("h4") ||
                    noeud.querySelector("[class*='name'], [class*='title'], [class*='Name'], [class*='Title']");
        if (nomEl) {
            var nomDom = (nomEl.textContent || "").trim();
            if (nomDom.length > 1 && !reBadge.test(nomDom) && !rePrix.test(nomDom)) {
                nom = nomDom;
            }
        }
        // Sinon on parcourt les lignes
        if (!nom) {
            for (var k = 0; k < lignes.length; k++) {
                var ll = lignes[k];
                if (!reBadge.test(ll) && !rePrix.test(ll) && ll.length > 1) {
                    nom = ll; break;
                }
            }
        }
        if (!nom || nom.length < 2) continue;

        // --- Description ---
        var desc = "";
        for (var m = 0; m < lignes.length; m++) {
            var ld = lignes[m];
            if (ld !== nom && !reBadge.test(ld) && !rePrix.test(ld) && ld.length > 10) {
                desc = ld; break;
            }
        }

        menu[categorie].push({ nom: nom, prix: prix, desc: desc });
    }

    // ── Dédoublonner par nom : garder la version avec prix réel ──
    Object.keys(menu).forEach(function(cat) {
        var vu = {};
        menu[cat] = menu[cat].filter(function(p) {
            var cle = p.nom.trim().toLowerCase();
            if (!vu[cle]) {
                vu[cle] = p;
                return true;
            }
            // Si doublon et que le précédent n'a pas de prix mais celui-ci oui → mettre à jour
            if (vu[cle].prix === "Prix non affiche" && p.prix !== "Prix non affiche") {
                vu[cle].prix = p.prix;
            }
            return false;
        });
    });

    // Supprimer catégories vides
    Object.keys(menu).forEach(function(k){
        if (menu[k].length === 0) delete menu[k];
    });

    return menu;
}
"""

