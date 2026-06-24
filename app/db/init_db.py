import asyncio
from sqlalchemy import select
from app.core.database import async_session_maker
from app.core.constants import UserRole, DaycareStatus, GuardianStatus, ChildStatus
from app.core.security import get_password_hash
from app.modules.auth.models import User
from app.modules.daycares.models import Daycare
from app.modules.guardians.models import Guardian, GuardianChild, GuardianDaycare
from app.modules.children.models import Child

async def seed_data():
    """
    Inserta datos semilla iniciales para pruebas del sistema.
    Es re-ejecutable sin causar duplicaciones de llaves.
    """
    print("Iniciando inserción de datos semilla...")
    async with async_session_maker() as db:
        # 1. Crear Administrador del Sistema
        admin_exists = await db.execute(select(User).filter(User.username == "admin"))
        if not admin_exists.scalar_one_or_none():
            admin = User(
                username="admin",
                email="admin@example.com",
                hashed_password=get_password_hash("adminpassword"),
                role=UserRole.ADMIN
            )
            db.add(admin)
            print("Usuario ADMIN creado: admin / adminpassword")

        # 2. Crear Guarderías
        daycares_data = [
            {"code": "GUA-SCZ-001", "name": "Guardería Los Pinos", "address": "Santa Cruz de la Sierra"},
            {"code": "GUA-SCZ-002", "name": "Guardería Mi Segundo Hogar", "address": "Santa Cruz de la Sierra"},
            {"code": "GUA-SCZ-003", "name": "Kinder San Mateo", "address": "Santa Cruz de la Sierra"}
        ]
        
        daycare_map = {}
        for dc in daycares_data:
            existing = await db.execute(select(Daycare).filter(Daycare.code == dc["code"]))
            db_dc = existing.scalar_one_or_none()
            if not db_dc:
                db_dc = Daycare(
                    code=dc["code"],
                    name=dc["name"],
                    address=dc["address"],
                    status=DaycareStatus.ACTIVE
                )
                db.add(db_dc)
                await db.flush()
                print(f"Guardería creada: {dc['code']} - {dc['name']}")
            daycare_map[dc["code"]] = db_dc

        # 3. Crear Niños
        children_data = [
            {"code": "NIN-8F42K", "name": "Mateo Vargas", "age": 4, "daycare_code": "GUA-SCZ-001"},
            {"code": "NIN-3P91A", "name": "Luciana Rojas", "age": 5, "daycare_code": "GUA-SCZ-001"},
            {"code": "NIN-7M22B", "name": "Diego Suárez", "age": 3, "daycare_code": "GUA-SCZ-002"},
            {"code": "NIN-5T10C", "name": "Camila Méndez", "age": 4, "daycare_code": "GUA-SCZ-003"}
        ]

        child_map = {}
        for ch in children_data:
            existing = await db.execute(select(Child).filter(Child.code == ch["code"]))
            db_ch = existing.scalar_one_or_none()
            if not db_ch:
                db_ch = Child(
                    code=ch["code"],
                    full_name=ch["name"],
                    age=ch["age"],
                    daycare_id=daycare_map[ch["daycare_code"]].id,
                    status=ChildStatus.ACTIVE
                )
                db.add(db_ch)
                await db.flush()
                print(f"Niño registrado: {ch['code']} - {ch['name']}")
            child_map[ch["code"]] = db_ch

        # 4. Crear Tutor (Ana Vargas)
        guardian_email = "ana@example.com"
        existing_g = await db.execute(select(Guardian).filter(Guardian.email == guardian_email))
        db_g = existing_g.scalar_one_or_none()
        if not db_g:
            db_g = Guardian(
                full_name="Ana Vargas",
                phone="70000001",
                email=guardian_email,
                status=GuardianStatus.ACTIVE
            )
            db.add(db_g)
            await db.flush()
            
            # Asociar credenciales para login del tutor
            db_user_g = User(
                username="ana",
                email=guardian_email,
                hashed_password=get_password_hash("password123"),
                role=UserRole.GUARDIAN,
                guardian_id=db_g.id
            )
            db.add(db_user_g)
            print("Tutor creado: Ana Vargas. Login: ana / password123")
            
            # Vinculaciones requeridas:
            # A. Ana Vargas -> Guardería Los Pinos (GUA-SCZ-001)
            link_dc = GuardianDaycare(
                guardian_id=db_g.id,
                daycare_id=daycare_map["GUA-SCZ-001"].id
            )
            db.add(link_dc)
            
            # B. Ana Vargas -> Mateo Vargas (NIN-8F42K)
            link_c1 = GuardianChild(
                guardian_id=db_g.id,
                child_id=child_map["NIN-8F42K"].id,
                relationship="MADRE"
            )
            db.add(link_c1)
            
            # C. Ana Vargas -> Luciana Rojas (NIN-3P91A)
            link_c2 = GuardianChild(
                guardian_id=db_g.id,
                child_id=child_map["NIN-3P91A"].id,
                relationship="MADRE"
            )
            db.add(link_c2)
            print("Vinculación de Ana Vargas establecida con: Guardería Los Pinos, Mateo y Luciana.")

        await db.commit()
        print("¡Datos semilla insertados correctamente en la base de datos!")

if __name__ == "__main__":
    asyncio.run(seed_data())
