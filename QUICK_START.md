# Quick Start Guide - New Features

This guide will help you quickly get started with the three new features.

## Prerequisites
- Backend server running
- Admin user account
- Database migrated

## Step-by-Step Setup

### 1️⃣ Run Database Migration

```powershell
# Navigate to project directory
cd d:\Personal\Projects\letmego-backend

# Run the migration
alembic upgrade head
```

**Expected Output**: Migration `add_new_features_2024` should execute successfully.

---

### 2️⃣ Create Your First Shop

```powershell
# Example using curl (or use Postman)
curl -X POST "http://localhost:8000/api/shop/create" `
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" `
  -H "Content-Type: application/json" `
  -d '{
    "name": "Main Street Café",
    "address": "123 Main Street",
    "latitude": 37.7749,
    "longitude": -122.4194,
    "phone_number": "+1234567890",
    "email": "contact@cafe.com",
    "category": "Restaurant",
    "is_active": true
  }'
```

---

### 3️⃣ Track a CTA Event

```powershell
# This works even without authentication
curl -X POST "http://localhost:8000/api/analytics/cta/track" `
  -H "Content-Type: application/json" `
  -d '{
    "event_type": "contact_shop",
    "event_context": "from_home_page",
    "related_entity_id": "YOUR_SHOP_ID",
    "related_entity_type": "shop"
  }'
```

---

### 4️⃣ Setup Apartment Admin

```powershell
# Promote a user to apartment admin role
python -m scripts.setup_apartment_admin user@example.com
```

---

### 5️⃣ Create an Apartment

```powershell
# Using super admin account
curl -X POST "http://localhost:8000/api/apartment/create" `
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" `
  -H "Content-Type: application/json" `
  -d '{
    "name": "Sunset Towers",
    "address": "456 Oak Avenue",
    "description": "200-unit residential complex",
    "admin_id": "APARTMENT_ADMIN_USER_ID"
  }'
```

---

### 6️⃣ Add Permitted Vehicle

```powershell
# Using apartment admin account
curl -X POST "http://localhost:8000/api/apartment/APARTMENT_ID/vehicles/add" `
  -H "Authorization: Bearer APARTMENT_ADMIN_TOKEN" `
  -H "Content-Type: application/json" `
  -d '{
    "vehicle_id": "VEHICLE_ID",
    "parking_spot": "A-15",
    "notes": "Owner: John Doe, Unit 204"
  }'
```

---

### 7️⃣ View Analytics

```powershell
# View CTA analytics summary (admin only)
curl -X GET "http://localhost:8000/api/analytics/cta/summary?start_date=2024-01-01T00:00:00" `
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

## Testing with Swagger UI

1. Start your server: `uvicorn app:app --reload`
2. Open browser: `http://localhost:8000/docs`
3. Look for the new tag sections:
   - 📂 **Shop Management**
   - 📂 **Analytics**
   - 📂 **Apartment Management**

---

## Common Commands

### List All Shops
```bash
GET /api/shop/list?page=1&limit=10
```

### Check Vehicle Permission
```bash
GET /api/apartment/{apartment_id}/vehicles/check/{vehicle_id}
# Headers: Authorization: Bearer APARTMENT_ADMIN_TOKEN
```

### View Detailed CTA Events
```bash
GET /api/analytics/cta/events?page=1&limit=20&event_type=contact_shop
# Headers: Authorization: Bearer ADMIN_TOKEN
```

### Get My Managed Apartments
```bash
GET /api/apartment/my-apartments
# Headers: Authorization: Bearer APARTMENT_ADMIN_TOKEN
```

---

## Troubleshooting

### Issue: Migration fails
**Solution**: Check if previous migrations are applied
```powershell
alembic current
alembic history
```

### Issue: User not authorized
**Solution**: Check user role
```powershell
python -m scripts.setup_apartment_admin --list
```

### Issue: Vehicle already permitted error
**Solution**: Check existing permissions
```bash
GET /api/apartment/{apartment_id}/vehicles/list
```

### Issue: Shop not found
**Solution**: Verify shop exists
```bash
GET /api/shop/list
```

---

## Environment Variables

No new environment variables required! The new features use existing configuration.

---

## API Documentation

- **Full Documentation**: See `NEW_FEATURES.md`
- **Implementation Details**: See `IMPLEMENTATION_SUMMARY.md`
- **Interactive API Docs**: `http://localhost:8000/docs`
- **Alternative Docs**: `http://localhost:8000/redoc`

---

## Next Steps

1. ✅ Test each endpoint using Swagger UI or Postman
2. ✅ Create sample data for shops and apartments
3. ✅ Track some CTA events and view analytics
4. ✅ Promote users to apartment admin role
5. ✅ Set up permitted vehicles for apartments
6. ✅ Monitor CTA analytics over time

---

## Quick Reference Card

| Task | Endpoint | Auth Required |
|------|----------|---------------|
| Create shop | `POST /api/shop/create` | Admin |
| List shops | `GET /api/shop/list` | None |
| Track CTA | `POST /api/analytics/cta/track` | Optional |
| View analytics | `GET /api/analytics/cta/summary` | Admin |
| Create apartment | `POST /api/apartment/create` | Super Admin |
| Add vehicle | `POST /api/apartment/{id}/vehicles/add` | Apt Admin |
| Check permission | `GET /api/apartment/{id}/vehicles/check/{vid}` | Apt Admin |

---

**Ready to go! 🚀**
