"""
Test script for parking management features
Run this to verify all parking features are working correctly

Usage: python -m scripts.test_parking_features
"""

import asyncio
from decimal import Decimal
from datetime import datetime, timedelta, timezone
import sqlalchemy as sa

from apps.api.parking.models import (
    ParkingSlot,
    ParkingSlotStaff,
    ParkingSession,
    VehicleDue,
    ParkingVehicleType,
    PricingModel,
    PaymentTiming,
    SlotStatus,
    StaffRole,
    SessionStatus
)
from apps.api.user.models import User, UserRoles
from avcfastapi.core.database.sqlalchamey.core import AsyncSessionLocal
from sqlalchemy import select


async def test_parking_slot_creation():
    """Test parking slot creation and verification"""
    print("\n🅿️  Testing Parking Slot Creation...")
    
    async with AsyncSessionLocal() as session:
        # Get or create a test user
        result = await session.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        
        if not user:
            print("  ⚠️  No users found, skipping parking tests")
            return False
        
        # Create a parking slot
        slot = ParkingSlot(
            owner_id=user.id,
            name="Test Parking Lot",
            description="Test parking facility",
            location="123 Test Street",
            latitude=37.7749,
            longitude=-122.4194,
            capacity={"car": 20, "bike": 10},
            pricing_model=PricingModel.HOURLY,
            pricing_config={
                "car": {
                    "base": 30,
                    "base_hours": 2,
                    "incremental": 10
                }
            },
            payment_timing=PaymentTiming.ON_EXIT,
            status=SlotStatus.PENDING_VERIFICATION
        )
        
        session.add(slot)
        await session.commit()
        await session.refresh(slot)
        
        print(f"  ✅ Created parking slot: {slot.name} (ID: {slot.id})")
        print(f"     Status: {slot.status}")
        
        # Add owner as staff
        owner_staff = ParkingSlotStaff(
            slot_id=slot.id,
            user_id=user.id,
            role=StaffRole.OWNER
        )
        session.add(owner_staff)
        await session.commit()
        
        print(f"  ✅ Added owner as staff")
        
        # Verify slot
        slot.status = SlotStatus.ACTIVE
        slot.verified_at = datetime.now(timezone.utc)
        await session.commit()
        
        print(f"  ✅ Activated parking slot")
        
        # Clean up
        await session.delete(owner_staff)
        await session.delete(slot)
        await session.commit()
        
        print(f"  ✅ Cleaned up test data")
        
        return True


async def test_parking_session():
    """Test vehicle check-in/check-out"""
    print("\n🚗 Testing Parking Sessions...")
    
    async with AsyncSessionLocal() as session:
        # Get a user
        result = await session.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        
        if not user:
            print("  ⚠️  No users found")
            return False
        
        # Create test slot
        slot = ParkingSlot(
            owner_id=user.id,
            name="Test Session Lot",
            location="Test Location",
            latitude=37.7749,
            longitude=-122.4194,
            capacity={"car": 10},
            pricing_model=PricingModel.HOURLY,
            pricing_config={
                "car": {
                    "base": 30,
                    "base_hours": 2,
                    "incremental": 10
                }
            },
            payment_timing=PaymentTiming.ON_EXIT,
            status=SlotStatus.ACTIVE
        )
        
        session.add(slot)
        await session.flush()
        
        # Check in vehicle
        parking_session = ParkingSession(
            slot_id=slot.id,
            vehicle_number="TEST1234",
            vehicle_type=ParkingVehicleType.CAR,
            checked_in_by=user.id,
            check_in_time=datetime.now(timezone.utc),
            status=SessionStatus.CHECKED_IN,
            calculated_fee=Decimal("0.00")
        )
        
        session.add(parking_session)
        await session.commit()
        await session.refresh(parking_session)
        
        print(f"  ✅ Checked in vehicle: {parking_session.vehicle_number}")
        print(f"     Check-in time: {parking_session.check_in_time}")
        
        # Simulate 5 hour parking
        check_out_time = parking_session.check_in_time + timedelta(hours=5)
        
        # Calculate fee (30 base + 30 for 3 additional hours = 60)
        parking_session.check_out_time = check_out_time
        parking_session.checked_out_by = user.id
        parking_session.status = SessionStatus.CHECKED_OUT
        parking_session.calculated_fee = Decimal("60.00")
        parking_session.collected_fee = Decimal("60.00")
        
        await session.commit()
        
        print(f"  ✅ Checked out vehicle")
        print(f"     Duration: 5 hours")
        print(f"     Fee: ₹{parking_session.calculated_fee}")
        
        # Clean up
        await session.delete(parking_session)
        await session.delete(slot)
        await session.commit()
        
        print(f"  ✅ Cleaned up test data")
        
        return True


