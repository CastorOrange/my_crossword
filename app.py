from flask import Flask, render_template, request, jsonify, session, redirect
import os
import json
import re
from bs4 import BeautifulSoup
import math
from datetime import datetime
import pandas as pd
import uuid

app = Flask(__name__)
app.secret_key = 'votre_cle_secrete_ici_' + str(uuid.uuid4())

class ExcelHTMLCrosswordParser:
    def __init__(self):
        self.grid = []
        self.clues = {'horizontal': [], 'vertical': []}
        self.solution = []
        self.raw_data = {}
        
    def parse_excel_html(self, html_content):
        """Parse le fichier HTML Excel avec une approche spécialisée pour les mots fléchés"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Chercher toutes les tables
        tables = soup.find_all('table')
        
        if not tables:
            raise ValueError("Aucune table trouvée dans le fichier HTML")
        
        # Analyser chaque table pour trouver la grille principale
        best_table = self._find_main_grid_table(tables)
        
        if not best_table:
            raise ValueError("Impossible de trouver la table principale de la grille")
        
        # Parser la table principale
        grid_data = self._parse_table_to_grid(best_table)
        
        # Analyser la structure pour identifier les patterns de mots fléchés
        self._analyze_crossword_structure(grid_data)
        
        # Extraire les définitions des cases noires
        self._extract_clues_from_grid(grid_data)
        
        return {
            'grid': self.grid,
            'clues': self.clues,
            'solution': self.solution,
            'raw_data': self.raw_data
        }
    
    def _find_main_grid_table(self, tables):
        """Trouve la table principale contenant la grille"""
        best_table = None
        max_score = 0
        
        for table in tables:
            score = self._score_table_as_crossword(table)
            
            if score > max_score:
                max_score = score
                best_table = table
        
        return best_table
    
    def _score_table_as_crossword(self, table):
        """Score une table pour déterminer si c'est une grille de mots fléchés"""
        score = 0
        rows = table.find_all('tr')
        
        if len(rows) < 3:
            return 0
        
        # Vérifier la régularité des lignes/colonnes
        cell_counts = []
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if cells:
                cell_counts.append(len(cells))
        
        if not cell_counts:
            return 0
        
        # Score basé sur la régularité
        if len(set(cell_counts)) <= 2:  # Tolérer une légère variation
            score += 50
        
        # Score basé sur la taille
        avg_cells = sum(cell_counts) / len(cell_counts)
        if 5 <= avg_cells <= 20:
            score += 30
        
        # Score basé sur le contenu
        total_cells = 0
        cells_with_content = 0
        black_cells = 0
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            for cell in cells:
                total_cells += 1
                text = cell.get_text(strip=True)
                style = cell.get('style', '').lower()
                class_attr = cell.get('class', [])
                
                if text:
                    cells_with_content += 1
                    
                    # Chercher des flèches ou définitions
                    if any(arrow in text for arrow in ['→', '↓', '←', '↑', '->', '<-', '↗', '↖', '↙', '↘']):
                        score += 10
                
                # Détecter les cases noires par classe CSS
                if isinstance(class_attr, list):
                    class_names = ' '.join(class_attr).lower()
                    if any(cls in class_names for cls in ['xl95', 'xl96', 'xl97', 'xl98', 'xl99']):
                        black_cells += 1
                        score += 5
                
                # Détecter par style
                if 'background' in style:
                    if any(color in style for color in ['black', '#000', '#333', 'rgb(0,0,0)']):
                        black_cells += 1
                        score += 5
        
        # Ratio de cases noires approprié
        if total_cells > 0:
            black_ratio = black_cells / total_cells
            if 0.1 <= black_ratio <= 0.7:
                score += 20
        
        return score
    
    def _parse_table_to_grid(self, table):
        """Parse une table en grille de données"""
        grid_data = []
        rows = table.find_all('tr')
        
        for row_idx, row in enumerate(rows):
            cells = row.find_all(['td', 'th'])
            row_data = []
            
            for col_idx, cell in enumerate(cells):
                cell_info = self._parse_cell_info(cell, row_idx, col_idx)
                row_data.append(cell_info)
            
            if row_data:
                grid_data.append(row_data)
        
        return grid_data
    
    def _parse_cell_info(self, cell, row_idx, col_idx):
        """Parse les informations d'une cellule"""
        text = cell.get_text(strip=True)
        style = cell.get('style', '').lower()
        class_attr = cell.get('class', [])
        
        cell_info = {
            'text': text,
            'row': row_idx,
            'col': col_idx,
            'style': style,
            'class': class_attr,
            'type': 'white',
            'editable': True,
            'number': None,
            'clue_direction': None
        }
        
        # Détecter le type de cellule
        is_black = self._is_black_cell(cell, style, class_attr, text)
        is_clue = self._is_clue_cell(text)
        is_numbered = self._is_numbered_cell(text)
        
        if is_black:
            cell_info['type'] = 'black'
            cell_info['editable'] = False
            if is_clue:
                cell_info['clue_direction'] = self._detect_clue_direction(text)
        elif is_clue:
            cell_info['type'] = 'clue'
            cell_info['editable'] = False
            cell_info['clue_direction'] = self._detect_clue_direction(text)
        elif is_numbered:
            cell_info['type'] = 'white'
            cell_info['number'] = self._extract_number(text)
            cell_info['text'] = ''
        elif not text.strip():
            # Case vide = case blanche editable
            cell_info['type'] = 'white'
            cell_info['text'] = ''
        
        return cell_info
    
    def _is_black_cell(self, cell, style, class_attr, text):
        """Détermine si une cellule est une case noire"""
        # Vérifier les classes CSS spécifiques d'Excel
        if isinstance(class_attr, list):
            class_names = ' '.join(class_attr).lower()
            if any(cls in class_names for cls in ['xl95', 'xl96', 'xl97', 'xl98', 'xl99']):
                return True
        
        # Vérifier le style CSS
        if 'background' in style:
            if any(color in style for color in ['black', '#000', '#333', 'rgb(0,0,0)']):
                return True
        
        # Vérifier si la cellule contient des définitions avec flèches
        if text and len(text) > 3:
            arrows = ['→', '↓', '←', '↑', '->', '<-', '↗', '↖', '↙', '↘']
            if any(arrow in text for arrow in arrows):
                return True
        
        return False
    
    def _is_clue_cell(self, text):
        """Détermine si une cellule contient une définition"""
        if not text or len(text) < 3:
            return False
        
        # Chercher des flèches
        arrows = ['→', '↓', '←', '↑', '->', '<-', '↗', '↖', '↙', '↘']
        if any(arrow in text for arrow in arrows):
            return True
        
        # Chercher des patterns de définitions (texte long avec espaces)
        words = text.split()
        if len(words) >= 2 and len(text) > 10:
            return True
        
        return False
    
    def _is_numbered_cell(self, text):
        """Détermine si une cellule contient un numéro de définition"""
        if text and text.isdigit() and 1 <= int(text) <= 99:
            return True
        return False
    
    def _detect_clue_direction(self, text):
        """Détecte la direction d'une définition basée sur les flèches"""
        horizontal_arrows = ['→', '->', '←', '<-']
        vertical_arrows = ['↓', '↑']
        
        for arrow in horizontal_arrows:
            if arrow in text:
                return 'horizontal'
        
        for arrow in vertical_arrows:
            if arrow in text:
                return 'vertical'
        
        return 'horizontal'  # Par défaut
    
    def _extract_number(self, text):
        """Extrait le numéro d'une cellule"""
        if text.isdigit():
            return int(text)
        
        # Chercher des numéros dans du texte mixte
        numbers = re.findall(r'\d+', text)
        if numbers:
            return int(numbers[0])
        
        return None
    
    def _analyze_crossword_structure(self, grid_data):
        """Analyse la structure de la grille pour optimiser l'affichage"""
        if not grid_data:
            return
        
        rows = len(grid_data)
        cols = max(len(row) for row in grid_data) if grid_data else 0
        
        # Normaliser la grille (s'assurer que toutes les lignes ont la même longueur)
        self.grid = []
        
        for row_data in grid_data:
            grid_row = []
            for col_idx in range(cols):
                if col_idx < len(row_data):
                    cell_data = row_data[col_idx]
                    standardized_cell = {
                        'type': cell_data['type'],
                        'text': cell_data['text'],
                        'editable': cell_data['editable'],
                        'number': cell_data['number']
                    }
                else:
                    # Cellule vide par défaut
                    standardized_cell = {
                        'type': 'white',
                        'text': '',
                        'editable': True,
                        'number': None
                    }
                grid_row.append(standardized_cell)
            self.grid.append(grid_row)
        
        # Stocker les données brutes pour débogage
        self.raw_data = {
            'dimensions': f"{rows}x{cols}",
            'total_cells': rows * cols,
            'grid_data': grid_data[:5]  # Limiter pour éviter les gros logs
        }
    
    def _extract_clues_from_grid(self, grid_data):
        """Extrait les définitions des cases de type 'clue' ou 'black'"""
        horizontal_clues = []
        vertical_clues = []
        clue_number = 1
        
        for row_data in grid_data:
            for cell_data in row_data:
                if (cell_data['type'] in ['clue', 'black']) and cell_data['text']:
                    direction = cell_data.get('clue_direction', 'horizontal')
                    
                    # Nettoyer le texte de la définition
                    clue_text = self._clean_clue_text(cell_data['text'])
                    
                    if clue_text:
                        clue_info = {
                            'number': clue_number,
                            'clue': clue_text,
                            'row': cell_data['row'],
                            'col': cell_data['col'],
                            'length': self._estimate_word_length(cell_data, grid_data, direction)
                        }
                        
                        if direction == 'horizontal':
                            horizontal_clues.append(clue_info)
                        else:
                            vertical_clues.append(clue_info)
                        
                        clue_number += 1
        
        self.clues = {
            'horizontal': horizontal_clues,
            'vertical': vertical_clues
        }
        
        # Créer une solution vide
        self._generate_empty_solution()
    
    def _clean_clue_text(self, text):
        """Nettoie le texte d'une définition"""
        # Supprimer les flèches
        arrows = ['→', '↓', '←', '↑', '->', '<-', '↗', '↖', '↙', '↘']
        for arrow in arrows:
            text = text.replace(arrow, '').strip()
        
        # Nettoyer les espaces multiples
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _estimate_word_length(self, clue_cell, grid_data, direction):
        """Estime la longueur d'un mot basé sur sa position"""
        # Pour l'instant, retourner une longueur par défaut
        return 5
    
    def _generate_empty_solution(self):
        """Génère une structure de solution vide"""
        self.solution = []
        for row in self.grid:
            solution_row = []
            for cell in row:
                if cell['type'] == 'white':
                    solution_row.append('')
                else:
                    solution_row.append(None)
            self.solution.append(solution_row)

