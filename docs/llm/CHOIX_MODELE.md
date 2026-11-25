# Choix du générateur LLM

Le notebook a été écrit avec **Qwen2.5-7B-Instruct** (décembre 2024). Depuis, des
modèles deux à trois fois plus petits font mieux sur les benchmarks publics, à licence
comparable et pour une mémoire GPU bien inférieure. Le changement a été fait avant la
génération des 115 QCM ; il n'a rien coûté et évite de dépenser le GPU sur un modèle
dépassé.

Ce document justifie le choix retenu, liste les alternatives examinées et décrit
l'ablation à faire pour trancher **sur notre corpus** plutôt que sur des fiches modèles.

## 1. Ce qu'on demande au générateur

| Critère | Exigence | Pourquoi |
|---|---|---|
| Licence | ouverte, sans formulaire | le dépôt doit rester exécutable par un correcteur |
| Taille | ≤ 4 B paramètres | tenir sur une T4 15 Go en 4 bits, avec marge pour le batch |
| Français | bon niveau | cours et QCM en français |
| JSON | respect strict du format | un JSON invalide est un QCM perdu (compté à l'étape 5.5) |
| Contexte | ≥ 8 k tokens | passage (≤ 460 tokens) + prompt few-shot (~1 500 tokens) |

## 2. Candidats examinés

Données tirées des fiches Hugging Face des modèles (consulté en novembre 2025) ; les
scores sont ceux **annoncés par les auteurs**, pas mesurés sur notre corpus.

| Modèle | Paramètres | Licence | Contexte | Langues | Éléments de comparaison |
|---|---|---|---|---|---|
| **Qwen3-4B-Instruct-2507** | 4,0 B (3,6 B hors embeddings) | Apache 2.0 | 262 k | multilingue | MMLU-Pro **69,6**, GPQA **62,0**, ZebraLogic 80,2, MultiIF 69,0, MMLU-ProX 61,6. Mode non-thinking uniquement. |
| SmolLM3-3B | 3 B | Apache 2.0 | 64 k (128 k YaRN) | 6, dont **français natif** | Global-MMLU 53,5 ; français (base) MLMM-HellaSwag **63,9** contre 61,0 pour Qwen3-4B-Base. Mode *thinking* désactivable. |
| Gemma 3 4B IT | 4 B | **Gemma Terms** (accès sur acceptation, non OSI) | 128 k | 140+ | Global-MMLU-Lite 57,0, MGSM 34,7, WMT24++ 48,4 (modèle pré-entraîné) ; multimodal (chargement un peu plus lourd). |
| Qwen3-1.7B | 1,7 B | Apache 2.0 | 32 k | multilingue | Pour tests rapides et ablations « modèle minuscule ». |
| Phi-4-mini-instruct | 3,8 B | MIT | 128 k | 23, dont français | Très bon en anglais et raisonnement ; la fiche reconnaît un entraînement **majoritairement anglais** et de moins bonnes performances hors anglais. |
| EuroLLM-1.7B-Instruct | 1,65 B | Apache 2.0 | — | 35, dont français | Excellent en traduction (FLORES 86,9), mais général faible : ARC 0,350 contre 0,362 pour Gemma-2B ; pas aligné. |
| Lucie-7B-Instruct-v1.1 | 7 B | Apache 2.0 | 32 k (22 k utiles) | fr/en | Français natif, mais 7 B (aucun gain de calcul) et instruction tuning léger ; la fiche déconseille un usage en pipeline sans affinage. |
| Qwen2.5-7B-Instruct | 7,6 B | Apache 2.0 | 128 k | 29 | **Remplacé** : 90 % de poids en plus pour des scores inférieurs sur les benchmarks publiés par Qwen. |
| Qwen3-30B-A3B-Instruct-2507 | 30 B totaux, 3 B actifs | Apache 2.0 | 262 k | multilingue | Moins de FLOPs par token, mais ~18 Go en 4 bits : **ne tient pas sur une T4 15 Go** sans déport CPU, donc plus lent ici. |
| Ministral-3B-2410 | 3 B | Mistral Research (non commerciale) | — | multilingue | Poids sous conditions et licence de recherche : exclu pour un dépôt réutilisable (à vérifier si besoin). |

Estimation de mémoire en NF4 (≈ 0,55 Go par milliard de paramètres, plus le cache KV) :
Qwen2.5-7B ≈ **4,2 Go**, Qwen3-4B ≈ **2,5 Go**, SmolLM3-3B ≈ **2,0 Go**. La T4 en a 15 :
la marge sert à augmenter le batch ou la longueur de sortie.

## 3. Décision

1. **Défaut : `Qwen/Qwen3-4B-Instruct-2507`.**
   Apache 2.0, 4 B, 262 k de contexte, mode non-thinking (sortie JSON directe, pas de
   bloc `<think>` à filtrer). Les scores annoncés dépassent Qwen2.5-7B pour ~55 % de
   poids. C'est le meilleur compromis qualité / mémoire / licence.
2. **Ablation française : `HuggingFaceTB/SmolLM3-3B`**, `enable_thinking=False`.
   Apache 2.0, français natif, benchmarks français supérieurs à Qwen3-4B pour le modèle
   de base. Il teste l'hypothèse « un modèle plus petit mais francophone fait mieux sur
   des cours de C ».
3. **Variante à licence non OSI : `google/gemma-3-4b-it`**, seulement si l'acceptation
   des Gemma Terms est acceptable pour le rendu. Bon multilingue, chargement multimodal.
4. **Tests rapides : `Qwen/Qwen3-1.7B`** avec `QCM_LLM_N=5`, pour valider le prompt et
   le parsing sans consommer de quota.

À l'oral, la justification tient en une phrase : *« même licence, moitié des poids,
meilleurs scores annoncés ; le choix est vérifié par une ablation sur 40 passages. »*

## 4. Comment changer de modèle

Le nom est un paramètre, et le cache est **étiqueté par modèle** : un cache produit par
un autre modèle est refusé plutôt que réutilisé silencieusement.

```bash
# défaut (Qwen3-4B-Instruct-2507)
QCM_LLM_MODEL=Qwen/Qwen3-4B-Instruct-2507

# ablation SmolLM3, cache séparé pour ne rien écraser
QCM_LLM_MODEL=HuggingFaceTB/SmolLM3-3B \
QCM_LLM_CACHE=outputs/qcm/qcm_llm_smollm3.jsonl \
QCM_LLM_BRUT=outputs/qcm/llm_brut_smollm3.jsonl

# test rapide sur 5 passages
QCM_LLM_N=5 QCM_LLM_MODEL=Qwen/Qwen3-1.7B
```

Variables reconnues par l'étape 5 : `QCM_LLM_MODEL`, `QCM_LLM_CACHE`, `QCM_LLM_BRUT`,
`QCM_LLM_N`, `QCM_ALLOW_CPU` (tests hors GPU). Chaque QCM enregistre son champ
`modele`, et `scripts/verifier_sorties.py` refuse un cache qui mélange deux modèles.

## 5. Ablation à faire sur le corpus (GPU)

Les scores des fiches ne disent rien de la génération de QCM sur un cours de C. Le
protocole, une fois le GPU disponible :

1. générer avec Qwen3-4B sur les **40 premiers passages** de l'échantillon, cache dédié ;
2. idem avec SmolLM3-3B (`enable_thinking=False`), cache dédié ;
3. faire passer les deux jeux par **les mêmes** contrôles de forme et le même validateur
   (mêmes modèles, mêmes seuils) ;
4. comparer : format JSON valide, couverture, conformité de forme, passage de V1/V2/V3,
   taux d'acceptation, longueur moyenne des questions, temps par QCM.

Critère de décision : à taux d'acceptation comparable, garder le modèle qui produit le
plus de QCM acceptés par minute de GPU. Si SmolLM3 fait jeu égal, le préférer pour son
français natif et sa taille.

*État : Qwen3-4B exécuté sur 115 QCM (95,8 % valides) ; SmolLM3 non exécuté.*

## 6. Sources

- Qwen3-4B-Instruct-2507 : <https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507>
- Qwen3 Technical Report : <https://arxiv.org/abs/2505.09388>
- SmolLM3-3B : <https://huggingface.co/HuggingFaceTB/SmolLM3-3B>
- Gemma 3 4B IT : <https://huggingface.co/google/gemma-3-4b-it>
- Phi-4-mini-instruct : <https://huggingface.co/microsoft/Phi-4-mini-instruct>
- EuroLLM-1.7B-Instruct : <https://huggingface.co/utter-project/EuroLLM-1.7B-Instruct>
- Lucie-7B-Instruct-v1.1 : <https://huggingface.co/OpenLLM-France/Lucie-7B-Instruct-v1.1>
- Qwen2.5-7B-Instruct (référence remplacée) : <https://huggingface.co/Qwen/Qwen2.5-7B-Instruct>