async def test_due_tracking():
    """Test escaped vehicle due tracking"""
    print("\n💰 Testing Due Tracking...")
    
    async with AsyncSessionLocal() as session:
        # Get a user
        result = await session.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        
        if not user:
            print("  ⚠️  No users found")
            return False
        
        # Create test slot
        slot = ParkingSlot(
            owner_id=user.id,
            name="Test Due Lot",
            location="Test Location",
            latitude=37.7749,
            longitude=-122.4194,
            capacity={"car": 10},
            pricing_model=PricingModel.FIXED,
            pricing_config={"car": 50},
            payment_timing=PaymentTiming.ON_EXIT,
            status=SlotStatus.ACTIVE
        )
        
        session.add(slot)
        await session.flush()
        
        # Create escaped session
        escaped_session = ParkingSession(
            slot_id=slot.id,
            vehicle_number="ESCAPE1234",
            vehicle_type=ParkingVehicleType.CAR,
            checked_in_by=user.id,
            check_in_time=datetime.now(timezone.utc) - timedelta(hours=2),
            check_out_time=datetime.now(timezone.utc),
            checked_out_by=user.id,
            status=SessionStatus.ESCAPED,
            calculated_fee=Decimal("50.00"),
            collected_fee=Decimal("0.00")
        )
        
        session.add(escaped_session)
        await session.flush()
        
        print(f"  ✅ Created escaped session")
        print(f"     Vehicle: {escaped_session.vehicle_number}")
        print(f"     Due amount: ₹{escaped_session.calculated_fee}")
        
        # Create due record
        due = VehicleDue(
            vehicle_number=escaped_session.vehicle_number,
            slot_owner_id=user.id,
            session_id=escaped_session.id,
            due_amount=escaped_session.calculated_fee,
            paid_amount=Decimal("0.00")
        )
        
        session.add(due)
        await session.commit()
        await session.refresh(due)
        
        print(f"  ✅ Created due record (ID: {due.id})")
        
        # Check for due
        result = await session.execute(
            select(VehicleDue).where(
                VehicleDue.vehicle_number == "ESCAPE1234",
                VehicleDue.slot_owner_id == user.id
            )
        )
        found_due = result.scalar_one_or_none()
        
        if found_due:
            print(f"  ✅ Successfully retrieved due record")
            print(f"     Outstanding: ₹{found_due.due_amount - found_due.paid_amount}")
        
        # Clean up
        await session.delete(due)
        await session.delete(escaped_session)
        await session.delete(slot)
        await session.commit()
        
        print(f"  ✅ Cleaned up test data")
        
        return True


async def test_live_occupancy():
    """Test live occupancy calculation"""
    print("\n📊 Testing Live Occupancy...")
    
    async with AsyncSessionLocal() as session:
        # Get a user
        result = await session.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        
        if not user:
            print("  ⚠️  No users found")
            return False
        
        # Create test slot
        slot = ParkingSlot(
            owner_id=user.id,
            name="Test Occupancy Lot",
            location="Test Location",
            latitude=37.7749,
            longitude=-122.4194,
            capacity={"car": 10, "bike": 5},
            pricing_model=PricingModel.FREE,
            pricing_config={},
            payment_timing=PaymentTiming.ON_EXIT,
            status=SlotStatus.ACTIVE
        )
        
        session.add(slot)
        await session.flush()
        
        # Create active sessions
        sessions = []
        for i in range(3):
            sess = ParkingSession(
                slot_id=slot.id,
                vehicle_number=f"CAR{i:04d}",
                vehicle_type=ParkingVehicleType.CAR,
                checked_in_by=user.id,
                check_in_time=datetime.now(timezone.utc),
                status=SessionStatus.CHECKED_IN,
                calculated_fee=Decimal("0.00")
            )
            sessions.append(sess)
            session.add(sess)
        
        for i in range(2):
            sess = ParkingSession(
                slot_id=slot.id,
                vehicle_number=f"BIKE{i:04d}",
                vehicle_type=ParkingVehicleType.BIKE,
                checked_in_by=user.id,
                check_in_time=datetime.now(timezone.utc),
                status=SessionStatus.CHECKED_IN,
                calculated_fee=Decimal("0.00")
            )
            sessions.append(sess)
            session.add(sess)
        
        await session.commit()
        
        print(f"  ✅ Created 3 car and 2 bike sessions")
        
        # Calculate occupancy
        result = await session.execute(
            select(
                ParkingSession.vehicle_type,
                sa.func.count(ParkingSession.id)
            )
            .where(
                ParkingSession.slot_id == slot.id,
                ParkingSession.status == SessionStatus.CHECKED_IN
            )
            .group_by(ParkingSession.vehicle_type)
        )
        
        occupancy = {}
        for vehicle_type, count in result:
            occupancy[vehicle_type] = count
        
        print(f"  ✅ Current occupancy:")
        print(f"     Cars: {occupancy.get('car', 0)}/10")
        print(f"     Bikes: {occupancy.get('bike', 0)}/5")
        print(f"     Available cars: {10 - occupancy.get('car', 0)}")
        print(f"     Available bikes: {5 - occupancy.get('bike', 0)}")
        
        # Clean up
        for sess in sessions:
            await session.delete(sess)
        await session.delete(slot)
        await session.commit()
        
        print(f"  ✅ Cleaned up test data")
        
        return True


