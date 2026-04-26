import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_USER = "pretalert@gmail.com"
EMAIL_PASS = "pagx wygs pptl ypgw"

def trimite_alerta(email_dest, nume_produs, pret_curent, pret_dorit, link_produs):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🔔 Alertă preț: {nume_produs[:50]}"
        msg['From'] = EMAIL_USER
        msg['To'] = email_dest

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #0f1117; color: #e2e8f0;">
            <div style="background: #1a1d2e; padding: 20px; text-align: center; border-bottom: 2px solid #f0a500;">
                <h1 style="color: #f0a500; margin: 0;">🔔 PretAlert.ro</h1>
            </div>
            <div style="padding: 30px;">
                <h2 style="color: #e2e8f0;">Prețul a scăzut! 🎉</h2>
                <p style="color: #94a3b8;">Produsul urmărit de tine are un preț mai mic decât ai setat:</p>
                <div style="background: #1a1d2e; padding: 20px; border-radius: 8px; margin: 20px 0; border: 1px solid #2d3148;">
                    <h3 style="color: #e2e8f0;">{nume_produs}</h3>
                    <p style="color: #64748b; text-decoration: line-through;">
                        Preț dorit: {pret_dorit} Lei
                    </p>
                    <p style="color: #f0a500; font-size: 24px; font-weight: bold; margin: 0;">
                        Preț actual: {pret_curent} Lei
                    </p>
                </div>
                <a href="{link_produs}"
                   style="background: #f0a500; color: #0f1117; padding: 12px 24px;
                          text-decoration: none; border-radius: 8px; display: inline-block; font-weight: bold;">
                    🛒 Cumpără acum
                </a>
            </div>
            <div style="padding: 20px; text-align: center; color: #334155; font-size: 12px; border-top: 1px solid #1a1d2e;">
                <p>PretAlert.ro — Monitorizare prețuri România</p>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html, 'html'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, email_dest, msg.as_string())

        print("✅ Email alertă trimis")
        return True
    except Exception as e:
        print(f"❌ Eroare email: {e}")
        return False

def trimite_contact(nume, email_expeditor, mesaj):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"[Contact PretAlert] Mesaj de la {nume}"
        msg['From'] = EMAIL_USER
        msg['To'] = EMAIL_USER
        msg['Reply-To'] = email_expeditor
        html = f"""
        <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#0f1117;color:#e2e8f0;padding:24px;">
          <h2 style="color:#f0a500;">Mesaj nou de contact — PretAlert.ro</h2>
          <p><strong>Nume:</strong> {nume}</p>
          <p><strong>Email:</strong> {email_expeditor}</p>
          <p><strong>Mesaj:</strong></p>
          <p style="background:#1a1d2e;padding:1rem;border-radius:8px;border:1px solid #2d3148;">{mesaj}</p>
        </body></html>
        """
        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, EMAIL_USER, msg.as_string())
        return True
    except Exception as e:
        print(f"❌ Eroare contact: {e}")
        return False

