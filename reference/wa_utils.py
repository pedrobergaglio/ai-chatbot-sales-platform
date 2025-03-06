import logging, json, requests, tempfile, datetime, time
from datetime import datetime, timedelta
from flask import current_app, jsonify
from dotenv import load_dotenv
from app.utils.bot import *
from app.services.pdf_creator import prepare_message
from whatsapp import WhatsApp
from app.utils.db_utils.mysql_helper import format_and_add_message_to_mysql
from app.utils.gpt_utils.summarizer import summarize_text_for_audio
from app.utils.gpt_utils.stt_tts import speech_to_text, text_to_speech_azure
from app.utils.whatsapp.whatsapp_message_util import send_message

load_dotenv('../../')

agent = create_chat_agent()
access_token = os.getenv("ACCESS_TOKEN")
assistant_number = os.getenv("WA_ASSISTANT_NUMBER")





def process_whatsapp_message(body):
    message = body["entry"][0]["changes"][0]["value"]["messages"][0]
    timestamp = int(body["entry"][0]["changes"][0]["value"]['messages'][0]['timestamp'])
    phone_number = message['from']
    rec_assistant_number = body["entry"][0]["changes"][0]["value"]["metadata"]["display_phone_number"]

    if(not rec_assistant_number==assistant_number):
       # Si no es un mensaje para este asistente no hago nada
       return 'ok'
    if phone_number.startswith('549'):
        # Eliminar el '9' del número de teléfono
        phone_number = phone_number[:2] + phone_number[3:]
    # Convertir timestamp a datetime
    dt_object = datetime.fromtimestamp(timestamp)

    # Calcular la diferencia
    time_difference = datetime.now() - dt_object

    # Comparar si la diferencia es mayor a 1 minuto
    if time_difference > timedelta(seconds=10):
        logging.info("El mensaje es más de 10 segundos más viejo que la hora actual.")
    else:
        if 'text' in message:
            # Procesamiento de mensajes de texto
            message_body = message["text"]["body"]
            
            
            response = agent.get_response(message_body, phone_number, phone_number) #responde al mensaje
            logging.info(f'RESPUESTA DEL BOT: {response}')
            
            [text_message, media_message] = prepare_message(message_body, response, phone_number)
            
            if text_message :
                logging.info('send text message:' + text_message)
                send_message(text_message)
            if media_message :
                send_message(media_message)

        elif 'audio' in message:
            # Procesamiento de mensajes de audio
            message_voice_id = message['audio']['id']
            api_url = "https://graph.facebook.com/v18.0/"
            headers = {'Authorization': f'Bearer {access_token}'}
            media_response = requests.get(f"{api_url}/{message_voice_id}", headers=headers)
            #Handle different errors...
            if media_response.status_code != 200:
                response = "Error al obtener información del media."
                return response
            
            media_info = media_response.json()
            media_url = media_info.get("url")

            if not media_url:
                response = "Error al obtener la URL del media."
                return response
            
            audio_response = requests.get(media_url, headers=headers)

            if audio_response.status_code != 200:
                response = "Error al obtener el audio."
                return response

            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_file:
                temp_file.write(audio_response.content)
                temp_file_path = temp_file.name
                temp_file.close()

                try:
                    
                    audio_transcript = speech_to_text(temp_file_path)
                    logging.info('Audio Transcript',audio_transcript)
                    response = agent.get_response(audio_transcript, phone_number, phone_number)                     
                    
                    
                    format_and_add_message_to_mysql(message["id"], 
                        body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"], 
                        message["timestamp"], 
                        phone_number, 
                        'audio',
                        audio_transcript,
                        body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"], 
                        response[1])
                    
                    [text_message, media_message] = prepare_message(audio_transcript, response, phone_number, True)
                    if media_message and not text_message: 
                        logging.info(media_message)
                        send_message(media_message)
                    if text_message:
                        text_dict = json.loads(text_message) 
                        logging.info(text_message)
                        #send_message(text_message)
                        audio_text = text_dict['text']['body']
                        logging.info(audio_text)
                        max_len = int(os.getenv('MAX_AUDIO_LENGTH'))
                        audio_text = summarize_text_for_audio(audio_text,max_len)

                        audio_name = f"output-{datetime.now()}.mp3"
                        text_to_speech_azure(audio_text,audio_name)

                        messenger = WhatsApp(token=access_token, phone_number_id=current_app.config['PHONE_NUMBER_ID'])
                        whatsapp_response = messenger.upload_media(audio_name)
                        media_id = whatsapp_response['id']
                        if media_message:
                            logging.info(media_message)
                            send_message(media_message)
                            time.sleep(0.5) #se espera brevemente para que se manden los mensajes en orden
                        #Si se resumió el texto para audio se manda a parte
                        if len(text_dict['text']['body'])>max_len:
                            send_message(text_message)
                        messenger.send_audio(media_id,phone_number,False)
                except Exception as e:
                    response = 'Ocurrió un error al procesar el audio'
                    logging.error(f'Ocurrió un error al procesar el audio: {e}')
                
            
            
        else:
            # Si no es texto ni audio, no hacer nada
            return 'uy'


def is_valid_whatsapp_message(body):
    """
    Check if the incoming webhook event has a valid WhatsApp message structure.
    """
    return (
        body.get("object")
        and body.get("entry")
        and body["entry"][0].get("changes")
        and body["entry"][0]["changes"][0].get("value")
        and body["entry"][0]["changes"][0]["value"].get("messages")
        and body["entry"][0]["changes"][0]["value"]["messages"][0]
    )


def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")