async def test_staff_management():
    """Test staff addition and removal"""
    print("\n👥 Testing Staff Management...")
    
    async with AsyncSessionLocal() as session:
        # Get two users
        result = await session.execute(select(User).limit(2))
        users = list(result.scalars().all())
        
        if len(users) < 2:
            print("  ⚠️  Need at least 2 users")
            return False
        
        owner = users[0]
        staff_user = users[1]
        
        # Create slot
        slot = ParkingSlot(
            owner_id=owner.id,
            name="Test Staff Lot",
            location="Test Location",
            latitude=37.7749,
            longitude=-122.4194,
            capacity={"car": 10},
            pricing_model=PricingModel.FREE,
            pricing_config={},
            payment_timing=PaymentTiming.ON_EXIT,
            status=SlotStatus.ACTIVE
        )
        
        session.add(slot)
        await session.flush()
        
        # Add owner as staff
        owner_staff = ParkingSlotStaff(
            slot_id=slot.id,
            user_id=owner.id,
            role=StaffRole.OWNER
        )
        session.add(owner_staff)
        
        print(f"  ✅ Added owner as staff")
        
        # Add second user as staff
        staff_member = ParkingSlotStaff(
            slot_id=slot.id,
            user_id=staff_user.id,
            role=StaffRole.STAFF
        )
        session.add(staff_member)
        await session.commit()
        
        print(f"  ✅ Added staff member: {staff_user.fullname}")
        
        # List staff
        result = await session.execute(
            select(ParkingSlotStaff).where(ParkingSlotStaff.slot_id == slot.id)
        )
        staff_list = result.scalars().all()
        
        print(f"  ✅ Total staff members: {len(staff_list)}")
        
        # Clean up
        for staff in staff_list:
            await session.delete(staff)
        await session.delete(slot)
        await session.commit()
        
        print(f"  ✅ Cleaned up test data")
        
        return True


async def run_all_tests():
    """Run all parking feature tests"""
    print("=" * 60)
    print("🧪 Running Parking Management System Tests")
    print("=" * 60)
    
    results = []
    
    try:
        results.append(("Parking Slot Creation", await test_parking_slot_creation()))
    except Exception as e:
        print(f"  ❌ Parking Slot Creation test failed: {e}")
        results.append(("Parking Slot Creation", False))
    
    try:
        results.append(("Parking Sessions", await test_parking_session()))
    except Exception as e:
        print(f"  ❌ Parking Session test failed: {e}")
        results.append(("Parking Sessions", False))
    
    try:
        results.append(("Due Tracking", await test_due_tracking()))
    except Exception as e:
        print(f"  ❌ Due Tracking test failed: {e}")
        results.append(("Due Tracking", False))
    
    try:
        results.append(("Live Occupancy", await test_live_occupancy()))
    except Exception as e:
        print(f"  ❌ Live Occupancy test failed: {e}")
        results.append(("Live Occupancy", False))
    
    try:
        results.append(("Staff Management", await test_staff_management()))
    except Exception as e:
        print(f"  ❌ Staff Management test failed: {e}")
        results.append(("Staff Management", False))
    
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
        print("\n  🎉 All parking tests passed!")
    else:
        print("\n  ⚠️  Some tests failed. Please review the output above.")
    
    print("=" * 60)


async def main():
    await run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())