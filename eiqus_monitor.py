import os
import json
import re
import base64
import time
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import anthropic
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

RECIPIENT = os.environ.get("RECIPIENT_EMAIL", "thomas.garcia@eiqus.com")
SENDER = os.environ.get("SENDER_EMAIL", "thomas.garcia@eiqus.com")
THRESHOLD = 70

CTX = (
    "EIQUS NGA = acteur hybride sante mentale + innovation deeptech France. "
    "Protocole PSCE brevet INPI 21 02798, valide 650+ cas. JEI, Bpifrance DeepTech TRL6. "
    "Modules IA: SCORING, TRACE, REACT, EVA. VR VRET. Biofeedback EEG/HRV/EDA. Mediation equine. "
    "Clients: AG2R La Mondiale, La Banque Postale, Mutuelle des Motards, Chateau de Versailles. "
    "Marches: France (priorite), Italie (Roma GTM), Suisse (Thomas Garcia, Zurich)."
)

BATCHES = [
    {"label": "Marches publics France", "queries": [
        "site:boamp.fr sante mentale QVCT RPS 2025 2026",
        "appel offres risques psychosociaux qualite vie travail France 2025 2026",
        "marche public EAP soutien psychologique France 2025 2026",
        "accord-cadre burn-out prevention France 2025 2026",
    ]},
    {"label": "Assureurs Mutuelles", "queries": [
        "appel offres assureur mutuelle sante mentale AG2R Malakoff MGEN Harmonie 2025 2026",
        "appel offres mediation equine mediation animale entreprise France",
        "appel offres realite virtuelle VRET sante mentale France 2026",
        "bien-etre psychologique salarie mutuelle prevoyance 2026",
    ]},
    {"label": "Italie Suisse", "queries": [
        "bando gara appalto salute mentale benessere aziendale 2025 2026",
        "pet therapy mediazione equina bando appalto Italia 2025 2026",
        "simap.ch psychische Gesundheit Wohlbefinden Ausschreibung 2025 2026",
        "sante mentale appel offres Suisse assureur 2025 2026",
    ]},
    {"label": "TED EU", "queries": [
        "ted.europa.eu mental health employee assistance tender 2025 2026",
        "procurement digital mental health Europe 2025 2026",
        "Ausschreibung psychische Gesundheit Versicherung 2026",
        "benessere aziendale prevenzione burnout assicurazione 2025 2026",
    ]},
    {"label": "Grants FR EU", "queries": [
        "Bpifrance Grand Defi sante mentale France 2030 appel projets",
        "ARS fonds innovation psychiatrie FIOP appel projets 2025 2026",
        "Agence Numerique Sante Structures 3.0 sante mentale 2026",
        "Horizon Europe HLTH-2026 mental health digital call 2026",
    ]},
    {"label": "Fondations", "queries": [
        "Fondation AG2R Fondation Apicil Fondation Groupama appel projets sante 2026",
        "Fondation Malakoff Assurance Maladie appel projets sante mentale 2026",
        "Human Safety Net Generali INAIL salute mentale 2025 2026",
        "Innosuisse Mobiliar sante mentale financement Suisse 2026",
    ]},
]


def safe_json(text):
    if not text:
        return []
    # Strategy 1: direct parse
    try:
        t = text.strip()
        if t.startswith("["):
            return json.loads(t)
    except Exception:
        pass
    # Strategy 2: find brackets
    try:
        s = text.index("[")
        e = text.rindex("]")
        return json.loads(text[s:e + 1])
    except Exception:
        pass
    # Strategy 3: extract objects
    results = []
    for m in re.finditer(r'\{(?:[^{}]|\{[^{}]*\})*\}', text):
        try:
            o = json.loads(m.group())
            if o.get("title"):
                results.append(o)
        except Exception:
            pass
    return results


