import os
import subprocess
from docx import Document

def update_repo():
    print("Checking GitHub for new instructions...")
    subprocess.run(["git", "pull"], cwd="/root/workspace/Penelope")

def get_knowledge_base(folder):
    full_text = []
    for file in os.listdir(folder):
        if file.endswith(".docx") and not file.startswith("~$"):
            try:
                doc = Document(os.path.join(folder, file))
                text = [p.text for p in doc.paragraphs]
                full_text.append(f"--- SOURCE: {file} ---\n" + "\n".join(text))
            except Exception as e:
                print(f"Error reading {file}: {e}")
    return "\n\n".join(full_text)

if __name__ == "__main__":
    update_repo()
    content = get_knowledge_base("/root/workspace/Penelope")
    with open("/root/workspace/Penelope/brain_dump.txt", "w") as f:
        f.write(content)
    print("Knowledge Base Updated.")


import os
from google import genai

def _get_gemini_client():
    """Lazy Gemini client — loads key from vault at call time."""
    import os as _o
    key = _o.getenv("GOOGLE_API_KEY", "")
    if not key:
        try:
            for line in open("/root/penelope_vault.env"):
                if line.strip().startswith("GOOGLE_API_KEY="):
                    key = line.strip().split("=", 1)[1].strip()
                    break
        except: pass
    if not key:
        return None
    from google import genai as _g
    return _g.Client(api_key=key)

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Load from Vault
# model migrated
_genai_model_name = 'gemini-1.5-flash'

def load_brain():
    try:
        with open("/root/workspace/Penelope/brain_dump.txt", "r") as f:
            return f.read()
    except:
        return "No specific instructions found."

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    knowledge = load_brain()
    user_msg = update.message.text
    
    prompt = f"""
    SYSTEM INSTRUCTIONS:
        pass
    You are Penelope, an autonomous AI agent. 
    Your mission is based on these documents:
        pass
    {knowledge}
    
    User says: {user_msg}
    """
    
    response = model.generate_content(prompt)
    await update.message.reply_text(response.text)

def main():
    app = Application.builder().token(os.getenv("BOT_TOKEN")).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()