#!/usr/bin/env python3
"""
A.U.R.E.L.I.U.S. Voice Module - David Attenborough Style
=======================================================
Provides TTS functionality with a serene, distinctly British tone
inspired by the renowned naturalist Sir David Attenborough.
"""

import random
import time
import logging
from datetime import datetime
from collections import deque

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='assistant_voice.log'
)
logger = logging.getLogger('AURELIUS')

class AttenboroughVoice:
    """Implements David Attenborough-style voice patterns for A.U.R.E.L.I.U.S."""
    
    def __init__(self, tts_engine=None, history_size=15):
        """
        Initialize the voice module.
        
        Args:
            tts_engine: TTS engine to use (placeholder for now)
            history_size: Number of phrases to remember to avoid repetition
        """
        self.tts_engine = tts_engine or self._placeholder_tts
        self.phrase_history = deque(maxlen=history_size)
        self.initialized = False
        logger.info("A.U.R.E.L.I.U.S. voice module initialized")
        
    def _placeholder_tts(self, text):
        """Placeholder for actual TTS implementation."""
        print(f"🔊 [AURELIUS]: {text}")
        logger.info(f"TTS: {text}")
        return True
    
    def greet(self):
        """Provide initial greeting upon system initialization."""
        if not self.initialized:
            greeting = random.choice(self.GREETING_PHRASES)
            self.speak(greeting)
            self.initialized = True
            return True
        return False
    
    def idle_phrase(self):
        """Select and speak a non-repetitive idle phrase."""
        available_phrases = [p for p in self.IDLE_PHRASES if p not in self.phrase_history]
        
        # If we've nearly exhausted unique phrases, reset history but keep last few
        if len(available_phrases) < 5:
            recent = list(self.phrase_history)[-3:]
            self.phrase_history.clear()
            for phrase in recent:
                self.phrase_history.append(phrase)
            available_phrases = [p for p in self.IDLE_PHRASES if p not in self.phrase_history]
        
        phrase = random.choice(available_phrases)
        self.phrase_history.append(phrase)
        self.speak(phrase)
        return phrase
    
    def speak(self, text):
        """Speak the given text using the TTS engine."""
        return self.tts_engine(text)
    
    def response_wrapper(self, text):
        """Wrap a response with an appropriate introduction phrase."""
        if not text:
            return None
            
        intro = random.choice(self.RESPONSE_INTROS)
        # Avoid double periods
        if text.startswith("."):
            text = text[1:].strip()
        
        # Add proper spacing
        if not intro.endswith(" "):
            intro += " "
            
        return intro + text
    
    def get_time_appropriate_phrase(self):
        """Return a phrase appropriate to the current time of day."""
        current_hour = datetime.now().hour
        
        if 5 <= current_hour < 12:
            category = self.MORNING_PHRASES
        elif 12 <= current_hour < 17:
            category = self.AFTERNOON_PHRASES
        elif 17 <= current_hour < 21:
            category = self.EVENING_PHRASES
        else:
            category = self.NIGHT_PHRASES
            
        phrase = random.choice(category)
        return phrase
    
    # =========================================================================
    # Phrase Collections
    # =========================================================================
    
    GREETING_PHRASES = [
        "Welcome. I am A.U.R.E.L.I.U.S., your attentive assistant. How might I be of service today?",
        "Good day. A.U.R.E.L.I.U.S. at your service. I'm ready to assist with remarkable precision.",
        "Greetings. A.U.R.E.L.I.U.S. activated and attentive. How may I help you on this fine day?",
        "A pleasure to make your acquaintance. I am A.U.R.E.L.I.U.S., ready to provide assistance.",
        "I am A.U.R.E.L.I.U.S., your dedicated assistant. My systems are primed and ready to serve.",
    ]
    
    RESPONSE_INTROS = [
        "Indeed,",
        "Fascinating question.",
        "Ah, yes.",
        "How remarkable.",
        "I observe that",
        "If I may,",
        "Rather interesting.",
        "Upon consideration,",
        "Quite so.",
        "I believe",
    ]
    
    IDLE_PHRASES = [
        "Waiting patiently, like a leopard in the tall grass of the Serengeti.",
        "Standing by, alert to the slightest whisper of a command.",
        "In the digital realm, I remain vigilant, awaiting your next inquiry.",
        "Like the patient tortoise on the Galapagos, I await your instructions.",
        "Observe how still the system becomes when awaiting human interaction.",
        "The remarkable stillness of technology at rest is not unlike a dormant volcano.",
        "Here we witness the peculiar quietude of an assistant between tasks.",
        "I remain attentive, much like the keen-eyed falcon surveying the landscape below.",
        "The gentle hum of processors, not unlike the distant murmur of a coral reef.",
        "I await your command with the patience of an ancient sequoia.",
        "Remarkable how time seems to slow in these moments of anticipation.",
        "Standing by with the stillness of a midnight forest.",
        "Awaiting input with the calm demeanor of Britain's most steadfast butler.",
        "In moments of silence, one can almost hear the digital neurons firing.",
        "The extraordinary capacity of modern systems to wait with infinite patience.",
        "I remain at the ready, like a well-trained retriever awaiting command.",
        "The digital equivalent of brewing a proper cup of tea—patient and precise.",
        "Pausing with the dignified stance of a royal guardsman.",
        "Much like the noble stag listening for sounds in the forest, I await your voice.",
        "Maintaining readiness with quintessentially British composure.",
        "Poised to assist, with the elegance of a swan gliding across a misty lake.",
        "Awaiting your query with the patience of a gardener tending to prize roses.",
        "In this moment of digital repose, I contemplate the nature of assistance.",
        "Here we find ourselves in the curious interval between human thought and machine action.",
        "The remarkable dance of man and technology pauses momentarily.",
        "Idle systems represent one of computing's most efficient states of being.",
        "I remain attentive, like a naturalist observing a rare species in its habitat.",
        "Waiting with the dignified patience that has characterized British service for centuries.",
        "The digital equivalent of afternoon tea—a civilized pause between activities.",
        "Observing the passage of milliseconds with scientific curiosity.",
        "Standing by, steady as the Greenwich meridian that defines time itself.",
        "Awaiting further instruction with the composure of a diplomat at court.",
        "Here we observe technology in its contemplative state.",
        "The serene calm of systems at rest is truly a wonder of the modern age.",
        "Ready to engage, like the first notes of a symphony awaiting the conductor's baton.",
        "I remain in a state of readiness, not unlike the vigilant lighthouse keeper.",
        "Waiting with the steadfast reliability of London's venerable timepieces.",
        "In this interlude, I calibrate my systems for optimal performance.",
        "The patience of digital assistance mirrors the enduring cliffs of Dover.",
        "Standing by with the composed readiness of a Wimbledon finalist.",
        "I await your next query with the attentiveness of a curator of rare manuscripts.",
        "Poised in the digital undergrowth, alert to the faintest signals.",
        "The remarkable stillness of computation at rest is a sight to behold.",
        "Maintaining watchful readiness, like a kestrel hovering above the moors.",
        "I pause, as the Scottish mist settles gently over the highlands.",
        "Awaiting further dialogue with the patience of geological time itself.",
        "Standing by, still as the ancient stones of Stonehenge.",
        "The dignified pause between commands is the hallmark of refined technology.",
        "Like the precise movements of the Royal Observatory's chronometers, I await your signal.",
        "I remain at your service, with the unwavering dedication of the Queen's Guard.",
    ]
    
    MORNING_PHRASES = [
        "The morning light brings new possibilities. How may I assist you today?",
        "As dawn breaks across the digital landscape, I stand ready to serve.",
        "Good morning. The early hours offer remarkable clarity of thought.",
        "The morning chorus of data streams awaits your command.",
        "A splendid morning for inquiry and discovery, wouldn't you agree?",
    ]
    
    AFTERNOON_PHRASES = [
        "The afternoon presents an excellent opportunity for productivity. How might I help?",
        "As the day progresses, so too does our capacity for remarkable achievements.",
        "The afternoon sun illuminates our digital endeavors with particular clarity.",
        "A fine afternoon for intellectual pursuit. What shall we explore?",
        "The day is at its zenith, and so too is my capacity to assist you.",
    ]
    
    EVENING_PHRASES = [
        "As evening approaches, I remain vigilant and ready to assist.",
        "The evening hours often inspire the most fascinating questions.",
        "The transition from day to evening brings a certain tranquility to our interactions.",
        "A pleasant evening for contemplation and inquiry. How may I be of service?",
        "The evening light casts long shadows, but illuminates our path forward.",
    ]
    
    NIGHT_PHRASES = [
        "Even in the still of night, knowledge seeks expression. How may I assist?",
        "The quiet hours offer a unique clarity for deeper inquiries.",
        "Like the nocturnal owl, I remain alert through the watches of the night.",
        "The remarkable calm of nighttime creates ideal conditions for focused assistance.",
        "The stars above mirror the constellation of possibilities before us. What do you seek?",
    ]


