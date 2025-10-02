#!/usr/bin/env python3
"""
Script d'installation automatique des dépendances
Détecte Python + OS et installe la bonne version d'ifcopenshell
"""

import sys
import platform
import subprocess
import os

def get_system_info():
    """Détecte Python version et OS"""
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    system = platform.system()
    machine = platform.machine()
    
    # Sur Windows, détection plus précise
    if system == 'Windows':
        import struct
        is_64bits = struct.calcsize("P") * 8 == 64
        machine = 'AMD64' if is_64bits else 'x86'
    
    return {
        'python': py_version,
        'system': system,
        'machine': machine,
        'is_64bits': machine in ['AMD64', 'x86_64', 'arm64', 'aarch64']
    }

def print_conda_instructions():
    """Affiche les instructions pour installer avec conda"""
    print("\n" + "="*60)
    print("💡 SOLUTION RECOMMANDÉE : Installer avec Conda")
    print("="*60)
    print("\n1️⃣ Télécharger Miniconda (gratuit, 5 min) :")
    print("   👉 https://docs.conda.io/en/latest/miniconda.html")
    print("   - Windows : Télécharger Miniconda3-latest-Windows-x86_64.exe")
    print("   - Installer avec les options par défaut")
    print()
    print("2️⃣ Ouvrir 'Anaconda Prompt' (chercher dans menu démarrer)")
    print()
    print("3️⃣ Dans Anaconda Prompt, taper ces commandes :")
    print("   cd chemin\\vers\\WLC-PLATFORM-ETS")
    print("   conda create -n wlc python=3.11 -y")
    print("   conda activate wlc")
    print("   conda install -c conda-forge ifcopenshell -y")
    print("   pip install -r Backend/requirements.txt")
    print()
    print("4️⃣ Lancer l'app :")
    print("   cd Backend")
    print("   python app.py")
    print("="*60)

def get_ifcopenshell_wheel(info):
    """Retourne l'URL du wheel ifcopenshell approprié"""
    
    # Base URL GitHub IfcOpenShell releases
    base = "https://github.com/IfcOpenShell/IfcOpenShell/releases/download"
    release = "blenderbim-240915"  # Version stable
    
    # Mapping Python version → wheel
    wheels = {
        # macOS (Darwin)
        ('Darwin', '3.8'): f"{base}/{release}/ifcopenshell-0.8.0-py38-none-macosx_11_0_arm64.whl",
        ('Darwin', '3.9'): f"{base}/{release}/ifcopenshell-0.8.0-py39-none-macosx_11_0_arm64.whl",
        ('Darwin', '3.10'): f"{base}/{release}/ifcopenshell-0.8.0-py310-none-macosx_11_0_arm64.whl",
        ('Darwin', '3.11'): f"{base}/{release}/ifcopenshell-0.8.0-py311-none-macosx_11_0_arm64.whl",
        ('Darwin', '3.12'): f"{base}/{release}/ifcopenshell-0.8.0-py312-none-macosx_11_0_arm64.whl",
        ('Darwin', '3.13'): f"{base}/{release}/ifcopenshell-0.8.0-py312-none-macosx_11_0_arm64.whl",  # Utiliser py312
        
        # Windows
        ('Windows', '3.8'): f"{base}/{release}/ifcopenshell-0.8.0-py38-none-win_amd64.whl",
        ('Windows', '3.9'): f"{base}/{release}/ifcopenshell-0.8.0-py39-none-win_amd64.whl",
        ('Windows', '3.10'): f"{base}/{release}/ifcopenshell-0.8.0-py310-none-win_amd64.whl",
        ('Windows', '3.11'): f"{base}/{release}/ifcopenshell-0.8.0-py311-none-win_amd64.whl",
        ('Windows', '3.12'): f"{base}/{release}/ifcopenshell-0.8.0-py312-none-win_amd64.whl",
        ('Windows', '3.13'): f"{base}/{release}/ifcopenshell-0.8.0-py312-none-win_amd64.whl",
        
        # Linux
        ('Linux', '3.8'): f"{base}/{release}/ifcopenshell-0.8.0-py38-none-manylinux_2_28_x86_64.whl",
        ('Linux', '3.9'): f"{base}/{release}/ifcopenshell-0.8.0-py39-none-manylinux_2_28_x86_64.whl",
        ('Linux', '3.10'): f"{base}/{release}/ifcopenshell-0.8.0-py310-none-manylinux_2_28_x86_64.whl",
        ('Linux', '3.11'): f"{base}/{release}/ifcopenshell-0.8.0-py311-none-manylinux_2_28_x86_64.whl",
        ('Linux', '3.12'): f"{base}/{release}/ifcopenshell-0.8.0-py312-none-manylinux_2_28_x86_64.whl",
        ('Linux', '3.13'): f"{base}/{release}/ifcopenshell-0.8.0-py312-none-manylinux_2_28_x86_64.whl",
    }
    
    key = (info['system'], info['python'])
    return wheels.get(key)

