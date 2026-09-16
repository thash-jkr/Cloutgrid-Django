import requests

def send_otp_email(api_key, recipient_email, template_key, placeholders):
    url = "https://api.zeptomail.com.au/v1.1/email/template"

    headers = {
        "Authorization": f"Zoho-enczapikey {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "from": {
            "address": "info@cloutgrid.com",
            "name": "CloutGrid"
        },
        "to": [{"email_address": {"address": recipient_email}}],
        "subject": "Email Verification",
        "merge_info": placeholders,
        "template_key": template_key
    }

    response = requests.post(url, json=payload, headers=headers)
    return response.status_code, response.json()

def send_password_reset_email(api_key, recipient_email, template_key, placeholders):
    url = "https://api.zeptomail.com.au/v1.1/email/template"

    headers = {
        "Authorization": f"Zoho-enczapikey {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "from": {
            "address": "info@cloutgrid.com",
            "name": "CloutGrid"
        },
        "to": [{"email_address": {"address": recipient_email}}],
        "subject": "Password Reset",
        "merge_info": placeholders,
        "template_key": template_key
    }

    response = requests.post(url, json=payload, headers=headers)
    return response.status_code, response.json()
