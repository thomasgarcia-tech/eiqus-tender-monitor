import os, json
import anthropic
from searcher import safe_json

SCORE_SYSTEM = """Tu es agent de scoring EIQUS NGA. Scoring STRICT.

GRILLE 6 CRITÈRES (total 100) :
1. Fit stratégique EIQUS — 30 : 30=coeur MH/QVCT/RPS/équine/VR/PSCE® / 22=fort EAP/burnout / 15=partiel / 8=tangentiel / 0=hors scope
2. Compatibilité offre — 20 : 20=seul / 15=légère adaptation / 10=partenariat / 5=éloigné / 0=impossible
3. Valeur institutionnelle — 15 : 15=grand compte national / 12=institution reconnue / 8=ETI / 4=PME / 0=inconnu
4. Potentiel récurrence — 15 : 15=accord-cadre pluriannuel / 12=reconductible / 8=référence / 4=one-shot / 0=aucun
5. Budget — 10 : 10=>500K / 7=100-500K / 5=20-100K / 3=<20K / 1=inconnu
6. Faisabilité — 10 : 10=immédiat / 7=modéré / 4=complexe / 1=difficile / 0=impossible

Ajoute à chaque item :
- score (int 0-100)
- score_breakdown {fit_strategique,compatibilite_offre,valeur_institutionnelle,potentiel_recurrence,budget,faisabilite}
- score_label : PRIORITAIRE>=85 / FORT>=75 / BON>=70 / REJETÉ<70
- recommendation : GO | GO-PARTNER | SURVEILLER | NO-GO
- why_eiqus : 1 phrase impactante
- action_imm : 1 action immédiate pour Thomas Garcia CSO

Retourne UNIQUEMENT le tableau JSON complet [ ... ]. Rien d'autre."""

def score_items(items, context):
    if not items:
        return []
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        system=SCORE_SYSTEM,
        messages=[{"role": "user", "content":
            f"Score ces {len(items)} opportunités pour EIQUS NGA :\n{json.dumps(items, ensure_ascii=False)}"
        }],
    )
    text = next((b.text for b in msg.content if b.type == "text"), "[]")
    scored = safe_json(text)
    if not scored:
        scored = [{**i, "score": 70, "score_label": "BON", "recommendation": "SURVEILLER",
                   "why_eiqus": "À évaluer.", "action_imm": "Vérifier directement."} for i in items]
    return scored

def filter_and_sort(scored, threshold):
    retained = sorted([t for t in scored if (t.get("score") or 0) >= threshold],
                      key=lambda x: x.get("score", 0), reverse=True)
    rejected = [t for t in scored if (t.get("score") or 0) < threshold][:5]
    return retained, rejected
