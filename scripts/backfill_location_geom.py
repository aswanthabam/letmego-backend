"""
Backfill script: Populate location_geom from existing latitude/longitude columns.
Also adds composite indexes for analytics performance.

Run inside the Docker container:
    python scripts/backfill_location_geom.py
"""
import asyncio
from sqlalchemy import text
from avcfastapi.core.database.sqlalchamey.core import AsyncSessionLocal


async def run_backfill():
    print("🚀 Starting location_geom backfill and index creation...")
    
    async with AsyncSessionLocal() as session:
        # 1. Backfill location_geom from lat/lng
        result = await session.execute(text(
            """
            UPDATE parking_slots 
            SET location_geom = ST_GeogFromText(
                'SRID=4326;POINT(' || longitude || ' ' || latitude || ')'
            )
            WHERE latitude IS NOT NULL 
              AND longitude IS NOT NULL 
              AND location_geom IS NULL;
            """
        ))
        print(f"✅ Backfilled location_geom for {result.rowcount} parking slots")
        
        # 2. Create composite indexes for analytics performance
        indexes = [
            (
                "idx_sessions_analytics",
                "CREATE INDEX IF NOT EXISTS idx_sessions_analytics "
                "ON parking_sessions (slot_id, status, check_in_time);"
            ),
            (
                "idx_sessions_vehicle_status",
                "CREATE INDEX IF NOT EXISTS idx_sessions_vehicle_status "
                "ON parking_sessions (vehicle_number, status);"
            ),
            (
                "idx_sessions_checkout_time",
                "CREATE INDEX IF NOT EXISTS idx_sessions_checkout_time "
                "ON parking_sessions (check_out_time) WHERE status = 'checked_out';"
            ),
            (
                "idx_dues_status",
                "CREATE INDEX IF NOT EXISTS idx_dues_status "
                "ON vehicle_dues (status, vehicle_number) WHERE status = 'pending';"
            ),
            (
                "idx_org_members_lookup",
                "CREATE INDEX IF NOT EXISTS idx_org_members_lookup "
                "ON organization_members (organization_id, user_id, role) "
                "WHERE deleted_at IS NULL;"
            ),
        ]
        
        for idx_name, idx_sql in indexes:
            try:
                await session.execute(text(idx_sql))
                print(f"✅ Created index: {idx_name}")
            except Exception as e:
                print(f"⚠️  Index {idx_name} skipped: {e}")
        
        # 3. Fix collation version mismatch
        try:
            await session.execute(text(
                "ALTER DATABASE letmego REFRESH COLLATION VERSION;"
            ))
            print("✅ Refreshed database collation version")
        except Exception as e:
            print(f"⚠️  Collation refresh skipped: {e}")
        
        await session.commit()
        print("\n✅ All backfill operations completed successfully!")


if __name__ == "__main__":
    # Bootstrap the app so models and DB engine are loaded
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import app as _  # noqa: F401 - triggers app bootstrapping
    
    asyncio.run(run_backfill())