# Stockage global des données
crossword_data = {}
user_progress = {}

@app.route('/')
def index():
    return render_template('upload.html')

# @app.route('/upload', methods=['POST'])
# def upload_file():
#     if 'file' not in request.files:
#         return jsonify({'error': 'Aucun fichier fourni'}), 400
#
#     file = request.files['file']
#     if file.filename == '':
#         return jsonify({'error': 'Aucun fichier sélectionné'}), 400
#
#     if file and file.filename.lower().endswith(('.htm', '.html')):
#         try:
#             # Lire le contenu du fichier
#             content = file.read().decode('utf-8', errors='ignore')
#
#             # Parser le contenu
#             parser = ExcelHTMLCrosswordParser()
#             data = parser.parse_excel_html(content)
#
#             # Générer un ID unique pour cette grille
#             grid_id = str(uuid.uuid4())
#             crossword_data[grid_id] = data
#
#             return jsonify({'success': True, 'redirect': f'/crossword/{grid_id}'})
#
#         except Exception as e:
#             app.logger.error(f"Erreur lors du parsing: {str(e)}")
#             return jsonify({'error': f'Erreur lors du traitement: {str(e)}'}), 500
#
#     return jsonify({'error': 'Format de fichier non supporté. Utilisez un fichier .htm ou .html'}), 400

