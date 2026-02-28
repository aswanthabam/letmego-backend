import asyncio
import os
import sys
from uuid import UUID

# Add backend directory to path so we can import apps
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from avcfastapi.core.database.sqlalchamey.core import AsyncSessionLocal
from sqlalchemy import select
from apps.api.parking.models import ParkingSlot, ParkingSlotStaff
from apps.api.apartment.models import Apartment
from apps.api.organization.models import Organization, OrganizationMember, OrganizationType, OrganizationRole
from apps.api.user.models import User

async def run_backfill():
    print("🚀 Starting B2B Multi-Tenant Data Backfill Script...")
    
    async with AsyncSessionLocal() as session:
        
        # 1. Backfill Parking Slot Owners
        print("\n--- Processing Parking Slots ---")
        slots_query = select(ParkingSlot).where(
            ParkingSlot.organization_id.is_(None),
            ParkingSlot.deleted_at.is_(None)
        )
        slots_result = await session.execute(slots_query)
        slots = slots_result.scalars().all()
        
        owner_org_map = {} # Maps owner_id to their new Organization ID
        
        for slot in slots:
            owner_id = slot.owner_id
            
            if owner_id not in owner_org_map:
                # Retrieve owner details to name the org
                user = await session.get(User, owner_id)
                org_name = f"{user.full_name or 'User'}'s Parking Operations"
                
                # Create the Organization
                org = Organization(
                    name=org_name,
                    type=OrganizationType.PARKING_OPERATOR
                )
                session.add(org)
                await session.flush()
                
                # Add the owner as ORG_ADMIN
                admin_member = OrganizationMember(
                    organization_id=org.id,
                    user_id=owner_id,
                    role=OrganizationRole.ORG_ADMIN
                )
                session.add(admin_member)
                await session.flush()
                
                owner_org_map[owner_id] = org.id
                print(f"Created Parking Org '{org_name}' for Owner ID {owner_id}")
            
            # Link Slot to Organization
            slot.organization_id = owner_org_map[owner_id]
            
        print(f"Migrated {len(slots)} Parking Slots to Organizations.")

        # 2. Backfill Apartment Admins
        print("\n--- Processing Apartments ---")
        apartments_query = select(Apartment).where(
            Apartment.organization_id.is_(None),
            Apartment.deleted_at.is_(None)
        )
        apt_result = await session.execute(apartments_query)
        apartments = apt_result.scalars().all()
        
        admin_org_map = {}
        
        for apt in apartments:
            admin_id = apt.admin_id
            
            if admin_id not in admin_org_map:
                user = await session.get(User, admin_id)
                org_name = f"{user.full_name or 'User'}'s Property Management"
                
                org = Organization(
                    name=org_name,
                    type=OrganizationType.PROPERTY_MANAGER
                )
                session.add(org)
                await session.flush()
                
                admin_member = OrganizationMember(
                    organization_id=org.id,
                    user_id=admin_id,
                    role=OrganizationRole.ORG_ADMIN
                )
                session.add(admin_member)
                await session.flush()
                
                admin_org_map[admin_id] = org.id
                print(f"Created Property Org '{org_name}' for Admin ID {admin_id}")
                
            apt.organization_id = admin_org_map[admin_id]
            
        print(f"Migrated {len(apartments)} Apartments to Organizations.")


        # 3. Migrate ParkingSlotStaff to OrganizationMember (GROUND_STAFF)
        print("\n--- Processing Legacy Staff Roles ---")
        staff_query = select(ParkingSlotStaff)
        staff_result = await session.execute(staff_query)
        legacy_staff = staff_result.scalars().all()
        
        migrated_staff_count = 0
        for staff in legacy_staff:
            slot = await session.get(ParkingSlot, staff.slot_id)
            if not slot or not slot.organization_id:
                continue # Skip if slot is deleted or not migrated
                
            # Check if membership already exists (e.g. they are the ORG_ADMIN already)
            existing_member_query = select(OrganizationMember).where(
                OrganizationMember.organization_id == slot.organization_id,
                OrganizationMember.user_id == staff.user_id
            )
            existing_member = (await session.execute(existing_member_query)).scalar_one_or_none()
            
            if not existing_member:
                # Add them to the organization as ground staff
                member = OrganizationMember(
                    organization_id=slot.organization_id,
                    user_id=staff.user_id,
                    role=OrganizationRole.GROUND_STAFF
                )
                session.add(member)
                migrated_staff_count += 1
                
        print(f"Migrated {migrated_staff_count} Legacy Slot Staff into Org Members.")

        # Commit everything!
        await session.commit()
        print("\n✅ Successfully committed all multi-tenant backfill data to the database!")

if __name__ == "__main__":
    asyncio.run(run_backfill())
