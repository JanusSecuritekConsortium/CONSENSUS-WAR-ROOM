"""English/Spanish conversation defaults; source names are never translated."""
import re
import unicodedata


def fold(text):
    text = str(text).replace('’', "'").replace('‘', "'")
    return ''.join(c for c in unicodedata.normalize('NFD', text.casefold())
                   if not unicodedata.combining(c))


def detect(text, hint=None, fallback='en'):
    value = fold(text)
    # Explicit language requests override the detected input language.
    if re.search(r'\b(?:in english|en ingles)\b', value):
        return 'en'
    if re.search(r'\b(?:in spanish|en espanol|en castellano)\b', value):
        return 'es'
    spanish = len(re.findall(r'\b(?:que|donde|mi|mis|hoy|manana|agenda|reunion|reuniones|'
                             r'puedes|quiero|gracias|hola|recuerdame|recuerdamelo|hecho|ya|'
                             r'encargado|siguiente|proxima|cambio|cambios|cambiado|seguimientos|leelo|voz|'
                             r'hagas|haz|puedo|necesito|tengo|tenemos|como|cuando|esto|esta|este|estos|'
                             r'por|favor|para|una|un|con|es|estoy|quieres|ayuda|dime|muestra|revisa|'
                             r'consulta|comprobar|hablame|explicame|si|buenos|dias|buenas|tardes|no)\b', value))
    english = len(re.findall(r'\b(?:what|where|my|today|tomorrow|meeting|meetings|please|'
                             r'show|check|read|next|handled|remind|thanks|hello|changed|english)\b', value))
    if spanish > english:
        return 'es'
    if english > spanish:
        return 'en'
    return hint if hint in ('en', 'es') else fallback


def choose(lang, english, spanish):
    return spanish if lang == 'es' else english


def error(key, lang='en'):
    messages = {
        'stale': ('This message arrived while Aurelius was offline. Please resend it if still needed; no action was taken.',
                  'Este mensaje llegó mientras Aurelius estaba desconectado. Envíalo de nuevo si aún lo necesitas; no se realizó ninguna acción.'),
        'audio': ('I could not process that audio. Send a clear voice note under ten minutes, or type your message.',
                  'No pude procesar ese audio. Envía una nota de voz clara de menos de diez minutos o escribe tu mensaje.'),
        'offline': ('My agent connection is currently offline. No action was dispatched. Agenda questions, briefing choices and follow-up controls still work.',
                    'La conexión con mi agente está desconectada. No se envió ninguna acción. Las consultas de agenda, las opciones de los informes y los controles de seguimiento siguen funcionando.'),
        'timeout': ('Aurelius has not confirmed the result. Check its status in Msty Go before repeating an action.',
                    'Aurelius no ha confirmado el resultado. Comprueba su estado en Msty Go antes de repetir una acción.'),
        'button': ('This button has expired or does not belong to this message. Send a fresh request.',
                   'Este botón ha caducado o no corresponde a este mensaje. Envía una nueva solicitud.'),
        'local': ('I could not complete that local request. Please try again; no agent action was dispatched.',
                  'No pude completar esa solicitud local. Inténtalo de nuevo; no se envió ninguna acción al agente.'),
    }
    return choose(lang, *messages[key])
