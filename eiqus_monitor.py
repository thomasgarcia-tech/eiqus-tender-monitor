import os, json, re, base64, time
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import anthropic
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# ── CONFIG ────────────────────────────────────────────────────
RECIPIENT = os.environ.get("RECIPIENT_EMAIL", "thomas.garcia@eiqus.com")
SENDER    = os.environ.get("SENDER_EMAIL",    "thomas.garcia@eiqus.com")
THRESHOLD = 70

CTX = """EIQUS NGA = acteur hybride santé mentale + innovation deeptech (France).
Protocole PSCE® breveté INPI 21 02798, validé 650+ cas. JEI, Bpifrance DeepTech TRL6.
Modules IA : SCORING, TRACE, REACT, EVA. VR VRET. Biofeedback EEG/HRV/EDA. Médiation équine.
Clients : AG2R La Mondiale, La Banque Postale, Mutuelle des Motards, Château de Versailles, Royal Canin, Pôle Emploi.
Marchés : France (priorité), Italie (Roma GTM), Suisse (Thomas Garcia, Zurich)."""

BATCHES = [
    {"label": "Marchés publics France", "queries": [
        "site:boamp.fr \"santé mentale\" OR \"QVCT\" OR \"RPS\" 2025 2026",
        "\"appel d'offres\" \"risques psychosociaux\" OR \"qualité de vie au travail\" France 2025 2026",
        "\"marché public\" \"EAP\" OR \"soutien psychologique\" France 2025 2026",
        "\"accord-cadre\" \"burn-out\" prévention France 2025 2026",
    ]},
    {"label": "Assureurs & Mutuelles", "queries": [
        "\"appel d'offres\" assureur mutuelle \"santé mentale\" AG2R Malakoff MGEN Harmonie 2025 2026",
        "\"appel d'offres\" \"médiation équine\" OR \"médiation animale\" entreprise France",
        "\"appel d'offres\" \"réalité virtuelle\" OR \"VRET\" santé mentale France 2026",
        "\"bien-être psychologique\" salarié mutuelle prévoyance appel offres 2026",
    ]},
    {"label": "Italie + Suisse", "queries": [
        "\"bando\" OR \"gara appalto\" \"salute mentale\" OR \"benessere aziendale\" 2025 2026",
        "\"pet therapy\" OR \"mediazione equina\" bando appalto Italia 2025 2026",
        "site:simap.ch \"psychische Gesundheit\" OR \"Wohlbefinden\" Ausschreibung 2025 2026",
        "\"santé mentale\" \"appel d'offres\" Suisse assureur 2025 2026",
    ]},
    {"label": "TED Europa + EU", "queries": [
        "site:ted.europa.eu \"mental health\" OR \"employee assistance\" tender 2025 2026",
        "\"procurement\" \"digital mental health\" Europe 2025 2026",
        "\"Ausschreibung\" \"psychische Gesundheit\" Versicherung 2026",
        "\"benessere aziendale\" \"prevenzione burnout\" assicurazione 2025 2026",
    ]},
    {"label": "Grants FR/EU", "queries": [
        "Bpifrance \"Grand Défi\" \"santé mentale\" France 2030 appel projets",
        "ARS \"fonds innovation\" psychiatrie FIOP appel projets 2025 2026",
        "\"Agence du Numérique en Santé\" \"Structures 3.0\" santé mentale 2026",
        "\"Horizon Europe\" HLTH-2026 \"mental health\" digital call 2026",
    ]},
    {"label": "Fondations assureurs", "queries": [
        "\"Fondation AG2R\" OR \"Fondation Apicil\" OR \"Fondation Groupama\" appel projets santé 2026",
        "\"Fondation Malakoff\" OR \"Assurance Maladie\" appel projets santé mentale 2026",
        "\"The Human Safety Net\" Generali OR \"INAIL\" salute mentale 2025 2026",
        "\"Innosuisse\" OR \"Mobiliar\" santé mentale financement Suisse 2026",
    ]},
]

