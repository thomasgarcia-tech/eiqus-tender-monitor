def _rc(r):
    return {"GO":"#004763","GO-PARTNER":"#336C82","SURVEILLER":"#AFAB92","NO-GO":"#aaa"}.get(r,"#aaa")

def _sc(s):
    return "#004763" if s>=85 else "#336C82" if s>=75 else "#56858B"

def _link(url, label="Voir l'annonce"):
    if url and url not in ("Non précisé","null",""):
        return f'<a href="{url}" style="font-size:11px;color:#336C82;">{label} →</a>'
    return ""

def build_email(retained, rejected, scan_date):
    top3 = retained[:3]
    main = retained[3:]
    medals = ["🥇","🥈","🥉"]
    go = sum(1 for t in retained if t.get("recommendation")=="GO")
    partner = sum(1 for t in retained if t.get("recommendation")=="GO-PARTNER")

    top3_rows = ""
    for i, t in enumerate(top3):
        sc = t.get("score", 0)
        top3_rows += f"""<tr style="border-bottom:2px solid #CCDBE0;vertical-align:top;background:{'#f0f7fa' if i==0 else 'white'};">
          <td style="padding:14px 8px;font-size:22px;">{medals[i]}</td>
          <td style="padding:14px 10px;">
            <div style="font-weight:bold;color:#004763;font-size:13px;">{t.get('title','—')}</div>
            <div style="color:#336C82;font-size:11px;margin:3px 0;">{t.get('organization','')} · {t.get('country','')} · Deadline : <strong style="color:#c0392b;">{t.get('deadline','—')}</strong></div>
            <div style="font-size:12px;color:#333;font-style:italic;margin:4px 0;">{t.get('why_eiqus','')}</div>
            <div style="font-size:11px;color:#004763;font-weight:bold;">→ {t.get('action_imm','')}</div>
            <div style="margin-top:9px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
              <span style="background:{_rc(t.get('recommendation',''))};color:white;border-radius:6px;padding:2px 10px;font-size:11px;font-weight:bold;">{t.get('recommendation','')}</span>
              <span style="background:{_sc(sc)};color:white;border-radius:50%;width:38px;height:38px;display:inline-flex;align-items:center;justify-content:center;font-size:14px;font-weight:bold;">{sc}</span>
              {_link(t.get('source_url'))}
            </div>
          </td>
        </tr>"""

    main_rows = ""
    for t in main:
        sc = t.get("score", 0)
        main_rows += f"""<tr style="border-bottom:1px solid #CCDBE0;vertical-align:top;">
          <td style="padding:10px;text-align:center;">
            <div style="background:{_sc(sc)};color:white;border-radius:50%;width:36px;height:36px;display:inline-flex;align-items:center;justify-content:center;font-size:13px;font-weight:bold;">{sc}</div>
            <div style="font-size:9px;color:{_rc(t.get('recommendation',''))};font-weight:bold;margin-top:2px;">{t.get('recommendation','')}</div>
          </td>
          <td style="padding:10px;">
            <div style="font-weight:bold;color:#004763;font-size:12px;">{t.get('title','—')}</div>
            <div style="color:#336C82;font-size:11px;">{t.get('organization','')} · {t.get('country','')}</div>
            <div style="font-size:10px;color:#555;margin-top:2px;">{t.get('scope_summary','')[:200]}</div>
            <div style="font-size:10px;color:#004763;font-style:italic;margin-top:2px;">→ {t.get('action_imm','')}</div>
          </td>
          <td style="padding:10px;font-size:10px;color:#c0392b;font-weight:bold;white-space:nowrap;">{t.get('deadline','—')}</td>
          <td style="padding:10px;font-size:10px;">{t.get('estimated_budget','—')}</td>
          <td style="padding:10px;">{_link(t.get('source_url'),'Lien')}</td>
        </tr>"""

    watch_rows = ""
    for t in rejected:
        watch_rows += f"""<tr style="border-bottom:1px solid #e8e8e8;">
          <td style="padding:6px;color:#888;font-size:11px;font-weight:bold;">{t.get('title','—')}</td>
          <td style="padding:6px;color:#aaa;font-size:10px;">{t.get('organization','')} · {t.get('country','')}</td>
          <td style="padding:6px;color:#bbb;font-size:10px;">Score : {t.get('score','—')}</td>
          <td style="padding:6px;">{_link(t.get('source_url'),'Lien')}</td>
        </tr>"""

    return f"""<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;background:#f0f4f6;margin:0;padding:16px;">
<div style="max-width:880px;margin:0 auto;background:white;border-radius:10px;overflow:hidden;">
  <div style="background:#004763;padding:24px 32px;">
    <h1 style="color:white;margin:0;font-size:21px;">EIQUS Tender Monitor — Weekly Digest</h1>
    <p style="color:#99B6C1;margin:5px 0 0;font-size:12px;">{scan_date} · Lundi 01:00 CET · FR · IT · CH · EU</p>
  </div>
  <div style="background:#EEECE0;padding:12px 32px;font-size:13px;color:#333;">
    <strong>{len(retained)+len(rejected)}</strong> détectées · <strong>{len(retained)}</strong> retenues (≥70) · <strong>{go}</strong> GO · <strong>{partner}</strong> GO-PARTNER
  </div>
  {"<div styl
