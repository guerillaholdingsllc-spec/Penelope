import json
import os

KEYS_FILE = "keys.json"


def load_keys():
    if os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_keys(keys):
    with open(KEYS_FILE, "w") as f:
        json.dump(keys, f, indent=4)


def get_key(name):
    keys = load_keys()
    return keys.get(name)


def set_key(name, value):
    keys = load_keys()
    keys[name] = value
    save_keys(keys)


def delete_key(name):
    keys = load_keys()
    if name in keys:
        del keys[name]
        save_keys(keys)


def list_keys():
    return load_keys().keys()


if __name__ == "__main__":
    print("Keys Manager Ready")
