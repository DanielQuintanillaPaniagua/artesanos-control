import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr


def _config():
    """Lee la configuracion SMTP del .env."""
    return {
        'host': os.getenv('SMTP_HOST'),
        'port': int(os.getenv('SMTP_PORT', 587)),
        'user': os.getenv('SMTP_USER'),
        'password': os.getenv('SMTP_PASSWORD'),
        'from_addr': os.getenv('SMTP_FROM', os.getenv('SMTP_USER')),
    }


def enviar_email(destinatario, asunto, html_body, texto_body=None):
    """Envia un email HTML. Devuelve (ok, error)."""
    cfg = _config()

    if not cfg['host'] or not cfg['user'] or not cfg['password']:
        return False, 'SMTP no configurado'

    # Crear mensaje
    msg = MIMEMultipart('alternative')
    msg['Subject'] = asunto
    msg['From'] = cfg['from_addr']
    msg['To'] = destinatario

    # Version texto plano (fallback)
    if texto_body:
        msg.attach(MIMEText(texto_body, 'plain', 'utf-8'))

    # Version HTML
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    try:
        with smtplib.SMTP(cfg['host'], cfg['port'], timeout=10) as server:
            server.starttls()
            server.login(cfg['user'], cfg['password'])
            server.send_message(msg)
        return True, None
    except Exception as e:
        return False, str(e)


def enviar_email_recuperacion(destinatario, nombre, link):
    """Envia el correo de recuperacion de contrasena."""
    asunto = 'Artesanos Control - Recuperacion de contrasena'

    texto = f"""Hola {nombre},

Recibimos una solicitud para restablecer tu contrasena en Artesanos Control.

Hace clic en este link para cambiarla (expira en 1 hora):
{link}

Si no solicitaste este cambio, ignora este correo.

-- Artesanos Control
"""

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
</head>
<body style="margin:0;padding:0;background:#f4f6f5;font-family:'Segoe UI',Tahoma,sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f5;padding:40px 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,0.05);">
                    <!-- Header -->
                    <tr>
                        <td style="background:#0f4630;padding:32px 40px;text-align:center;">
                            <h1 style="color:#fff;margin:0;font-size:24px;font-weight:800;letter-spacing:0.5px;">ARTESANOS CONTROL</h1>
                            <p style="color:#a8d5bd;margin:8px 0 0;font-size:13px;">Sistema de control de facturas</p>
                        </td>
                    </tr>

                    <!-- Contenido -->
                    <tr>
                        <td style="padding:40px;">
                            <h2 style="color:#1d2a24;margin:0 0 20px;font-size:20px;">Hola {nombre},</h2>

                            <p style="color:#4a5568;font-size:15px;line-height:1.6;margin:0 0 20px;">
                                Recibimos una solicitud para <strong>restablecer tu contrasena</strong> en Artesanos Control.
                            </p>

                            <p style="color:#4a5568;font-size:15px;line-height:1.6;margin:0 0 30px;">
                                Hace clic en el siguiente boton para crear una nueva contrasena:
                            </p>

                            <table cellpadding="0" cellspacing="0" style="margin:0 auto 30px;">
                                <tr>
                                    <td align="center" style="background:#1a6b48;border-radius:8px;">
                                        <a href="{link}" style="display:inline-block;padding:16px 40px;color:#fff;text-decoration:none;font-size:15px;font-weight:700;letter-spacing:0.5px;">
                                            Cambiar mi contrasena
                                        </a>
                                    </td>
                                </tr>
                            </table>

                            <p style="color:#718096;font-size:13px;line-height:1.6;margin:0 0 20px;">
                                O copia y pega este link en tu navegador:
                            </p>

                            <p style="background:#f4f6f5;border-radius:6px;padding:12px;font-size:12px;color:#4a5568;word-break:break-all;margin:0 0 30px;">
                                {link}
                            </p>

                            <div style="background:#fff7e6;border-left:4px solid #d97706;border-radius:4px;padding:16px;margin:0 0 20px;">
                                <p style="color:#92400e;font-size:13px;line-height:1.5;margin:0;">
                                    <strong>Este link expira en 1 hora.</strong><br>
                                    Si no solicitaste este cambio, puedes ignorar este correo.
                                </p>
                            </div>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background:#f9fafb;padding:24px 40px;text-align:center;border-top:1px solid #e5e7eb;">
                            <p style="color:#9ca3af;font-size:12px;margin:0;">
                                Artesanos Control &copy; 2026<br>
                                Este es un correo automatico, no respondas a este mensaje.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

    return enviar_email(destinatario, asunto, html, texto)


