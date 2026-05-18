import os
import sys
sys.path.append(r"J:\CONSENSUS_SYSTEM")
from CONSENSUS_SYSTEM_WAR_ROOM_MAGI_EDITION import perform_tribunal_ritual, current_theme
from flask import Flask, request, jsonify

app = Flask("CONSENSUS_TRIBUNAL")

@app.route("/tribunal", methods=["POST"])
def tribunal():
    query = request.json.get("query", "")
    result = perform_tribunal_ritual(query)
    
    naming = {
        "eva": {"RATIONALIS":"CASPER-3", "AETERNUM":"BALTHASAR-2", "BELLATOR":"MELCHIOR-1"},
              "wh40k": {"RATIONALIS":"LOGI-COGITATOR", "AETERNUM":"TEMPORAL-ARCHIVIST", "BELLATOR":"TACTICA-PRIME"},
              "helldivers": {"RATIONALIS":"LIBERTY-LOGIC", "AETERNUM":"DEMOCRACY-ARCHIVE", "BELLATOR":"STRATAGEM-MASTER"}
             }.get(current_theme.value, {"RATIONALIS":"RATIONALIS", "AETERNUM":"AETERNUM", "BELLATOR":"BELLATOR"})
    
    response = f"""Commander,

The MAGI have spoken:

• {naming['RATIONALIS']} → {result['votes']['RATIONALIS']['vote']} ({result['votes']['RATIONALIS']['confidence']:.0%})
• {naming['AETERNUM']} → {result['votes']['AETERNUM']['vote']} ({result['votes']['AETERNUM']['confidence']:.0%})
• {naming['BELLATOR']} → {result['votes']['BELLATOR']['vote']} ({result['votes']['BELLATOR']['confidence']:.0%})

FINAL VERDICT: **{result['verdict']}** — {result['confidence']:.0%} certainty."""
    if result.get("arbiter_used"):
        response += "\n\nThe ARBITER has overridden all three. Absolute judgement executed."
    
    return jsonify({"response": response})

if __name__ == "__main__":
    # Ejecuta en segundo plano sin ventana
    import pythoncom, win32com.client
    pythoncom.CoInitialize()
    app.run(port=5000, threaded=True, use_reloader=False)