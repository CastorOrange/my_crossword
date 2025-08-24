# Structure du projet Mot Fléché Interactif

## Structure des dossiers

```
votre-projet/
├── app.py
├── requirements.txt
├── templates/
│   ├── base.html
│   ├── upload.html
│   └── crossword.html
└── static/ (optionnel pour des ressources statiques)
```

## Principales corrections apportées

### 1. **Gestion des routes avec ID unique**
- Chaque grille uploadée génère un ID unique avec `uuid.uuid4()`
- URL de la forme `/crossword/<grid_id>` pour des liens partageables
- APIs mises à jour pour utiliser l'ID de grille

### 2. **Parser amélioré**
- Détection améliorée des cases noires basée sur les classes CSS Excel (`xl95`, `xl96`, etc.)
- Meilleure gestion des flèches et des définitions
- Normalisation de la grille pour éviter les erreurs d'index
- Gestion robuste des erreurs

### 3. **Interface utilisateur corrigée**
- Templates HTML complets et fonctionnels
- CSS responsive pour mobile
- Système de navigation par flèches amélioré
- Bouton de debug pour diagnostiquer les problèmes

### 4. **Fonctionnalités ajoutées**
- Sauvegarde/chargement de progression par grille
- Auto-sauvegarde toutes les 30 secondes
- Partage de lien unique par grille
- Endpoint de debug `/api/debug/<grid_id>`

## Installation et utilisation

### 1. Installation des dépendances
```bash
pip install -r requirements.txt
```

### 2. Créer la structure de dossiers
```bash
mkdir templates
# Copier les fichiers HTML dans le dossier templates/
```

### 3. Lancer l'application
```bash
python app.py
```

### 4. Accéder à l'application
- Ouvrir `http://localhost:5000` dans votre navigateur
- Uploader un fichier .htm Excel
- Partager le lien généré avec d'autres utilisateurs

## Format Excel attendu

Votre fichier Excel doit contenir :
- **Cases blanches** : cellules vides pour les lettres à saisir
- **Cases noires** : cellules avec fond noir contenant les définitions
- **Définitions** : texte avec flèches (→ pour horizontal, ↓ pour vertical)

Exemple de définition dans une case noire :
```
Du monde au balcon →
Endroit rêvé ↓
```

## Troubleshooting

### Si la grille ne s'affiche pas correctement :
1. Vérifiez l'endpoint debug : `/api/debug/<grid_id>`
2. Assurez-vous que votre fichier Excel utilise des cases avec fond noir
3. Vérifiez que les définitions contiennent des flèches

### Si les définitions ne sont pas détectées :
- Utilisez les flèches Unicode : → (Alt+26) et ↓ (Alt+25)
- Placez les définitions dans des cases avec fond noir
- Évitez les cellules fusionnées complexes

## Fonctionnalités disponibles

- ✅ Upload de fichiers .htm/.html
- ✅ Génération de liens uniques partageables
- ✅ Interface de saisie interactive
- ✅ Navigation par clavier (flèches)
- ✅ Sauvegarde automatique de progression
- ✅ Support mobile (responsive)
- ✅ Mode debug pour diagnostic
- ✅ Nettoyage et effacement de grille

Le site est maintenant fonctionnel et permet de créer des mots fléchés interactifs à partir de vos fichiers Excel HTML !