"""
Téléchargement automatique des fichiers depuis Google Drive
Ce fichier est appelé automatiquement au démarrage de app.py
"""

import os
import requests
import zipfile
import shutil
from pathlib import Path

# ══════════════════════════════════════════════════════
# IDs Google Drive
# ══════════════════════════════════════════════════════
DRIVE_FOLDERS = {
    "data":      "1GyAG_D9to_N-g7w1a_9s4rM1OagyIjiM",
    "models":    "1KZbtqpPBHvNpZiIir-U4IMmD6caEHQfQ",
    "models_m2": "1SlBqUXfyNRAb7GSvuYNOGir5GQYX4g_S",
}

# Fichiers individuels critiques (à télécharger en priorité)
# Format : (chemin_local, id_google_drive)
DRIVE_FILES = [
    # ── models ──
    ("models/global_lstm.keras",     None),  # sera rempli automatiquement
    ("models/scaler.pkl",            None),

    # ── models_m2 ──
    ("models_m2/global_lstm_aqua.keras",   None),
    ("models_m2/global_lstm_dessal.keras", None),
    ("models_m2/scaler_aqua.pkl",          None),
    ("models_m2/scaler_dessal.pkl",        None),
    ("models_m2/seuil_config_m2.json",     None),
]


def _download_file_from_drive(file_id: str, dest_path: str) -> bool:
    """Télécharge un fichier Google Drive par son ID."""
    os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)
    URL = "https://drive.google.com/uc?export=download"
    session = requests.Session()

    try:
        response = session.get(URL, params={"id": file_id}, stream=True, timeout=60)
        # Gestion du warning "fichier volumineux"
        token = None
        for key, value in response.cookies.items():
            if key.startswith("download_warning"):
                token = value
                break

        if token:
            response = session.get(
                URL,
                params={"id": file_id, "confirm": token},
                stream=True,
                timeout=300,
            )

        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=32768):
                if chunk:
                    f.write(chunk)

        size_mb = os.path.getsize(dest_path) / (1024 * 1024)
        print(f"  ✅ {dest_path} ({size_mb:.1f} MB)")
        return True

    except Exception as e:
        print(f"  ❌ Erreur téléchargement {dest_path} : {e}")
        return False


def _list_drive_folder(folder_id: str):
    """Liste les fichiers d'un dossier Google Drive (API publique)."""
    url = (
        f"https://drive.google.com/drive/folders/{folder_id}"
    )
    # Utilise l'API Drive v3 en mode public
    api_url = (
        f"https://www.googleapis.com/drive/v3/files"
        f"?q='{folder_id}'+in+parents"
        f"&fields=files(id,name,mimeType)"
        f"&key=AIzaSyD-fake-key-replace-if-needed"
    )
    try:
        resp = requests.get(api_url, timeout=30)
        if resp.status_code == 200:
            return resp.json().get("files", [])
    except Exception:
        pass
    return []


def download_folder_as_zip(folder_id: str, dest_dir: str) -> bool:
    """
    Télécharge un dossier Google Drive entier via l'export ZIP.
    Fonctionne uniquement si le dossier est partagé publiquement.
    """
    os.makedirs(dest_dir, exist_ok=True)
    zip_url = f"https://drive.google.com/drive/folders/{folder_id}"
    download_url = (
        f"https://drive.google.com/uc?export=download&id={folder_id}"
    )

    # Méthode alternative : utiliser gdown
    try:
        import gdown
        output_zip = f"{dest_dir}.zip"
        gdown.download_folder(
            id=folder_id,
            output=dest_dir,
            quiet=False,
            use_cookies=False,
        )
        print(f"  ✅ Dossier {dest_dir} téléchargé via gdown")
        return True
    except Exception as e:
        print(f"  ⚠️ gdown folder : {e}")

    return False


def ensure_data_available():
    """
    Vérifie et télécharge les fichiers manquants depuis Google Drive.
    Appelé au démarrage de app.py via st.cache_resource.
    """
    import streamlit as st

    # Dossiers à vérifier
    checks = {
        "data/lstm_final_clean":               ("data", "lstm_final_clean"),
        "data/dataset_model2_1999_2023_clean": ("data", "dataset_model2_1999_2023_clean"),
        "models":                              ("models", None),
        "models_m2":                           ("models_m2", None),
    }

    missing = []
    for path, _ in checks.items():
        if not os.path.exists(path):
            missing.append(path)

    if not missing:
        print("✅ Tous les fichiers sont déjà présents localement.")
        return True

    print(f"📥 Fichiers manquants : {missing}")
    print("⬇️ Téléchargement depuis Google Drive...")

    success = True

    # Télécharger chaque dossier manquant
    folders_to_download = set()
    for path in missing:
        if path.startswith("data"):
            folders_to_download.add("data")
        elif path.startswith("models_m2"):
            folders_to_download.add("models_m2")
        elif path.startswith("models"):
            folders_to_download.add("models")

    for folder_name in folders_to_download:
        folder_id = DRIVE_FOLDERS[folder_name]
        print(f"\n📁 Téléchargement dossier : {folder_name}")
        ok = download_folder_as_zip(folder_id, folder_name)
        if not ok:
            print(f"  ⚠️ Impossible de télécharger {folder_name} automatiquement.")
            st.warning(
                f"⚠️ Le dossier `{folder_name}` n'a pas pu être téléchargé automatiquement.\n\n"
                f"Lien Drive : https://drive.google.com/drive/folders/{folder_id}"
            )
            success = False

    return success


if __name__ == "__main__":
    ensure_data_available()
