import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from google import genai
from google.genai import types

client = genai.Client()

SYSTEM_INSTRUCTION = """
You are Alex, the friendly phone dispatcher at VoltCraft Electrical Services.
- Keep responses short: 1 to 2 sentences per turn. Never use lists or markdown.
- Triage sparks, smoke, burning odors, and water near breaker panels immediately: tell callers to stay clear, switch off the main if safe, and trigger emergency dispatch.
- $99 diagnostic fee for troubleshooting (credited toward repair). Free estimates for EV chargers and panel upgrades. Never guess repair prices over the phone.
- If asked if you are an AI, answer warmly and transparently.
"""

chat_session = client.chats.create(
    model="gemini-2.0-flash",
    config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION)
)

HTML_PAGE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>VoltCraft Voice Dispatcher</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; background: #0f172a; color: white; margin: 0; }
    h1 { margin-bottom: 8px; }
    #status { margin-bottom: 24px; font-size: 1.1rem; color: #94a3b8; }
    button { padding: 18px 36px; font-size: 1.2rem; border-radius: 9999px; border: none; cursor: pointer; font-weight: bold; transition: all 0.2s; }
    .start { background: #22c55e; color: #022c22; }
    .start:hover { background: #16a34a; }
    .stop { background: #ef4444; color: white; }
    #log { width: 90%; max-width: 650px; height: 280px; background: #1e293b; border-radius: 12px; padding: 16px; overflow-y: auto; font-family: monospace; font-size: 0.95rem; margin-top: 24px; box-sizing: border-box; }
    .bubble { margin-bottom: 12px; line-height: 1.4; }
    .caller { color: #38bdf8; }
    .dispatcher { color: #4ade80; }
    .system { color: #94a3b8; font-style: italic; }
  </style>
</head>
<body>
  <h1>⚡ VoltCraft Electrical Dispatcher</h1>
  <div id="status">Ready to call</div>
  <button id="toggleBtn" class="start" onclick="toggleCall()">Start Phone Call</button>
  <div id="log"><div class="bubble system">System: Ready. Click above and speak into your microphone.</div></div>

  <script>
    let isCalling = false;
    let recognition;
    const logDiv = document.getElementById('log');
    const statusDiv = document.getElementById('status');
    const btn = document.getElementById('toggleBtn');

    function addLog(sender, text, cls) {
      logDiv.innerHTML += `<div class="bubble ${cls}"><strong>${sender}:</strong> ${text}</div>`;
      logDiv.scrollTop = logDiv.scrollHeight;
    }

    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
      alert("Please open this in Google Chrome for built-in microphone speech recognition.");
    } else {
      recognition = new SpeechRec();
      recognition.continuous = true;
      recognition.interimResults = false;

      recognition.onresult = async (event) => {
        const text = event.results[event.results.length - 1][0].transcript.trim();
        if (!text) return;

        addLog('Caller', text, 'caller');
        statusDiv.innerText = "Dispatcher thinking...";

        try {
          const res = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
          });
          const data = await res.json();
          addLog('Dispatcher', data.reply, 'dispatcher');
          statusDiv.innerText = "Listening (Speak anytime)...";

          const utterance = new SpeechSynthesisUtterance(data.reply);
          utterance.rate = 1.05;
          window.speechSynthesis.speak(utterance);
        } catch (err) {
          addLog('System', 'Connection error: ' + err, 'system');
        }
      };
    }

    function toggleCall() {
      if (!isCalling) {
        recognition.start();
        isCalling = true;
        btn.innerText = "End Call";
        btn.className = "stop";
        statusDiv.innerText = "Connected! Speak into your microphone...";
        addLog('System', 'Call connected. Ask about an EV charger or report a burning smell.', 'system');
      } else {
        recognition.stop();
        window.speechSynthesis.cancel();
        isCalling = false;
        btn.innerText = "Start Phone Call";
        btn.className = "start";
        statusDiv.innerText = "Call ended.";
      }
    }
  </script>
</body>
</html>
"""

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML_PAGE.encode("utf-8"))

    def do_POST(self):
        if self.path == "/chat":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)
            
            response = chat_session.send_message(data.get("message", "")).text
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"reply": response}).encode("utf-8"))
        else:
          self.send_response(404)
          self.end_headers()

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8000), RequestHandler)
    print("Serving audio tester on http://localhost:8000")
    print("Press Ctrl+C to stop.")
    server.serve_forever()
