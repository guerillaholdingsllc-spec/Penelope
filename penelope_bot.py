from github_actions import create_test_file, create_issue
import threading
import os
from google import genai
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()

if not BOT_TOKEN or ":" not in BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is missing or invalid")

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY is missing")

client = genai.Client(api_key=GOOGLE_API_KEY)


def load_brain():
    try:
        path = "/root/workspace/Penelope/brain_dump.txt"
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
    except Exception as e:
        print(f"Brain Read Error: {e}")
    return "No specific instructions found."


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_msg = update.message.text or ""
        knowledge = load_brain()

        prompt = f"""Instructions from your Word Docs:
{knowledge}

User Question:
{user_msg}
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        reply_text = getattr(response, "text", None) or "I processed your message but had no text response."
        await update.message.reply_text(reply_text)

    except Exception as e:
        await update.message.reply_text(f"Error processing message: {e}")


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Penelope is running...")
    import dropship_agent
    threading.Thread(target=dropship_agent.run_dropship_agent, daemon=True).start()
    app.run_polling()


if __name__ == "__main__":
    main()

