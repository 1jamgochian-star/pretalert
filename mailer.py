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

        print(f"✅ Email trimis către {email_dest}")
        return True
    except Exception as e:
        print(f"❌ Eroare email: {e}")
        return False
