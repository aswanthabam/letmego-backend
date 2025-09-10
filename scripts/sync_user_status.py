# apps/management/commands/sync_user_status.py
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from apps.api.user.models import User, UserStatus
from avcfastapi.core.utils.commands.command import Command
from avcfastapi.core.database.sqlalchamey.core import AsyncSessionLocal


class SyncUserStatusCommand(Command):
    help = "Synchronize user status based on profile and vehicle information"

    def add_arguments(self, parser):
        # Optional: you can add arguments like --limit
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Limit the number of users to process (0 = all)",
        )

    async def handle(self, **options):
        limit = options.get("limit", 0)

        async with AsyncSessionLocal() as session:
            stmt = select(User).options(joinedload(User.vehicles))
            if limit > 0:
                stmt = stmt.limit(limit)

            result = await session.execute(stmt)
            users = result.unique().scalars().all()

            for user in users:
                original_status = user.status
                if (
                    user.fullname
                    and user.fullname.lower() != "unknown user"
                    and user.email
                    and user.phone_number
                ):
                    user.status = UserStatus.PROFILE_COMPLETED.value
                    if user.vehicles and len(user.vehicles) > 0:
                        user.status = UserStatus.VEHICLE_ADDED.value
                else:
                    user.status = UserStatus.REGISTERED.value

                session.add(user)  # mark as dirty
                print(
                    f"Updated user {user.email} | {user.phone_number} | {user.fullname} ({user.id}) from status {original_status} to {user.status}"
                )

            await session.commit()
            print("User status synchronization completed.")
