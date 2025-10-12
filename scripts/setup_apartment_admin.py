# scripts/setup_apartment_admin.py
"""
Script to promote users to apartment_admin role.
Usage: python -m scripts.setup_apartment_admin <user_email>
"""

import asyncio
import sys
from sqlalchemy import select, update
from apps.api.user.models import User, UserRoles
from avcfastapi.core.database.sqlalchamey.core import get_session


async def promote_to_apartment_admin(user_email: str):
    """
    Promote a user to apartment_admin role.
    
    Args:
        user_email: Email of the user to promote
    """
    async with get_session() as session:
        # Find user by email
        result = await session.execute(
            select(User).where(User.email == user_email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"❌ User with email '{user_email}' not found")
            return
        
        if user.role == UserRoles.APARTMENT_ADMIN.value:
            print(f"ℹ️  User '{user.fullname}' ({user_email}) is already an apartment admin")
            return
        
        # Update role
        await session.execute(
            update(User)
            .where(User.id == user.id)
            .values(role=UserRoles.APARTMENT_ADMIN.value)
        )
        await session.commit()
        
        print(f"✅ Successfully promoted '{user.fullname}' ({user_email}) to apartment_admin")
        print(f"   User ID: {user.id}")


async def list_apartment_admins():
    """List all users with apartment_admin role."""
    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.role == UserRoles.APARTMENT_ADMIN.value)
        )
        admins = result.scalars().all()
        
        if not admins:
            print("No apartment admins found")
            return
        
        print(f"\n📋 Apartment Admins ({len(admins)}):")
        print("-" * 80)
        for admin in admins:
            print(f"• {admin.fullname} ({admin.email})")
            print(f"  ID: {admin.id}")
            print(f"  Phone: {admin.phone_number or 'N/A'}")
            print()


async def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Promote user:    python -m scripts.setup_apartment_admin <user_email>")
        print("  List admins:     python -m scripts.setup_apartment_admin --list")
        return
    
    if sys.argv[1] == "--list":
        await list_apartment_admins()
    else:
        user_email = sys.argv[1]
        await promote_to_apartment_admin(user_email)


if __name__ == "__main__":
    asyncio.run(main())
