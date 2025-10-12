"""
Test script for the new features
Run this to verify all three features are working correctly

Usage: python -m scripts.test_new_features
"""

import asyncio
from uuid import uuid4
from datetime import datetime, timedelta

from apps.api.shop.models import Shop
from apps.api.analytics.models import CallToActionEvent
from apps.api.apartment.models import Apartment, ApartmentPermittedVehicle
from apps.api.user.models import User, UserRoles
from apps.api.vehicle.models import Vehicle
from avcfastapi.core.database.sqlalchamey.core import get_session
from sqlalchemy import select


async def test_shop_management():
    """Test shop management functionality"""
    print("\n🏪 Testing Shop Management...")
    
    async with get_session() as session:
        # Create a test shop
        shop = Shop(
            name="Test Coffee Shop",
            address="123 Test Street",
            latitude=37.7749,
            longitude=-122.4194,
            phone_number="+1234567890",
            email="test@shop.com",
            category="Restaurant",
            is_active=True
        )
        session.add(shop)
        await session.commit()
        await session.refresh(shop)
        
        print(f"  ✅ Created shop: {shop.name} (ID: {shop.id})")
        
        # Retrieve the shop
        result = await session.execute(
            select(Shop).where(Shop.id == shop.id)
        )
        retrieved_shop = result.scalar_one()
        print(f"  ✅ Retrieved shop: {retrieved_shop.name}")
        
        # Update the shop
        retrieved_shop.is_active = False
        await session.commit()
        print(f"  ✅ Updated shop active status")
        
        # Clean up
        await retrieved_shop.delete(session)
        await session.commit()
        print(f"  ✅ Soft deleted shop")
        
        return True


async def test_cta_analytics():
    """Test CTA analytics functionality"""
    print("\n📊 Testing CTA Analytics...")
    
    async with get_session() as session:
        # Get a user (or use None for anonymous)
        result = await session.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        
        # Track some events
        events = []
        event_types = ["contact_shop", "view_vehicle", "call_owner"]
        
        for i, event_type in enumerate(event_types):
            event = CallToActionEvent(
                user_id=user.id if user else None,
                event_type=event_type,
                event_context="test_context",
                ip_address="127.0.0.1",
                metadata={"test": True, "index": i}
            )
            session.add(event)
            events.append(event)
        
        await session.commit()
        print(f"  ✅ Created {len(events)} CTA events")
        
        # Query events
        result = await session.execute(
            select(CallToActionEvent).where(
                CallToActionEvent.event_context == "test_context"
            )
        )
        tracked_events = result.scalars().all()
        print(f"  ✅ Retrieved {len(tracked_events)} events")
        
        # Clean up
        for event in events:
            await session.delete(event)
        await session.commit()
        print(f"  ✅ Cleaned up test events")
        
        return True


async def test_apartment_management():
    """Test apartment management functionality"""
    print("\n🏢 Testing Apartment Management...")
    
    async with get_session() as session:
        # Get or create an admin user
        result = await session.execute(
            select(User).where(User.role == UserRoles.ADMIN.value).limit(1)
        )
        admin_user = result.scalar_one_or_none()
        
        if not admin_user:
            print("  ⚠️  No admin user found, skipping apartment tests")
            return False
        
        # Create a test apartment
        apartment = Apartment(
            name="Test Towers",
            address="789 Test Avenue",
            description="Test apartment complex",
            admin_id=admin_user.id
        )
        session.add(apartment)
        await session.commit()
        await session.refresh(apartment)
        
        print(f"  ✅ Created apartment: {apartment.name} (ID: {apartment.id})")
        
        # Get a vehicle
        result = await session.execute(select(Vehicle).limit(1))
        vehicle = result.scalar_one_or_none()
        
        if vehicle:
            # Add permitted vehicle
            permitted = ApartmentPermittedVehicle(
                apartment_id=apartment.id,
                vehicle_id=vehicle.id,
                parking_spot="TEST-01",
                notes="Test vehicle"
            )
            session.add(permitted)
            await session.commit()
            await session.refresh(permitted)
            
            print(f"  ✅ Added permitted vehicle (ID: {vehicle.id})")
            
            # Check permission
            result = await session.execute(
                select(ApartmentPermittedVehicle).where(
                    ApartmentPermittedVehicle.apartment_id == apartment.id,
                    ApartmentPermittedVehicle.vehicle_id == vehicle.id
                )
            )
            permission = result.scalar_one_or_none()
            
            if permission:
                print(f"  ✅ Verified vehicle permission exists")
            
            # Clean up permission
            await permitted.delete(session)
            await session.commit()
            print(f"  ✅ Removed vehicle permission")
        else:
            print("  ⚠️  No vehicles found, skipping vehicle permission tests")
        
        # Clean up apartment
        await apartment.delete(session)
        await session.commit()
        print(f"  ✅ Deleted apartment")
        
        return True


async def test_user_roles():
    """Test user role functionality"""
    print("\n👥 Testing User Roles...")
    
    async with get_session() as session:
        # Check for users with different roles
        for role in [UserRoles.ADMIN, UserRoles.USER, UserRoles.APARTMENT_ADMIN]:
            result = await session.execute(
                select(User).where(User.role == role.value).limit(1)
            )
            user = result.scalar_one_or_none()
            
            if user:
                print(f"  ✅ Found {role.value}: {user.fullname}")
            else:
                print(f"  ⚠️  No {role.value} found")
        
        return True


async def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("🧪 Running New Features Tests")
    print("=" * 60)
    
    results = []
    
    try:
        results.append(("Shop Management", await test_shop_management()))
    except Exception as e:
        print(f"  ❌ Shop Management test failed: {e}")
        results.append(("Shop Management", False))
    
    try:
        results.append(("CTA Analytics", await test_cta_analytics()))
    except Exception as e:
        print(f"  ❌ CTA Analytics test failed: {e}")
        results.append(("CTA Analytics", False))
    
    try:
        results.append(("Apartment Management", await test_apartment_management()))
    except Exception as e:
        print(f"  ❌ Apartment Management test failed: {e}")
        results.append(("Apartment Management", False))
    
    try:
        results.append(("User Roles", await test_user_roles()))
    except Exception as e:
        print(f"  ❌ User Roles test failed: {e}")
        results.append(("User Roles", False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 Test Summary")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {test_name}: {status}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\n  Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n  🎉 All tests passed!")
    else:
        print("\n  ⚠️  Some tests failed. Please review the output above.")
    
    print("=" * 60)


async def main():
    await run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
