import asyncio
import sys
import os
import json
import selectors
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.config.database import get_db, engine
from src.models.user import User
from src.auth.jwt_utils import get_password_hash
from seed_passwords import seed_password
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import AsyncSession
from src.config.database import get_db, engine
from src.models.user import User
from src.auth.jwt_utils import get_password_hash

# Lista de propietarios de activos
PROPIETARIOS_ACTIVOS = [
    "Jefe Oficina de Control Interno ",
    "Subdirección Financiera y Administrativa ",
    "Asesor de la Dirección para Comunicaciones y Servicio al Ciudadano",
    "Oficina de Control Disciplinario Interno",
    "Profesional Gestión Financiera",
    "Responsable Área de Contabilidad",
    "Responsable Área Cesantías",
    "Jefe de la Oficina Asesora de Planeación",
    "Profesional Universitario Grado 19 - AHL",
    "Jefe Oficina de Informática y Sistemas ",
    "Profesional especializado Subdirección de Prestaciones Económicas",
    "Profesional Subdirección de Prestaciones Económicas",
    "Profesional y Profesional especializado Subdirección de Prestaciones Económicas",
    "Técnico Operativo Subdirección de Prestaciones Económicas",
    "Gerencia de Pensiones",
    "Jefe Oficina Asesora de Jurídica",
    "Responsable Área Administrativa",
    "Jefe Oficina de Informática y Sistemas",
    "Responsable Área Talento Humano",
    "Responsable Área de Cartera y Jurisdicción coactiva",
    "Técnico operativo del Área de Cartera y Jurisdicción coactiva",
    "Profesional universitario y Técnico operativo del Área de Cartera y Jurisdicción coactiva",
    " Técnico operativo del Área de Cartera y Jurisdicción coactiva",
    "Profesionales Universitarios Jurisdicción coactiva",
    "Responsable Área Cesantías ",
    "Profesional Especializado Subdirección de Prestaciones Económicas",
    "Profesionales Subdirección de Prestaciones Económicas",
    "Técnico operativo Subdirección de Prestaciones Económicas",
    "Departamento de TI"
]

def create_username_from_dueno(dueno: str) -> str:
    """Create a username from the dueno_de_activo string"""
    # Remove extra spaces and convert to lowercase
    clean_dueno = dueno.strip().lower()
    
    # Replace spaces and special characters with underscores
    username = (clean_dueno
                .replace(" ", "_")
                .replace("ñ", "n")
                .replace("ó", "o")
                .replace("é", "e")
                .replace("í", "i")
                .replace("á", "a")
                .replace("ú", "u")
                .replace(".", "")
                .replace(",", "")
                .replace("-", "_"))
    
    # Remove multiple underscores
    while "__" in username:
        username = username.replace("__", "_")
    
    # Remove leading/trailing underscores
    username = username.strip("_")
    
    return username

def create_email_from_username(username: str) -> str:
    """Create an email from username"""
    return f"{username}@inventario.gov.co"

async def create_users():
    """Create users for each unique propietario and admin user"""
    # Remove duplicates while preserving order
    unique_propietarios = []
    seen = set()
    for prop in PROPIETARIOS_ACTIVOS:
        clean_prop = prop.strip()
        if clean_prop not in seen:
            seen.add(clean_prop)
            unique_propietarios.append(clean_prop)
    
    print(f"Creating users for {len(unique_propietarios)} unique propietarios...")
    
    # Store credentials for testing
    credentials_list = []
    
    async with AsyncSession(engine) as session:
        try:
            # Create admin user first
            admin_password = seed_password("SEED_ADMIN_PASSWORD")
            admin_user = User(
                email="admin@inventario.gov.co",
                username="admin",
                hashed_password=get_password_hash(admin_password),
                full_name="Administrador Principal",
                dueno_de_activo=None,  # Admin can see everything
                is_active=True,
                is_superuser=True
            )
            session.add(admin_user)
            
            # Add admin credentials to list
            credentials_list.append({
                "username": "admin",
                "email": "admin@inventario.gov.co",
                "password": admin_password,
                "full_name": "Administrador Principal",
                "dueno_de_activo": None,
                "is_superuser": True,
                "role": "ADMIN - Can see all assets"
            })
            
            print(f"✓ Created admin user: admin@inventario.gov.co")
            
            # Create users for each propietario
            created_count = 0
            for dueno in unique_propietarios:
                try:
                    username = create_username_from_dueno(dueno)
                    email = create_email_from_username(username)
                    
                    # Check if user already exists
                    existing_user = await session.execute(
                        select(User).where(
                            (User.username == username) | (User.email == email)
                        )
                    )
                    if existing_user.scalar_one_or_none():
                        print(f"⚠ User already exists: {username}")
                        continue
                    
                    # Random password per user, saved only to the git-ignored credentials file
                    default_password = seed_password()
                    
                    user = User(
                        email=email,
                        username=username,
                        hashed_password=get_password_hash(default_password),
                        full_name=dueno,
                        dueno_de_activo=dueno,
                        is_active=True,
                        is_superuser=False
                    )
                    
                    session.add(user)
                    created_count += 1
                    
                    # Add user credentials to list
                    credentials_list.append({
                        "username": username,
                        "email": email,
                        "password": default_password,
                        "full_name": dueno,
                        "dueno_de_activo": dueno,
                        "is_superuser": False,
                        "role": "USER - Can only see own assets"
                    })
                    
                    print(f"✓ Created user: {username} ({email}) for '{dueno}'")
                    
                except Exception as e:
                    print(f"✗ Error creating user for '{dueno}': {e}")
                    continue
            
            # Commit all changes
            await session.commit()
            
            print(f"\n🎉 Successfully created {created_count} users + 1 admin user!")
            print("\n📋 Quick reference:")
            print("Passwords: scripts/user_credentials.json (git-ignored, do not share)")
            
            return credentials_list
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error creating users: {e}")
            raise


def save_credentials_to_file(credentials_list):
    """Save credentials to JSON file for testing"""
    try:
        credentials_file = Path(__file__).parent / "user_credentials.json"
        with open(credentials_file, 'w', encoding='utf-8') as f:
            json.dump({
                "created_at": datetime.now().isoformat(),
                "total_users": len(credentials_list),
                "admin_users": 1,
                "regular_users": len(credentials_list) - 1,
                "credentials": credentials_list
            }, f, indent=2, ensure_ascii=False)
        
        print(f"📁 Credentials saved to: {credentials_file}")
        print("\n For detailed credentials, check the JSON file above.")
        
    except Exception as e:
        print(f"⚠ Warning: Could not save credentials file: {e}")


if __name__ == "__main__":
    # Fix for Windows ProactorEventLoop incompatibility with psycopg async
    import asyncio
    import selectors
    
    # Use SelectorEventLoop instead of ProactorEventLoop on Windows
    if hasattr(selectors, 'SelectSelector'):
        loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
        asyncio.set_event_loop(loop)
        credentials = loop.run_until_complete(create_users())
        loop.close()
    else:
        credentials = asyncio.run(create_users())
    
    if credentials:
        save_credentials_to_file(credentials)