# ── JSON EXTRACTION ───────────────────────────────────────────
def safe_json(text):
    if not text: return []
    for fn in [
        lambda t: json.loads(t.strip()) if t.strip().startswith("[") else (_ for _ in ()).throw(ValueError()),
        lambda t: json.loads(t[t.index("["):t.rindex("]")+1]),
        lambda t: [json.loads(m.group()) for m in re.finditer(r'\{(?:[^{}]|\{[^{}]*\})*\}', t) if json.loads(m.group()).get("title")],
    ]:
        try:
            r = fn(text)
            if isinstance(r, list) and r: return r
        except: continue
    return []

# ── SEARCH ────────────────────────────────────────────────────
def search_batch(batch, client):
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=5000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        system=f"""Tu es agent de veille EIQUS NGA. {CTX}
Utilise web_search pour chaque requête. Retourne UNIQUEMENT un tableau JSON:
[{{"title":"...","organization":"...","org_type":"assureur|mutuelle|public|eu|autre",
"country":"France|Italie|Suisse|EU","deadline":"YYYY-MM-DD ou Non précisé",
"estimated_budget":"montant ou Non précisé","scope_summary":"2 phrases","source_url":"URL directe",
"match_keywords":["k1","k2","k3"]}}]""",
        messages=[{"role": "user", "content":
            f"Segment: {batch['label']}. Exécute ces requêtes:\n"
            + "\n".join(f"Q{i+1}: {q}" for i,q in enumerate(batch["queries"]))
            + "\nRetourne le tableau JSON."
        }],
    )
    return safe_json(" ".join(b.text for b in msg.content if b.type=="text"))

# ── SCORE ─────────────────────────────────────────────────────
def score_items(items, client):
    if not items: return []
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        system=f"""Tu es agent de scoring EIQUS NGA. {CTX}
Score chaque item sur 100:
1.Fit stratégique(30): 30=MH/QVCT/RPS/équine/VR/PSCE® / 22=EAP/burnout / 15=partiel / 8=tangentiel / 0=hors scope
2.Compatibilité offre(20): 20=seul / 15=légère adaptation / 10=partenariat / 0=impossible
3.Valeur institutionnelle(15): 15=grand compte / 12=institution reconnue / 8=ETI / 4=PME / 0=inconnu
4.Potentiel récurrence(15): 15=accord-cadre / 12=reconductible / 8=référence / 4=one-shot / 0=aucun
5.Budget(10): 10=>500K / 7=100-500K / 5=20-100K / 3=<20K / 1=inconnu
6.Faisabilité(10): 10=immédiat / 7=modéré / 4=complexe / 1=difficile / 0=impossible
Ajoute: score(int), score_label(PRIORITAIRE>=85/FORT>=75/BON>=70/REJETÉ<70),
recommendation(GO|GO-PARTNER|SURVEILLER|NO-GO), why_eiqus(1 phrase), action_imm(1 phrase pour Thomas Garcia CSO)
Retourne UNIQUEMENT le tableau JSON complet.""",
        messages=[{"role":"user","content":f"Score ces {len(items)} opportunités:\n{json.dumps(items,ensure_ascii=False)}"}],
    )
    text = next((b.text for b in msg.content if b.type=="text"), "[]")
    scored = safe_json(text)
    return scored or [{**i,"score":70,"score_label":"BON","recommendation":"SURVEILLER",
                       "why_eiqus":"À évaluer.","action_imm":"Vérifier directement."} for i in items]

