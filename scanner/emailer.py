import html
import smtplib
from email.mime.text import MIMEText

import markdown
import nh3

# Tags and attributes the AI narrative is permitted to produce.
# Everything else (scripts, iframes, event handlers, style overrides, etc.)
# is stripped by nh3 before the HTML is embedded in the email template.
_ALLOWED_TAGS = {
    "p", "br", "strong", "em", "b", "i",
    "h1", "h2", "h3", "h4",
    "ul", "ol", "li",
    "a", "blockquote", "code", "pre",
}
_ALLOWED_ATTRS = {"a": {"href", "title"}}


def markdown_to_html(md_text):
    raw_html = markdown.markdown(md_text)
    return nh3.clean(raw_html, tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRS)


def render_ticker_table(ticker_records):
    if not ticker_records:
        return ""

    rows = []
    for r in ticker_records:
        pct = r["pct_change"]
        pct_color = "#0a7d34" if pct >= 0 else "#c0362c"
        pct_sign = "+" if pct >= 0 else ""

        pl_cell = "&mdash;"
        if r.get("unrealized_pl") is not None:
            pl = r["unrealized_pl"]
            pl_color = "#0a7d34" if pl >= 0 else "#c0362c"
            pl_sign = "+" if pl >= 0 else ""
            pl_cell = f'<span style="color:{pl_color};">{pl_sign}${pl:,.2f}</span>'

        mover_badge = (
            ' <span style="background:#fef3c7;color:#92400e;font-size:11px;'
            'font-weight:600;padding:2px 6px;border-radius:4px;">MOVER</span>'
            if r["is_mover"]
            else ""
        )

        rows.append(f"""
        <tr>
          <td data-label="Ticker" style="padding:10px 12px;border-bottom:1px solid #e5e7eb;font-weight:600;">{html.escape(r["ticker"])}{mover_badge}</td>
          <td data-label="Price" style="padding:10px 12px;border-bottom:1px solid #e5e7eb;text-align:right;">${r["current_price"]:,.2f}</td>
          <td data-label="Change" style="padding:10px 12px;border-bottom:1px solid #e5e7eb;text-align:right;color:{pct_color};font-weight:600;">{pct_sign}{pct:.2f}%</td>
          <td data-label="P&amp;L" style="padding:10px 12px;border-bottom:1px solid #e5e7eb;text-align:right;">{pl_cell}</td>
        </tr>""")

    return f"""
    <table style="width:100%;border-collapse:collapse;margin:8px 0 20px 0;font-size:14px;">
      <thead>
        <tr style="background:#f3f4f6;">
          <th style="padding:8px 12px;text-align:left;color:#6b7280;font-size:12px;text-transform:uppercase;">Ticker</th>
          <th style="padding:8px 12px;text-align:right;color:#6b7280;font-size:12px;text-transform:uppercase;">Price</th>
          <th style="padding:8px 12px;text-align:right;color:#6b7280;font-size:12px;text-transform:uppercase;">Change</th>
          <th style="padding:8px 12px;text-align:right;color:#6b7280;font-size:12px;text-transform:uppercase;">P&amp;L</th>
        </tr>
      </thead>
      <tbody>{"".join(rows)}</tbody>
    </table>"""


def render_digest_email(markdown_text, ticker_records, subject_date):
    table_html = render_ticker_table(ticker_records)
    narrative_html = markdown_to_html(markdown_text)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  body {{
    margin: 0;
    padding: 0;
    background: #f3f4f6;
    font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #111827;
  }}
  .container {{ max-width: 640px; margin: 0 auto; padding: 24px 16px; }}
  .card {{
    background: #ffffff;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  }}
  h1 {{ font-size: 20px; margin: 0 0 4px 0; }}
  .subtitle {{ color: #6b7280; font-size: 13px; margin: 0 0 20px 0; }}
  h2 {{ font-size: 16px; margin: 20px 0 8px 0; }}
  p, li {{ line-height: 1.55; font-size: 14px; }}
  table {{ width: 100%; }}
  @media (max-width: 480px) {{
    .container {{ padding: 12px 8px; }}
    .card {{ padding: 16px; border-radius: 8px; }}
    table, thead, tbody, tr {{ display: block; width: 100%; }}
    th {{ display: none; }}
    td {{ display: flex; justify-content: space-between; padding: 6px 4px !important; }}
    td::before {{ content: attr(data-label); color: #6b7280; font-weight: 500; }}
  }}
</style>
</head>
<body>
  <div class="container">
    <div class="card">
      <h1>Morning Digest</h1>
      <p class="subtitle">{html.escape(subject_date)}</p>
      {table_html}
      {narrative_html}
    </div>
  </div>
</body>
</html>"""


def send_email(gmail_address, gmail_app_password, recipient_email, subject, html_body):
    recipients = [addr.strip() for addr in recipient_email.split(",") if addr.strip()]

    msg = MIMEText(html_body, "html")
    msg["Subject"] = subject
    msg["From"] = gmail_address
    msg["To"] = ", ".join(recipients)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_address, gmail_app_password)
        server.sendmail(gmail_address, recipients, msg.as_string())


def send_debug_email(gmail_address, gmail_app_password, recipient_email, errors):
    body = "<h2>Debug report</h2><ul>" + "".join(f"<li>{html.escape(str(e))}</li>" for e in errors) + "</ul>"
    send_email(gmail_address, gmail_app_password, recipient_email, "⚠️ Debug report", body)
