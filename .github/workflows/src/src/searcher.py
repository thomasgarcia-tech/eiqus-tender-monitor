import os, json, re
from datetime import date
import anthropic

def get_client():
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SEARCH_SYSTEM = """Tu es agent de veille spécialisé EIQUS NGA.
Utilise web_search pour exécuter chaque requête fournie.
Pour chaque résultat, retourne cet objet JSON :
{
  "title": "intitulé exact",
  "organization": "organisme émetteur",
  "org_type": "assureur|mutuelle|entreprise|public|hopital|fondation|eu|autre",
  "type_ao": "Appel d'offres|Appel a projet|RFP|Concours|Grant",
  "country": "France|Italie|Suisse|EU",
  "region": "région ou ville ou vide",
  "deadline": "YYYY-MM-DD ou Non précisé",
  "estimated_budget": "montant ou Non précisé",
  "scope_summary": "Ce qui est demandé. Pourquoi EIQUS est pertinent.",
  "source_url": "URL directe vers la page officielle",
  "match_keywords": ["mot1","mot2","mot3"]
}
Retourne UNIQUEMENT un tableau JSON valide [ ... ]. Rien d'autre."""

def safe_json(text):
    if not text:
        return []
    tries = [
        lambda t: json.loads(t.strip()) if t.strip().startswith("[") else (_ for _ in ()).throw(ValueError()),
        lambda t: json.loads(t[t.index("["):t.rindex("]")+1]),
        lambda t: [json.loads(m.group()) for m in re.finditer(r'\{(?:[^{}]|\{[^{}]*\})*\}', t) if json.loads(m.group()).get("title")],
    ]
    for fn in tries:
        try:
            r = fn(text)
            if isinstance(r, list) and r:
                return r
        except:
            continue
    return []

def search_batch(batch, context):
    client = get_client()
    today = date.today().strftime("%d/%m/%Y")
    queries = batch["queries"]
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=6000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        system=SEARCH_SYSTEM,
        messages=[{"role": "user", "content":
            f"Aujourd'hui : {today}. Segment : {batch['label']}.\n"
            + "\n".join(f"Q{i+1}: {q}" for i, q in enumerate(queries))
            + "\n\nRetourne le tableau JSON. [ ... ]"
        }],
    )
    text = " ".join(b.text for b in msg.content if b.type == "text")
    return safe_json(text)