def parse_excel_grid(df):
    """
    Transforme un DataFrame Excel en une structure utilisable pour crossword.html.
    - grid : matrice (liste de listes)
    - clues : liste de définitions extraites des cases noires avec texte
    """
    grid = []
    clues = []

    for i, row in df.iterrows():
        grid_row = []
        for j, val in row.items():
            if pd.isna(val):
                grid_row.append("")
            elif val.lower() == 'x':
                continue
            else:
                # Case noire avec définition
                text = str(val).strip()
                grid_row.append("#")
                clues.append({"row": i, "col": j, "text": text})
        if len(grid_row) > 0:
            grid.append(grid_row)
        else:
            break

    return {"grid": grid, "clues": clues}


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier fourni'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400

    # Vérifie extension .xlsx
    if file and file.filename.lower().endswith('.xlsx'):
        try:
            excel_data = pd.read_excel(file, sheet_name=None, header=None)  # toutes les feuilles
            first_sheet = list(excel_data.values())[0]
            # rows = first_sheet.to_dict(orient="records")

            # Transformer
            data = parse_excel_grid(first_sheet)

            # Sauvegarde avec ID
            grid_id = str(uuid.uuid4())
            crossword_data[grid_id] = data

            return jsonify({'success': True, 'redirect': f'/crossword/{grid_id}'})

        except Exception as e:
            app.logger.error(f"Erreur lors du parsing Excel: {str(e)}")
            return jsonify({'error': f'Erreur lors du traitement: {str(e)}'}), 500

    return jsonify({'error': 'Format de fichier non supporté. Utilisez un fichier .xlsx'}), 400

