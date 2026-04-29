import os, time
from datetime import date
from config import RECIPIENT_EMAIL, SENDER_EMAIL, SCORE_THRESHOLD, EIQUS_CONTEXT, QUERY_BATCHES
from searcher import search_batch, safe_json
from scorer import score_items, filter_and_sort
from email_builder import build_email
from gmail_sender import send_email

def deduplicate(items):
    seen, result = set(), []
    for item in items:
        key = (item.get("title") or "").lower()[:70].strip()
        if key and key not in seen:
            seen.add(key)
            result.append(item)
    return result

def main():
    print("=" * 50)
    print("EIQUS Tender Monitor — Démarrage")
    print(f"Date : {date.today().strftime('%A %d %B %Y')}")
    print("=" * 50)

    today_str = date.today().strftime("%A %d %B %Y")

    print("\n[1/4] Recherche — 6 segments, 24 requêtes...")
    all_raw = []
    for i, batch in enumerate(QUERY_BATCHES):
        print(f"  Lot {i+1}/6 — {batch['label']}...")
        try:
            results = search_batch(batch, EIQUS_CONTEXT)
            print(f"  → {len(results)} résultats")
            all_raw.extend(results)
        except Exception as e:
            print(f"  ⚠️ Erreur lot {i+1} : {e}")
        if i < len(QUERY_BATCHES) - 1:
            time.sleep(1.5)

    print(f"\n[2/4] Déduplication...")
    deduped = deduplicate(all_raw)
    print(f"  {len(deduped)} uniques sur {len(all_raw)} bruts")

    print(f"\n[3/4] Scoring {len(deduped)} opportunités...")
    scored = score_items(deduped, EIQUS_CONTEXT)
    retained, rejected = filter_and_sort(scored, SCORE_THRESHOLD)
    print(f"  ✅ {len(retained)} retenues (≥{SCORE_THRESHOLD})")
    print(f"  👁  {len(rejected)} à surveiller")

    print("\n[4/4] Envoi email...")
    html = build_email(retained, rejected, today_str)
    subject = f"EIQUS Tender Monitor — {today_str} ({len(retained)} opportunités ≥{SCORE_THRESHOLD})"
    send_email(subject, html, RECIPIENT_EMAIL, SENDER_EMAIL)
    print("\n✅ Terminé !")

if __name__ == "__main__":
    main()