# ── EMAIL HTML ────────────────────────────────────────────────
def build_email(retained, rejected, scan_date):
    rc = lambda r: {"GO":"#004763","GO-PARTNER":"#336C82","SURVEILLER":"#AFAB92","NO-GO":"#aaa"}.get(r,"#aaa")
    sc = lambda s: "#004763" if s>=85 else "#336C82" if s>=75 else "#56858B"
    medals = ["🥇","🥈","🥉"]
    top3, main = retained[:3], retained[3:]

    top3_rows = ""
    for i,t in enumerate(top3):
        s = t.get("score",0)
        url = t.get("source_url","")
        lnk = f'<a href="{url}" style="font-size:11px;color:#336C82;">→ Voir l\'annonce</a>' if url and url not in ("Non précisé","null","") else ""
        top3_rows += f"""<tr style="border-bottom:2px solid #CCDBE0;vertical-align:top;background:{'#f0f7fa' if i==0 else 'white'};">
<td style="padding:14px 8px;font-size:22px;">{medals[i]}</td>
<td style="padding:14px 10px;">
<div style="font-weight:bold;color:#004763;font-size:13px;">{t.get('title','—')}</div>
<div style="color:#336C82;font-size:11px;margin:3px 0;">{t.get('organization','')} · {t.get('country','')} · Deadline: <strong style="color:#c0392b;">{t.get('deadline','—')}</strong></div>
<div style="font-size:12px;color:#333;font-style:italic;margin:4px 0;">{t.get('why_eiqus','')}</div>
<div style="font-size:11px;color:#004763;font-weight:bold;">→ {t.get('action_imm','')}</div>
<div style="margin-top:9px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
<span style="background:{rc(t.get('recommendation',''))};color:white;border-radius:6px;padding:2px 10px;font-size:11px;font-weight:bold;">{t.get('recommendation','')}</span>
<span style="background:{sc(s)};color:white;border-radius:50%;width:38px;height:38px;display:inline-flex;align-items:center;justify-content:center;font-size:14px;font-weight:bold;">{s}</span>
{lnk}</div></td></tr>"""

    main_rows = ""
    for t in main:
        s = t.get("score",0)
        url = t.get("source_url","")
        lnk = f'<a href="{url}" style="font-size:10px;color:#336C82;">Lien →</a>' if url and url not in ("Non précisé","null","") else "—"
        main_rows += f"""<tr style="border-bottom:1px solid #CCDBE0;vertical-align:top;">
<td style="padding:10px;text-align:center;">
<div style="background:{sc(s)};color:white;border-radius:50%;width:36px;height:36px;display:inline-flex;align-items:center;justify-content:center;font-size:13px;font-weight:bold;">{s}</div>
<div style="font-size:9px;color:{rc(t.get('recommendation',''))};font-weight:bold;">{t.get('recommendation','')}</div></td>
<td style="padding:10px;">
<div style="font-weight:bold;color:#004763;font-size:12px;">{t.get('title','—')}</div>
<div style="color:#336C82;font-size:11px;">{t.get('organization','')} · {t.get('country','')}</div>
<div style="font-size:10px;color:#555;">{t.get('scope_summary','')[:180]}</div>
<div style="font-size:10px;color:#004763;font-style:italic;">→ {t.get('action_imm','')}</div></td>
<td style="padding:10px;font-size:10px;color:#c0392b;font-weight:bold;">{t.get('deadline','—')}</td>
<td style="padding:10px;font-size:10px;">{t.get('estimated_budget','—')}</td>
<td style="padding:10px;">{lnk}</td></tr>"""

    watch_rows = "".join(f"""<tr style="border-bottom:1px solid #e8e8e8;">
<td style="padding:6px;color:#888;font-size:11px;font-weight:bold;">{t.get('title','—')}</td>
<td style="padding:6px;color:#aaa;font-size:10px;">{t.get('organization','')} · {t.get('country','')}</td>
<td style="padding:6px;color:#bbb;font-size:10px;">Score: {t.get('score','—')}</td></tr>""" for t in rejected)

    go = sum(1 for t in retained if t.get("recommendation")=="GO")
    gp = sum(1 for t in retained if t.get("recommendation")=="GO-PARTNER")

    return f"""<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;background:#f0f4f6;margin:0;padding:16px;">
<div style="max-width:880px;margin:0 auto;background:white;border-radius:10px;overflow:hidden;">
<div style="background:#004763;padding:24px 32px;">
<h1 style="color:white;margin:0;font-size:21px;">EIQUS Tender Monitor — Weekly Digest</h1>
<p style="color:#99B6C1;margin:5px 0 0;font-size:12px;">{scan_date} · Lundi 01:00 CET · FR · IT · CH · EU · 6 segments · 24 requêtes</p></div>
<div style="background:#EEECE0;padding:12px 32px;font-size:13px;color:#333;">
<strong>{len(retained)+len(rejected)}</strong> détectées · <strong>{len(retained)}</strong> retenues ≥70 · <strong>{go}</strong> GO · <strong>{gp}</strong> GO-PARTNER</div>
{"<div style='padding:20px 32px 10px;'><h2 style='color:#004763;font-size:15px;border-bottom:2px solid #004763;padding-bottom:5px;margin:0 0 12px;'>🎯 TOP 3 — ACTION IMMÉDIATE</h2><table style='width:100%;border-collapse:collapse;'>" + top3_rows + "</table></div>" if top3 else ""}
{"<div style='padding:14px 32px 10px;'><h2 style='color:#336C82;font-size:14px;border-bottom:2px solid #336C82;padding-bottom:4px;margin:0 0 10px;'>📋 OPPORTUNITÉS PRINCIPALES</h2><table style='width:100%;border-collapse:collapse;font-size:12px;'><thead><tr style='background:#CCDBE0;'><th style='padding:8px;color:#004763;font-size:10px;'>Score</th><th style='padding:8px;color:#004763;font-size:10px;text-align:left;'>Opportunité</th><th style='padding:8px;color:#004763;font-size:10px;'>Deadline</th><th style='padding:8px;color:#004763;font-size:10px;'>Budget</th><th style='padding:8px;color:#004763;font-size:10px;'>Lien</th></tr></thead><tbody>" + main_rows + "</tbody></table></div>" if main else ""}
{"<div style='padding:12px 32px 18px;'><h3 style='color:#AFAB92;font-size:12px;margin:0 0 6px;'>👁 À SURVEILLER</h3><table style='width:100%;border-collapse:collapse;'>" + watch_rows + "</table></div>" if watch_rows else ""}
<div style="background:#004763;padding:12px 32px;font-size:10px;color:#99B6C1;">
EIQUS NGA · Thomas Garcia CSO · thomas.garcia@eiqus.com · +41 76 453 0485 · PSCE® INPI 21 02798 · JEI · Bpifrance DeepTech TRL6</div>
</div></body></html>"""