@app.route('/crossword/<grid_id>')
def crossword(grid_id):
    if grid_id not in crossword_data:
        return redirect('/')

    data = crossword_data[grid_id]
    return render_template('crossword.html',
                         grid=data['grid'],
                         clues=data['clues'],
                         grid_id=grid_id)

@app.route('/api/save_progress/<grid_id>', methods=['POST'])
def save_progress(grid_id):
    if grid_id not in crossword_data:
        return jsonify({'error': 'Grille invalide'}), 400
    
    progress_data = request.json
    user_progress[grid_id] = {
        'data': progress_data,
        'timestamp': datetime.now().isoformat()
    }
    
    return jsonify({'success': True})

@app.route('/api/load_progress/<grid_id>')
def load_progress(grid_id):
    if grid_id not in user_progress:
        return jsonify({'progress': {}})
    
    return jsonify({'progress': user_progress[grid_id]['data']})

@app.route('/api/debug/<grid_id>')
def debug_info(grid_id):
    """Endpoint pour déboguer les données de parsing"""
    if grid_id not in crossword_data:
        return jsonify({'error': 'Grille invalide'}), 400
    
    data = crossword_data[grid_id]
    return jsonify({
        'grid_size': f"{len(data['grid'])}x{len(data['grid'][0]) if data['grid'] else 0}",
        'total_clues': len(data['clues']['horizontal']) + len(data['clues']['vertical']),
        'horizontal_clues': data['clues']['horizontal'],
        'vertical_clues': data['clues']['vertical'],
        'raw_data': data.get('raw_data', {}),
        'sample_grid': data['grid'][:3] if data['grid'] else []  # Échantillon des 3 premières lignes
    })

# Filtres Jinja personnalisés
@app.template_filter('tojsonfilter')
def to_json_filter(obj):
    return json.dumps(obj, ensure_ascii=False)

# if __name__ == '__main__':
#     app.run(debug=True, port=5000, host='0.0.0.0', use_reloader=False)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)