def search_batch(batch, client):
    system = (
        "Tu es agent de veille EIQUS NGA. " + CTX + "\n"
        "Utilise web_search pour chaque requete fournie. "
        "Retourne UNIQUEMENT un tableau JSON valide avec ces champs: "
        "title, organization, country (France|Italie|Suisse|EU), "
        "deadline (YYYY-MM-DD ou Non precis), estimated_budget, "
        "scope_summary (2 phrases), source_url, match_keywords (liste). "
        "Commence par [ et termine par ]. Rien d autre."
    )
    queries = batch["queries"]
    user_msg = "Segment: " + batch["label"] + ".\n"
    for i, q in enumerate(queries):
        user_msg += "Q" + str(i + 1) + ": " + q + "\n"
    user_msg += "\nRetourne le tableau JSON."

    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=5000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        system=system,
        messages=[{"role": "user", "content": user_msg}],
    )
    text = " ".join(b.text for b in msg.content if b.type == "text")
    return safe_json(text)


def score_items(items, client):
    if not items:
        return []
    system = (
        "Tu es agent de scoring EIQUS NGA. " + CTX + "\n"
        "Score chaque item sur 100:\n"
        "1.Fit strategique(30): 30=MH/QVCT/RPS/equine/VR/PSCE, 22=EAP/burnout, 15=partiel, 8=tangentiel, 0=hors scope\n"
        "2.Compatibilite(20): 20=seul, 15=adaptation, 10=partenariat, 0=impossible\n"
        "3.Institution(15): 15=grand compte, 12=reconnu, 8=ETI, 4=PME, 0=inconnu\n"
        "4.Recurrence(15): 15=accord-cadre, 12=reconductible, 8=reference, 4=one-shot, 0=aucun\n"
        "5.Budget(10): 10=>500K, 7=100-500K, 5=20-100K, 3=<20K, 1=inconnu\n"
        "6.Faisabilite(10): 10=immediat, 7=modere, 4=complexe, 1=difficile, 0=impossible\n"
        "Ajoute pour chaque item: score (int), score_label (PRIORITAIRE>=85/FORT>=75/BON>=70/REJETE<70), "
        "recommendation (GO ou GO-PARTNER ou SURVEILLER ou NO-GO), "
        "why_eiqus (1 phrase), action_imm (1 phrase pour Thomas Garcia CSO).\n"
        "Retourne UNIQUEMENT le tableau JSON complet. Commence par [. Rien d autre."
    )
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        system=system,
        messages=[{"role": "user", "content": "Score ces " + str(len(items)) + " opportunites:\n" + json.dumps(items, ensure_ascii=False)}],
    )
    text = next((b.text for b in msg.content if b.type == "text"), "[]")
    scored = safe_json(text)
    if not scored:
        scored = []
        for item in items:
            item["score"] = 70
            item["score_label"] = "BON"
            item["recommendation"] = "SURVEILLER"
            item["why_eiqus"] = "A evaluer."
            item["action_imm"] = "Verifier directement."
            scored.append(item)
    return scored


