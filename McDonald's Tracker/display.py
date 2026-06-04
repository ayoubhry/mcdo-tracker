# display.py
# Fonctions d'affichage console.


def afficher_choix_restaurant(stores: dict) -> str:
    """Affiche la liste des restaurants et retourne le choix validé."""
    print("Restaurants disponibles :")
    for k, (nom, _) in stores.items():
        print(f"   [{k}] {nom}")
    choix = input("\nChoix du restaurant (1/2/3) : ").strip()
    if choix not in stores:
        choix = "1"
    return choix


def afficher_categories(menu: dict, nom_resto: str) -> None:
    """Affiche la liste numérotée des catégories."""
    categories = list(menu.keys())
    print(f"\n{'─'*60}")
    print(f"Categories — {nom_resto} :")
    print(f"{'─'*60}")
    for i, cat in enumerate(categories, 1):
        nb = len(menu[cat])
        print(f"   [{i:>2}] {cat}  ({nb} produit(s))")
    print(f"   [ 0] Quitter")
    print(f"{'─'*60}")


def afficher_produits(categorie: str, produits: list) -> None:
    """Affiche les produits d'une catégorie avec prix et ingrédients."""
    print("\n" + "="*60)
    print(f"  Categorie : {categorie}  ({len(produits)} produit(s))")
    print("="*60)
    for i, p in enumerate(produits, 1):
        print(f"\n  [{i}] {p['nom']}")
        print(f"       Prix        : {p['prix']}")
        desc = p["desc"] if p["desc"] else "(non renseignes)"
        print(f"       Ingredients : {desc}")
    print()


def choisir_categorie(menu: dict) -> str | None:
    """
    Demande à l'utilisateur de choisir une catégorie.
    Retourne le nom de la catégorie choisie, ou None pour quitter.
    """
    categories = list(menu.keys())
    while True:
        choix = input("\nChoix de la categorie (numero) : ").strip()
        if choix == "0":
            return None
        if choix.isdigit() and 1 <= int(choix) <= len(categories):
            return categories[int(choix) - 1]
        print("   Choix invalide, reessaie.")