# ── SEND EMAIL ────────────────────────────────────────────────
def send_email(subject, html):
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GMAIL_REFRESH_TOKEN"],
        client_id=os.environ["GMAIL_CLIENT_ID"],
        client_secret=os.environ["GMAIL_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/gmail.send"],
    )
    service = build("gmail", "v1", credentials=creds)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = SENDER
    msg["To"]      = RECIPIENT
    msg.attach(MIMEText(html, "html", "utf-8"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    r = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    print(f"✅ Email envoyé — ID: {r.get('id')}")

# ── MAIN ──────────────────────────────────────────────────────
def main():
    today = date.today().strftime("%A %d %B %Y")
    print(f"{'='*50}\nEIQUS Tender Monitor — {today}\n{'='*50}")
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    print("\n[1/4] Recherche — 6 segments, 24 requêtes...")
    all_raw = []
    for i, batch in enumerate(BATCHES):
        print(f"  Lot {i+1}/6 — {batch['label']}...")
        try:
            r = search_batch(batch, client)
            print(f"  → {len(r)} résultats")
            all_raw.extend(r)
        except Exception as e:
            print(f"  ⚠️ Erreur: {e}")
        if i < len(BATCHES)-1:
            time.sleep(1.5)

    print(f"\n[2/4] Déduplication...")
    seen, deduped = set(), []
    for item in all_raw:
        k = (item.get("title") or "").lower()[:70]
        if k and k not in seen:
            seen.add(k); deduped.append(item)
    print(f"  {len(deduped)} uniques sur {len(all_raw)} bruts")

    print(f"\n[3/4] Scoring {len(deduped)} opportunités...")
    scored = score_items(deduped, client)
    retained = sorted([t for t in scored if (t.get("score") or 0) >= THRESHOLD],
                      key=lambda x: x.get("score",0), reverse=True)
    rejected = [t for t in scored if (t.get("score") or 0) < THRESHOLD][:5]
    print(f"  ✅ {len(retained)} retenues ≥{THRESHOLD} | 👁 {len(rejected)} sous seuil")

    print("\n[4/4] Envoi email...")
    html = build_email(retained, rejected, today)
    subject = f"EIQUS Tender Monitor — {today} ({len(retained)} opportunités ≥{THRESHOLD})"
    send_email(subject, html)
    print("\n✅ Terminé avec succès!")

if __name__ == "__main__":
    main()
