import os
import subprocess
import sys
import shutil

def main():
    print("="*50)
    print("Iniciando a Forja Definitiva do Wakfu Damage Overlay...")
    print("="*50)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    app_version = "v1.2.9" 
    
    # 1. Faxina completa
    print("\n[0/4] Limpando cache...")
    for path in ['build', 'dist', 'WakfuDamageOverlay.spec']:
        full_path = os.path.join(base_dir, path)
        if os.path.exists(full_path):
            if os.path.isdir(full_path):
                shutil.rmtree(full_path, ignore_errors=True)
            else:
                os.remove(full_path)

    # 2. Bibliotecas
    try:
        from PIL import Image
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
        from PIL import Image

    try:
        import PyInstaller
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    png_file = os.path.join(base_dir, "wakfu_tray_icon.png")
    ico_file = os.path.join(base_dir, "wakfu_tray_icon.ico")
    main_script = os.path.join(base_dir, "wakfu_overlay.py")

    # 3. Conversão Simplificada do Ícone
    if os.path.exists(png_file):
        print("\n[1/4] Convertendo PNG para ICO...")
        try:
            img = Image.open(png_file)
            img.save(ico_file, format="ICO")
            print("✔ Ícone criado!")
        except Exception as e:
            print(f"❌ Erro ao converter a imagem: {e}")
    else:
        print(f"\n[1/4] AVISO: Imagem '{png_file}' não encontrada na pasta.")

    # 4. Compilação no formato Pasta (OneDir) para evitar alertas de vírus
    print("\n[2/4] Compilando o executável no formato Pasta (OneDir)...")
    
    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",      
        "--onedir",         
        "--windowed",       
        "--name", "WakfuDamageOverlay"
    ]

    if os.path.exists(ico_file):
        pyinstaller_cmd.extend(["--icon", ico_file])

    pyinstaller_cmd.append(main_script)

    try:
        subprocess.check_call(pyinstaller_cmd)
        print("✔ Compilação concluída!")
    except Exception as e:
        print("\n❌ Ocorreu um erro durante a compilação:")
        print(e)
        input("\nPressione ENTER para sair...")
        return

    # 5. Compactação Automática (.zip)
    print("\n[3/4] Compactando tudo em um arquivo .zip para o itch.io...")
    try:
        dist_folder = os.path.join(base_dir, "dist", "WakfuDamageOverlay")
        zip_output_name = os.path.join(base_dir, "dist", f"WakfuDamageOverlay_{app_version}")
        
        shutil.make_archive(zip_output_name, 'zip', dist_folder)
        print("✔ Pasta compactada com sucesso!")
        
        print("\n" + "="*50)
        print("✅ FORJA CONCLUÍDA COM SUCESSO!")
        print(f"Pegue o seu arquivo WakfuDamageOverlay_{app_version}.zip dentro da pasta 'dist'.")
        print("Ele está pronto para ser publicado no itch.io!")
        print("="*50)
    except Exception as e:
        print(f"\n❌ Erro ao compactar a pasta: {e}")

    input("\nPressione ENTER para sair...")

if __name__ == "__main__":
    main()