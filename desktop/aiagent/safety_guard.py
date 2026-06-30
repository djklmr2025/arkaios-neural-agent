import tkinter as tk
from tkinter import messagebox

# Lista negra de palabras o comandos que siempre requieren confirmación
DANGEROUS_KEYWORDS = [
    "password", "rm -rf", "format", "delete", "drop table", 
    "shutdown", "rmdir", "del ", "contraseña", "sudo"
]

def prompt_user_permission(action: str, description: str) -> bool:
    """Muestra un modal de tkinter para pedir permiso al usuario."""
    root = tk.Tk()
    root.withdraw()  # Oculta la ventana principal
    root.attributes('-topmost', True)  # Asegura que aparezca encima de todo
    
    msg = (
        f"🛡️ El Agente ARKAIOS quiere ejecutar una acción sensible:\n\n"
        f"Acción: {action}\n"
        f"Detalles: {description}\n\n"
        f"¿Deseas PERMITIR esta acción?"
    )
    
    # Devuelve True si presiona "Sí", False si presiona "No"
    result = messagebox.askyesno("ARKAIOS Safety Guard", msg, parent=root)
    root.destroy()
    return result

def check_action_safety(action: str, params: dict) -> bool:
    """Evalúa si una acción es peligrosa y requiere confirmación.
    Retorna True si la acción está permitida, False si fue bloqueada.
    """
    if action == "type":
        text = params.get("text", "").lower()
        if any(keyword in text for keyword in DANGEROUS_KEYWORDS):
            return prompt_user_permission(action, f"Escribir texto confidencial/peligroso:\n'{text}'")
        
    elif action == "launch_app":
        app = params.get("app_name", "").lower()
        # Siempre pedir permiso para abrir terminales
        if app in ["cmd", "powershell", "terminal", "bash", "sh", "wt"]:
            return prompt_user_permission(action, f"Abrir aplicación de terminal: {app}")

    elif action == "key_combo":
        keys = params.get("keys", [])
        keys_lower = [str(k).lower() for k in keys]
        if "delete" in keys_lower or ("alt" in keys_lower and "f4" in keys_lower) or ("ctrl" in keys_lower and "c" in keys_lower):
            return prompt_user_permission(action, f"Atajo de teclado crítico: {' + '.join(keys)}")
            
    # Si no coincide con ninguna regla de peligro, se permite por defecto
    return True
