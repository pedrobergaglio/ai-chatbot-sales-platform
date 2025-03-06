import json, os, requests, logging
from datetime import datetime
from flask import jsonify


access_token = os.getenv("ACCESS_TOKEN")
number_id = os.getenv("PHONE_NUMBER_ID")
version = os.getenv("VERSION")

def get_pdf_message(recipient, pdf_link, caption):
    result = json.dumps({
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": recipient,
                "type": "document",
                "document": {
                    "link": pdf_link,
                    "caption": caption,  # Eliminar espacios en blanco al inicio y fin
                    "filename": f'informacion-solicitada-{datetime.now()}.pdf'
                }
            })
    return result

def get_text_message(recipient, text):
    result = json.dumps(
            {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": recipient,
                "type": "text",
                "text": {"preview_url": False, "body": text.strip()},
            })
    return result

def get_image_message(recipient, image_link, caption):
    result = json.dumps({
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "image",
            "image": {
                "link": image_link,
                "caption": caption.strip()  # Eliminar espacios en blanco al inicio y fin
            }})
    return result



def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")


def send_message(data):
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }

    url = f"https://graph.facebook.com/{version}/{number_id}/messages"
    
    try:
        
        response = requests.post(
            url, data=data, headers=headers, timeout=10
        )  # 10 seconds timeout as an example
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
    except requests.Timeout:
        logging.error("Timeout occurred while sending message")
        return jsonify({"status": "error", "message": "Request timed out"}), 408
    except (
        requests.RequestException
    ) as e:  # This will catch any general request exception
        logging.error(f"Request failed due to: {e}")
        return jsonify({"status": "error", "message": "Failed to send message"}), 500
    else:
        # Process the response as normal
        log_http_response(response)
        return response