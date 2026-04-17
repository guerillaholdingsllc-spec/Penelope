import os
import subprocess
from docx import Document

def pull_latest_knowledge():
    print("Pulling latest instructions from GitHub...")
    subprocess.run(["git", "pull"], cwd="/root/workspace/Penelope")

def read_word_docs(folder_path):
    knowledge_base = ""
    for filename in os.listdir(folder_path):
        if filename.endswith(".docx"):
            print(f"Reading: {filename}")
            doc = Document(os.path.join(folder_path, filename))
            for para in doc.paragraphs:
                knowledge_base += para.text + "\n"
    return knowledge_base

if __name__ == "__main__":
    pull_latest_knowledge()
    # Replace 'knowledge' with the folder where your Word docs are stored
    content = read_word_docs("/root/workspace/Penelope") 
    print("Knowledge sync complete. Penelope is now updated.")