def trimite_raport_saptamanal(email_dest, username, produse_raport):
    """produse_raport: list of dict cu chei: nume, pret_curent, pret_initial, link, produs_id"""
    try:
        randuri = ""
        for p in produse_raport:
            pret_curent = p['pret_curent']
            pret_initial = p.get('pret_initial')
            link = p['link']
            nume = p['nume']

            if pret_initial and pret_curent < pret_initial:
                indicator = "📉 Preț mai mic!"
                culoare_indicator = "#22c55e"
                diferenta = f"<span style='color:#22c55e;font-size:12px;'>față de {pret_initial:.2f} Lei la adăugare</span>"
            elif pret_initial and pret_curent > pret_initial:
                indicator = "📈 Preț crescut"
                culoare_indicator = "#ef4444"
                diferenta = f"<span style='color:#ef4444;font-size:12px;'>față de {pret_initial:.2f} Lei la adăugare</span>"
            else:
                indicator = "➡️ Preț neschimbat"
                culoare_indicator = "#94a3b8"
                diferenta = ""

            randuri += f"""
            <tr>
                <td style="padding:14px 12px;border-bottom:1px solid #2d3148;color:#e2e8f0;font-size:13px;">
                    <a href="{link}" style="color:#e2e8f0;text-decoration:none;">{nume[:70]}</a>
                </td>
                <td style="padding:14px 12px;border-bottom:1px solid #2d3148;text-align:right;white-space:nowrap;">
                    <strong style="color:#f0a500;font-size:15px;">{pret_curent:.2f} Lei</strong><br>
                    {diferenta}
                </td>
                <td style="padding:14px 12px;border-bottom:1px solid #2d3148;text-align:center;white-space:nowrap;
                            color:{culoare_indicator};font-size:13px;font-weight:bold;">
                    {indicator}
                </td>
                <td style="padding:14px 12px;border-bottom:1px solid #2d3148;text-align:center;">
                    <a href="{link}"
                       style="background:#f0a500;color:#0f1117;padding:6px 14px;text-decoration:none;
                              border-radius:6px;font-size:12px;font-weight:bold;">
                        Vezi
                    </a>
                </td>
            </tr>"""

        html = f"""
        <html>
        <body style="font-family:Arial,sans-serif;max-width:650px;margin:0 auto;background:#0f1117;color:#e2e8f0;">
            <div style="background:#1a1d2e;padding:24px;text-align:center;border-bottom:2px solid #f0a500;">
                <h1 style="color:#f0a500;margin:0;font-size:22px;">📊 PretAlert.ro</h1>
            </div>
            <div style="padding:28px 24px;">
                <h2 style="color:#e2e8f0;margin-top:0;">Salut, {username}!</h2>
                <p style="color:#94a3b8;margin-bottom:24px;">
                    Iată raportul săptămânal pentru produsele tale urmărite:
                </p>
                <table style="width:100%;border-collapse:collapse;background:#1a1d2e;
                              border-radius:8px;overflow:hidden;border:1px solid #2d3148;">
                    <thead>
                        <tr style="background:#2d3148;">
                            <th style="padding:12px;text-align:left;color:#94a3b8;font-size:12px;text-transform:uppercase;">Produs</th>
                            <th style="padding:12px;text-align:right;color:#94a3b8;font-size:12px;text-transform:uppercase;">Preț curent</th>
                            <th style="padding:12px;text-align:center;color:#94a3b8;font-size:12px;text-transform:uppercase;">Evoluție</th>
                            <th style="padding:12px;text-align:center;color:#94a3b8;font-size:12px;text-transform:uppercase;">Link</th>
                        </tr>
                    </thead>
                    <tbody>
                        {randuri}
                    </tbody>
                </table>
                <div style="margin-top:28px;text-align:center;">
                    <a href="https://pretalert.ro/profil"
                       style="background:#1a1d2e;color:#f0a500;padding:12px 28px;text-decoration:none;
                              border-radius:8px;border:1px solid #f0a500;font-weight:bold;display:inline-block;">
                        Gestionează urmăririle
                    </a>
                </div>
            </div>
            <div style="padding:16px 24px;text-align:center;color:#334155;font-size:11px;border-top:1px solid #1a1d2e;">
                <p style="margin:0;">PretAlert.ro — Monitorizare prețuri România</p>
                <p style="margin:4px 0 0;">
                    <a href="https://pretalert.ro/profil" style="color:#475569;text-decoration:none;">
                        Dezactivează emailurile săptămânale
                    </a>
                </p>
            </div>
        </body>
        </html>
        """

        msg = MIMEMultipart('alternative')
        msg['Subject'] = "📊 Raportul tău săptămânal de prețuri - PretAlert.ro"
        msg['From'] = EMAIL_USER
        msg['To'] = email_dest
        msg.attach(MIMEText(html, 'html'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, email_dest, msg.as_string())

        print("✅ Raport săptămânal trimis")
        return True
    except Exception as e:
        print(f"❌ Eroare raport: {e}")
        return False