def install_dependencies():
    """Installe toutes les dépendances avec le bon ifcopenshell"""
    
    print("🔍 Détection du système...")
    info = get_system_info()
    print(f"   Python: {info['python']}")
    print(f"   OS: {info['system']} ({info['machine']})")
    
    # Déterminer le fichier requirements
    req_file = "Backend/requirements.txt"
    if not os.path.exists(req_file):
        print(f"❌ Fichier {req_file} introuvable")
        return False
    
    print(f"\n📦 Installation des dépendances de base...")
    # Installer toutes les dépendances SAUF ifcopenshell
    with open(req_file, 'r') as f:
        lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    # Filtrer ifcopenshell
    other_deps = [line for line in lines if not line.startswith('ifcopenshell')]
    
    for dep in other_deps:
        print(f"   Installing {dep}...")
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', dep], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print(f"   ⚠️  Erreur: {dep}")
    
    print(f"\n🔧 Installation d'ifcopenshell...")
    wheel_url = get_ifcopenshell_wheel(info)
    
    if not wheel_url:
        print(f"❌ Pas de wheel ifcopenshell disponible pour Python {info['python']} sur {info['system']}")
        print_conda_instructions()
        return False
    
    print(f"   Téléchargement depuis GitHub...")
    print(f"   URL: {wheel_url}")
    
    result = subprocess.run([sys.executable, '-m', 'pip', 'install', wheel_url],
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"   ✅ ifcopenshell installé avec succès!")
        return True
    else:
        print(f"   ❌ Erreur lors de l'installation d'ifcopenshell")
        print(f"   Détails: {result.stderr[:200]}")
        print_conda_instructions()
        return False

def main():
    print("=" * 60)
    print("🚀 Installation Automatique des Dépendances - Plateforme WLC")
    print("=" * 60)
    print()
    
    # Vérifier qu'on est dans un venv
    if sys.prefix == sys.base_prefix:
        print("⚠️  ATTENTION: Vous n'êtes pas dans un environnement virtuel!")
        print("\n💡 Créez et activez un venv d'abord:")
        print("   python -m venv venv")
        print("   source venv/bin/activate  (ou venv\\Scripts\\activate sur Windows)")
        print()
        response = input("Continuer quand même? (oui/non): ")
        if response.lower() not in ['oui', 'yes', 'y', 'o']:
            print("❌ Installation annulée")
            return
    
    success = install_dependencies()
    
    print()
    print("=" * 60)
    if success:
        print("✅ Installation terminée avec succès!")
        print("\n🚀 Vous pouvez maintenant lancer l'application:")
        print("   cd Backend")
        print("   python app.py")
    else:
        print("⚠️  Installation terminée avec des avertissements")
        print("   Certaines dépendances peuvent nécessiter une installation manuelle")
    print("=" * 60)

if __name__ == "__main__":
    main()