def build_email(retained, rejected, scan_date):
    go_count = sum(1 for t in retained if t.get("recommendation") == "GO")
    gp_count = sum(1 for t in retained if t.get("recommendation") == "GO-PARTNER")
    total = len(retained) + len(rejected)

    def score_color(s):
        if s >= 85:
            return "#004763"
        if s >= 75:
            return "#336C82"
        return "#56858B"

    def rec_color(r):
        colors = {"GO": "#004763", "GO-PARTNER": "#336C82", "SURVEILLER": "#AFAB92", "NO-GO": "#aaa"}
        return colors.get(r, "#aaa")

    medals = ["&#127945;", "&#127946;", "&#127947;"]
    top3 = retained[:3]
    main = retained[3:]

    # Build top3 rows
    top3_html = ""
    for i, t in enumerate(top3):
        s = t.get("score", 0)
        bg = "#f0f7fa" if i == 0 else "white"
        url = t.get("source_url", "")
        link = ""
        if url and url not in ("Non precis", "null", ""):
            link = '<a href="' + url + '" style="font-size:11px;color:#336C82;">Voir annonce</a>'
        top3_html += (
            '<tr style="border-bottom:2px solid #CCDBE0;vertical-align:top;background:' + bg + ';">'
            '<td style="padding:14px 8px;font-size:20px;">' + medals[i] + '</td>'
            '<td style="padding:14px 10px;">'
            '<div style="font-weight:bold;color:#004763;font-size:13px;">' + str(t.get("title", "—")) + '</div>'
            '<div style="color:#336C82;font-size:11px;margin:3px 0;">' + str(t.get("organization", "")) + ' &middot; ' + str(t.get("country", "")) + ' &middot; Deadline: <strong style="color:#c0392b;">' + str(t.get("deadline", "—")) + '</strong></div>'
            '<div style="font-size:12px;font-style:italic;margin:4px 0;">' + str(t.get("why_eiqus", "")) + '</div>'
            '<div style="font-size:11px;color:#004763;font-weight:bold;">&rarr; ' + str(t.get("action_imm", "")) + '</div>'
            '<div style="margin-top:8px;">'
            '<span style="background:' + rec_color(t.get("recommendation", "")) + ';color:white;border-radius:6px;padding:2px 10px;font-size:11px;font-weight:bold;">' + str(t.get("recommendation", "")) + '</span> '
            '<span style="background:' + score_color(s) + ';color:white;border-radius:50%;width:36px;height:36px;display:inline-flex;align-items:center;justify-content:center;font-size:13px;font-weight:bold;">' + str(s) + '</span> '
            + link +
            '</div>'
            '</td></tr>'
        )

    # Build main rows
    main_html = ""
    for t in main:
        s = t.get("score", 0)
        url = t.get("source_url", "")
        link = "—"
        if url and url not in ("Non precis", "null", ""):
            link = '<a href="' + url + '" style="font-size:10px;color:#336C82;">Lien</a>'
        main_html += (
            '<tr style="border-bottom:1px solid #CCDBE0;vertical-align:top;">'
            '<td style="padding:10px;text-align:center;">'
            '<div style="background:' + score_color(s) + ';color:white;border-radius:50%;width:34px;height:34px;display:inline-flex;align-items:center;justify-content:center;font-size:12px;font-weight:bold;">' + str(s) + '</div>'
            '<div style="font-size:9px;color:' + rec_color(t.get("recommendation", "")) + ';font-weight:bold;">' + str(t.get("recommendation", "")) + '</div>'
            '</td>'
            '<td style="padding:10px;">'
            '<div style="font-weight:bold;color:#004763;font-size:12px;">' + str(t.get("title", "—")) + '</div>'
            '<div style="color:#336C82;font-size:11px;">' + str(t.get("organization", "")) + ' &middot; ' + str(t.get("country", "")) + '</div>'
            '<div style="font-size:10px;color:#555;">' + str(t.get("scope_summary", ""))[:180] + '</div>'
            '<div style="font-size:10px;color:#004763;font-style:italic;">&rarr; ' + str(t.get("action_imm", "")) + '</div>'
            '</td>'
            '<td style="padding:10px;font-size:10px;color:#c0392b;font-weight:bold;">' + str(t.get("deadline", "—")) + '</td>'
            '<td style="padding:10px;font-size:10px;">' + str(t.get("estimated_budget", "—")) + '</td>'
            '<td style="padding:10px;">' + link + '</td>'
            '</tr>'
        )

    # Build watch rows
    watch_html = ""
    for t in rejected:
        watch_html += (
            '<tr style="border-bottom:1px solid #e8e8e8;">'
            '<td style="padding:6px;color:#888;font-size:11px;font-weight:bold;">' + str(t.get("title", "—")) + '</td>'
            '<td style="padding:6px;color:#aaa;font-size:10px;">' + str(t.get("organization", "")) + ' &middot; Score: ' + str(t.get("score", "")) + '</td>'
            '</tr>'
        )

    html = """<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;background:#f0f4f6;margin:0;padding:16px;">
<div style="max-width:880px;margin:0 auto;background:white;border-radius:10px;overflow:hidden;">
<div style="background:#004763;padding:24px 32px;">
<h1 style="color:white;margin:0;font-size:21px;">EIQUS Tender Monitor &mdash; Weekly Digest</h1>
<p style="color:#99B6C1;margin:5px 0 0;font-size:12px;">""" + scan_date + """ &middot; Lundi 01:00 CET &middot; FR IT CH EU &middot; 6 segments &middot; 24 requetes</p>
</div>
<div style="background:#EEECE0;padding:12px 32px;font-size:13px;color:#333;">
<strong>""" + str(total) + """</strong> detectees &middot;
<strong>""" + str(len(retained)) + """</strong> retenues &ge;70 &middot;
<strong>""" + str(go_count) + """</strong> GO &middot;
<strong>""" + str(gp_count) + """</strong> GO-PARTNER
</div>"""

    if top3:
        html += """
<div style="padding:20px 32px 10px;">
<h2 style="color:#004763;font-size:15px;border-bottom:2px solid #004763;padding-bottom:5px;margin:0 0 12px;">
TOP 3 &mdash; ACTION IMMEDIATE</h2>
<table style="width:100%;border-collapse:collapse;">""" + top3_html + """</table>
</div>"""

    if main:
        html += """
<div style="padding:14px 32px 10px;">
<h2 style="color:#336C82;font-size:14px;border-bottom:2px solid #336C82;padding-bottom:4px;margin:0 0 10px;">
OPPORTUNITES PRINCIPALES</h2>
<table style="width:100%;border-collapse:collapse;font-size:12px;">
<thead><tr style="background:#CCDBE0;">
<th style="padding:8px;font-size:10px;">Score</th>
<th style="padding:8px;font-size:10px;text-align:left;">Opportunite</th>
<th style="padding:8px;font-size:10px;">Deadline</th>
<th style="padding:8px;font-size:10px;">Budget</th>
<th style="padding:8px;font-size:10px;">Lien</th>
</tr></thead>
<tbody>""" + main_html + """</tbody>
</table>
</div>"""

    if watch_html:
        html += """
<div style="padding:12px 32px 18px;">
<h3 style="color:#AFAB92;font-size:12px;margin:0 0 6px;">A SURVEILLER</h3>
<table style="width:100%;border-collapse:collapse;">""" + watch_html + """</table>
</div>"""

    html += """
<div style="background:#004763;padding:12px 32px;font-size:10px;color:#99B6C1;">
EIQUS NGA &middot; Thomas Garcia CSO &middot; thomas.garcia@eiqus.com &middot;
+41 76 453 0485 &middot; PSCE INPI 21 02798 &middot; JEI &middot; Bpifrance DeepTech TRL6
</div>
</div>
</body>
</html>"""

    return html


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
    msg["From"] = SENDER
    msg["To"] = RECIPIENT
    msg.attach(MIMEText(html, "html", "utf-8"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    print("Email envoye ID: " + str(result.get("id")))


def main():
    today = date.today().strftime("%A %d %B %Y")
    print("EIQUS Tender Monitor — " + today)
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    print("\n[1/4] Recherche 6 segments 24 requetes...")
    all_raw = []
    for i, batch in enumerate(BATCHES):
        print("  Lot " + str(i + 1) + "/6 " + batch["label"] + "...")
        try:
            r = search_batch(batch, client)
            print("  -> " + str(len(r)) + " resultats")
            all_raw.extend(r)
        except Exception as e:
            print("  Erreur: " + str(e))
        if i < len(BATCHES) - 1:
            time.sleep(1.5)

    print("\n[2/4] Deduplication...")
    seen = set()
    deduped = []
    for item in all_raw:
        k = str(item.get("title", "")).lower()[:70]
        if k and k not in seen:
            seen.add(k)
            deduped.append(item)
    print("  " + str(len(deduped)) + " uniques sur " + str(len(all_raw)))

    print("\n[3/4] Scoring " + str(len(deduped)) + " opportunites...")
    scored = score_items(deduped, client)
    retained = sorted(
        [t for t in scored if (t.get("score") or 0) >= THRESHOLD],
        key=lambda x: x.get("score", 0),
        reverse=True
    )
    rejected = [t for t in scored if (t.get("score") or 0) < THRESHOLD][:5]
    print("  " + str(len(retained)) + " retenues | " + str(len(rejected)) + " sous seuil")

    print("\n[4/4] Envoi email...")
    html = build_email(retained, rejected, today)
    subject = "EIQUS Tender Monitor — " + today + " (" + str(len(retained)) + " opportunites >=" + str(THRESHOLD) + ")"
    send_email(subject, html)
    print("\nTermine avec succes!")


if __name__ == "__main__":
    main()
