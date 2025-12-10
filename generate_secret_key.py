"""
Script para generar una SECRET_KEY segura para JWT
"""
import secrets

# Generar una clave secreta segura
secret_key = secrets.token_urlsafe(32)

print("=" * 60)
print("🔑 SECRET_KEY generada:")
print("=" * 60)
print(secret_key)
print("=" * 60)
print("\n📋 Copia este valor y úsalo como SECRET_KEY en tus variables de entorno")
print("=" * 60)