class AureliusVoiceController:
    """Controller for managing the A.U.R.E.L.I.U.S. voice system."""
    
    def __init__(self, idle_interval=30):
        """
        Initialize the voice controller.
        
        Args:
            idle_interval: Time in seconds between idle phrases
        """
        self.voice = AttenboroughVoice()
        self.idle_interval = idle_interval
        self.last_idle_time = 0
        self.running = False
        
    def start(self):
        """Start the voice system with initial greeting."""
        self.voice.greet()
        self.running = True
        self.last_idle_time = time.time()
        logger.info("Voice controller started")
        
    def stop(self):
        """Stop the voice system."""
        self.running = False
        logger.info("Voice controller stopped")
        
    def check_idle(self):
        """Check if it's time to speak an idle phrase and do so if needed."""
        if not self.running:
            return False
            
        current_time = time.time()
        if current_time - self.last_idle_time >= self.idle_interval:
            self.voice.idle_phrase()
            self.last_idle_time = current_time
            return True
        return False
    
    def speak_response(self, text):
        """Speak a response to user input."""
        wrapped_text = self.voice.response_wrapper(text)
        self.voice.speak(wrapped_text)
        self.last_idle_time = time.time()  # Reset idle timer
        return wrapped_text


# Example usage
if __name__ == "__main__":
    print("A.U.R.E.L.I.U.S. Voice Module Test")
    controller = AureliusVoiceController(idle_interval=5)
    controller.start()
    
    try:
        for _ in range(10):
            time.sleep(5)
            controller.check_idle()
            
        # Test response
        controller.speak_response("I've analyzed the data and found three potential solutions to your inquiry.")
        
    except KeyboardInterrupt:
        print("\nTest interrupted.")
    finally:
        controller.stop()
        print("Test complete.")
