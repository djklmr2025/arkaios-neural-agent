import google.generativeai as genai, os; genai.configure(api_key=os.environ.get(" GEMINI_API_KEY\, \AIzaSyBzTXJoGc8sNhsoP1K8Xy3VoAz6aAYhEAg\)); print([m.name for m in genai.list_models()])