def enviar_email_supervisor_edito(destinatario, factura, supervisor, motivo, cambios, link):
    """Notifica al owner cuando un supervisor edita una factura."""
    asunto = f"Artesanos Control - Supervisor edito factura #{factura.numero_factura}"

    texto = f"""Hola,

El supervisor {supervisor.nombre} ha editado una factura que requiere tu revision.

Factura: #{factura.numero_factura}
Sucursal: {factura.sucursal.nombre if factura.sucursal else '?'}
Supervisor: {supervisor.nombre}
Motivo: {motivo}

Cambios realizados:
{cambios}

Revisa la factura en: {link}

-- Artesanos Control
"""

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
</head>
<body style="margin:0;padding:0;background:#f4f6f5;font-family:'Segoe UI',Tahoma,sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f5;padding:40px 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,0.05);">
                    <!-- Header -->
                    <tr>
                        <td style="background:#0f4630;padding:32px 40px;text-align:center;">
                            <h1 style="color:#fff;margin:0;font-size:24px;font-weight:800;letter-spacing:0.5px;">ARTESANOS CONTROL</h1>
                            <p style="color:#a8d5bd;margin:8px 0 0;font-size:13px;">Notificacion de supervisor</p>
                        </td>
                    </tr>

                    <!-- Contenido -->
                    <tr>
                        <td style="padding:40px;">
                            <div style="background:#fff7e6;border-left:4px solid #d97706;border-radius:4px;padding:16px;margin-bottom:24px;">
                                <p style="color:#92400e;font-size:14px;line-height:1.5;margin:0;">
                                    <strong>Un supervisor ha editado una factura.</strong><br>
                                    Requiere tu revision.
                                </p>
                            </div>

                            <h2 style="color:#1d2a24;margin:0 0 20px;font-size:20px;">Factura #{factura.numero_factura}</h2>

                            <table width="100%" cellpadding="8" cellspacing="0" style="font-size:14px;color:#4a5568;margin-bottom:20px;">
                                <tr>
                                    <td style="font-weight:600;width:140px;">Sucursal:</td>
                                    <td>{factura.sucursal.nombre if factura.sucursal else '?'}</td>
                                </tr>
                                <tr>
                                    <td style="font-weight:600;">Supervisor:</td>
                                    <td>{supervisor.nombre}</td>
                                </tr>
                                <tr>
                                    <td style="font-weight:600;">Total:</td>
                                    <td>${factura.total_factura:.2f}</td>
                                </tr>
                                <tr>
                                    <td style="font-weight:600;">Motivo:</td>
                                    <td>{motivo}</td>
                                </tr>
                            </table>

                            <h3 style="color:#1d2a24;font-size:16px;margin:24px 0 12px;">Cambios realizados</h3>
                            <div style="background:#f9fafb;border-radius:8px;padding:16px;font-size:13px;color:#4a5568;">
                                {cambios}
                            </div>

                            <table cellpadding="0" cellspacing="0" style="margin:30px auto 0;">
                                <tr>
                                    <td align="center" style="background:#1a6b48;border-radius:8px;">
                                        <a href="{link}" style="display:inline-block;padding:16px 40px;color:#fff;text-decoration:none;font-size:15px;font-weight:700;letter-spacing:0.5px;">
                                            Revisar factura
                                        </a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background:#f9fafb;padding:24px 40px;text-align:center;border-top:1px solid #e5e7eb;">
                            <p style="color:#9ca3af;font-size:12px;margin:0;">
                                Artesanos Control &copy; 2026<br>
                                Este es un correo automatico.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

    return enviar_email(destinatario, asunto, html, texto)