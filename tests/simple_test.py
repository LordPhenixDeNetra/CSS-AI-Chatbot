import json

def test_simple():
    # Exactement ce que l'utilisateur voit
    user_text = '"Bonjour,\\n\\nEn tant qu\'assistant de la Caisse de S\\u00e9curit\\u00e9 Sociale du S\\u00e9n\\u00e9gal"'
    
    print("PROBLEME IDENTIFIE:")
    print("Le texte affiché contient des guillemets au début et à la fin")
    print("Cela indique une sérialisation JSON accidentelle")
    print()
    print("Texte problématique:")
    print(user_text)
    print()
    
    # Solution: utiliser json.loads pour désérialiser
    try:
        corrected = json.loads(user_text)
        print("SOLUTION - Après json.loads:")
        print(corrected)
        print()
        print("Le texte est maintenant correct!")
    except Exception as e:
        print(f"Erreur: {e}")

if __name__ == "__main__":
    test_simple()