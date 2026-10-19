# Démarrage du rapport Power BI

Après avoir exécuté `python src/quality_monitor.py`, chargez les cinq CSV de `outputs/` dans Power BI Desktop.

## Modèle conseillé

Utilisez `table_quality` comme dimension de table, avec une relation un-à-plusieurs vers `check_results` et une autre vers `quality_issues`, via `table_name`. `column_quality` est une table de profilage au grain table-colonne ; elle peut être filtrée par une dimension de table dédiée créée dans Power Query à partir des valeurs distinctes de `table_name`.

`check_results` contient une ligne par règle. `quality_issues` ne contient que les règles en échec. `column_quality` conserve le taux de valeurs manquantes et la cardinalité distincte pour chaque colonne. Ces grains sont différents : ne reliez pas les tables de faits entre elles par une relation plusieurs-à-plusieurs.

## Page de suivi

Placez en haut les cartes « Score qualité global », « Anomalies ouvertes », « Contrôles en échec » et « Lignes profilées ». Ajoutez ensuite un graphique en barres du score par table, une matrice catégorie × priorité, un tableau des anomalies filtrable et un graphique de complétude des colonnes.

Les mesures DAX proposées dans `Measures.dax` sont des points de départ. Vérifiez les relations et le comportement des filtres dans votre modèle avant de publier le rapport.
