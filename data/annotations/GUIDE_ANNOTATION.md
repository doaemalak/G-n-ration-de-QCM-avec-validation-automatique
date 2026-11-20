# Guide d'annotation des QCM

Merci de remplir **votre** grille (`grille_evaluateur_A.csv` ou `grille_evaluateur_B.csv`) **seul·e**, sans en parler avec l'autre évaluateur avant d'avoir terminé.
**N'ouvrez pas `cle_echantillon.csv`** : il indique quelle méthode a produit chaque QCM et si le filtre l'a accepté.

Pour chaque ligne : lisez le **passage**, puis la question, les options A à D et la bonne réponse indiquée.
Jugez le QCM **par rapport au passage**, comme un enseignant qui vérifierait une question d'examen sur ce cours.

## clarte : 1, 2 ou 3
- **3** : la question se comprend du premier coup.
- **2** : compréhensible avec effort (formulation maladroite, faute, phrase tronquée, mot étrange).
- **1** : incompréhensible, ou plusieurs lectures possibles.

## difficulte : 1, 2 ou 3
Pour un étudiant qui **a étudié ce cours** :
- **1** : facile, ou réponse devinable sans connaître le cours (par exemple, distracteurs absurdes).
- **2** : moyenne.
- **3** : difficile, il faut avoir bien compris.

## unicite : 1 ou 0
- **1** : **une seule** option est correcte d'après le passage, **et** c'est la bonne réponse indiquée.
- **0** : aucune option n'est correcte, **ou** plusieurs le sont, **ou** la bonne réponse indiquée est fausse.

Exemple. Question « Complétez : un tableau à deux _____ est un tableau de tableaux », options *size, dimensions, sizeof, tailles*, réponse indiquée *dimensions*.
« tailles » n'est pas strictement synonyme mais pourrait se défendre : si vous hésitez sérieusement, mettez **0** et expliquez en commentaire.

## commentaire (facultatif)
Notez en quelques mots le défaut observé : « deux bonnes réponses », « distracteurs hors sujet », « phrase tronquée », « réponse fausse »…

Remplissez **toutes** les lignes. Enregistrez au même format (CSV, séparateur « ; »).
