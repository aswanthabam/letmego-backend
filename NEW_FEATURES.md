# New Features Documentation

This document describes the three new features added to the LetMeGo backend application.

## Table of Contents
1. [Shop Management](#1-shop-management)
2. [Call-to-Action Analytics](#2-call-to-action-analytics)
3. [Apartment Management](#3-apartment-management)

---

## 1. Shop Management

### Overview
CRUD APIs for managing shops with location data. Only admins can create, update, and delete shops.

### Endpoints

#### POST `/api/shop/create`
Create a new shop (Admin only)

**Request Body:**
```json
{
  "name": "Coffee Shop",
  "description": "Best coffee in town",
  "address": "123 Main St, City",
  "latitude": 37.7749,
  "longitude": -122.4194,
  "phone_number": "+1234567890",
  "email": "contact@coffeeshop.com",
  "website": "https://coffeeshop.com",
  "category": "Restaurant",
  "operating_hours": "Mon-Fri: 8AM-8PM",
  "is_active": true
}
```

**Response:** `ShopResponse` (201 Created)

#### GET `/api/shop/list`
Get paginated list of shops

**Query Parameters:**
- `page` (int, optional): Page number (default: 1)
- `limit` (int, optional): Items per page (default: 10)
- `category` (string, optional): Filter by category
- `is_active` (boolean, optional): Filter by active status

**Response:** `PaginatedResponse<ShopResponse>`

#### GET `/api/shop/{shop_id}`
Get shop details by ID

**Response:** `ShopResponse`

#### PUT `/api/shop/{shop_id}`
Update shop details (Admin only)

**Request Body:** `ShopUpdate` (all fields optional)

**Response:** `ShopResponse`

#### DELETE `/api/shop/{shop_id}`
Delete a shop (Admin only)

**Response:** `MessageResponse`

---

## 2. Call-to-Action Analytics

### Overview
Track user interactions with call-to-action buttons and provide analytics for admins.

### Endpoints

#### POST `/api/analytics/cta/track`
Track a CTA event (Authenticated or Anonymous)

**Request Body:**
```json
{
  "event_type": "contact_shop",
  "event_context": "from_shop_detail_page",
  "related_entity_id": "550e8400-e29b-41d4-a716-446655440000",
  "related_entity_type": "shop",
  "metadata": {
    "button_position": "top",
    "device_type": "mobile"
  }
}
```

**Response:** `CTAEventResponse`

**Event Types (Examples):**
- `contact_shop` - User clicked contact button on shop
- `view_vehicle` - User viewed vehicle details
- `report_issue` - User reported an issue
- `call_owner` - User initiated call to vehicle owner
- Custom event types as needed

#### GET `/api/analytics/cta/summary`
Get CTA analytics summary (Admin only)

**Query Parameters:**
- `start_date` (datetime, optional): Filter from this date (ISO format)
- `end_date` (datetime, optional): Filter until this date (ISO format)
- `event_type` (string, optional): Filter by event type
- `related_entity_type` (string, optional): Filter by entity type

**Response:**
```json
{
  "total_events": 1500,
  "analytics_by_type": [
    {
      "event_type": "contact_shop",
      "count": 450,
      "unique_users": 320
    },
    {
      "event_type": "view_vehicle",
      "count": 1050,
      "unique_users": 780
    }
  ],
  "date_range": {
    "start_date": "2024-01-01T00:00:00",
    "end_date": "2024-12-31T23:59:59"
  }
}
```

#### GET `/api/analytics/cta/events`
Get detailed CTA events (Admin only)

**Query Parameters:**
- `page` (int, optional): Page number
- `limit` (int, optional): Items per page
- `start_date` (datetime, optional): Filter from this date
- `end_date` (datetime, optional): Filter until this date
- `event_type` (string, optional): Filter by event type

**Response:** `PaginatedResponse<CTAEventResponse>`

---

## 3. Apartment Management

### Overview
System for apartment admins to manage their apartments and control vehicle parking permissions.

### User Roles
- **Super Admin (`admin`)**: Can create apartments, assign apartment admins
- **Apartment Admin (`apartment_admin`)**: Can manage vehicles in their assigned apartments

### Endpoints

#### POST `/api/apartment/create`
Create a new apartment (Super Admin only)

**Request Body:**
```json
{
  "name": "Sunrise Apartments",
  "address": "456 Oak Avenue, City",
  "description": "Luxury apartment complex with 200 units",
  "admin_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response:** `ApartmentResponse`

#### GET `/api/apartment/list`
Get all apartments (Super Admin only)

**Query Parameters:**
- `page` (int): Page number
- `limit` (int): Items per page

**Response:** `PaginatedResponse<ApartmentResponse>`

#### GET `/api/apartment/my-apartments`
Get apartments managed by current admin (Apartment Admin)

**Response:** `List<ApartmentResponse>`

#### GET `/api/apartment/{apartment_id}`
Get apartment details

**Response:** `ApartmentResponse`

#### PUT `/api/apartment/{apartment_id}`
Update apartment details (Super Admin only)

**Request Body:** `ApartmentUpdate`

**Response:** `ApartmentResponse`

#### DELETE `/api/apartment/{apartment_id}`
Delete apartment (Super Admin only)

**Response:** `MessageResponse`

---

### Permitted Vehicle Management

#### POST `/api/apartment/{apartment_id}/vehicles/add`
Add vehicle to permitted parking list (Apartment Admin)

**Request Body:**
```json
{
  "vehicle_id": "550e8400-e29b-41d4-a716-446655440000",
  "notes": "Owner: John Doe, Unit 204",
  "parking_spot": "A-15"
}
```

**Response:** `PermittedVehicleResponse`

#### DELETE `/api/apartment/{apartment_id}/vehicles/{vehicle_id}`
Remove vehicle from permitted parking list (Apartment Admin)

**Response:** `MessageResponse`

#### GET `/api/apartment/{apartment_id}/vehicles/check/{vehicle_id}`
Check if a vehicle is permitted (Apartment Admin)

**Response:**
```json
{
  "is_permitted": true,
  "apartment_id": "550e8400-e29b-41d4-a716-446655440000",
  "apartment_name": "Sunrise Apartments",
  "parking_spot": "A-15",
  "notes": "Owner: John Doe, Unit 204"
}
```

#### GET `/api/apartment/{apartment_id}/vehicles/list`
Get all permitted vehicles for an apartment (Apartment Admin)

**Query Parameters:**
- `page` (int): Page number
- `limit` (int): Items per page

**Response:** `PaginatedResponse<PermittedVehicleResponse>`

---

## Database Migrations

After implementing these features, run the database migration:

```bash
# Run migrations
alembic upgrade head
```

The migration file `add_new_features_2024.py` creates the following tables:
- `shops` - Shop information with location data
- `cta_events` - Call-to-action event tracking
- `apartments` - Apartment complex information
- `apartment_permitted_vehicles` - Vehicle parking permissions

---

## Authentication & Authorization

### Required Headers
All authenticated endpoints require:
```
Authorization: Bearer <firebase_token>
```

### Role-Based Access Control

| Feature | Endpoint Type | Required Role |
|---------|--------------|---------------|
| Shop Management (Create/Update/Delete) | Admin | `admin` |
| Shop Management (View) | Public | Any |
| CTA Tracking | Public | Any (optional auth) |
| CTA Analytics | Admin | `admin` |
| Apartment CRUD | Super Admin | `admin` |
| Apartment Vehicle Management | Apartment Admin | `apartment_admin` or `admin` |

---

## Usage Examples

### Example 1: Admin Creates a Shop
```bash
curl -X POST "http://localhost:8000/api/shop/create" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Tech Repair Shop",
    "latitude": 37.7749,
    "longitude": -122.4194,
    "category": "Service",
    "is_active": true
  }'
```

### Example 2: Track User CTA Event
```bash
curl -X POST "http://localhost:8000/api/analytics/cta/track" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "contact_shop",
    "related_entity_id": "<shop_id>",
    "related_entity_type": "shop"
  }'
```

### Example 3: Admin Views CTA Analytics
```bash
curl -X GET "http://localhost:8000/api/analytics/cta/summary?start_date=2024-01-01T00:00:00&end_date=2024-12-31T23:59:59" \
  -H "Authorization: Bearer <admin_token>"
```

### Example 4: Apartment Admin Adds Permitted Vehicle
```bash
curl -X POST "http://localhost:8000/api/apartment/<apartment_id>/vehicles/add" \
  -H "Authorization: Bearer <apartment_admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "vehicle_id": "<vehicle_id>",
    "parking_spot": "B-22",
    "notes": "Resident: Jane Smith, Unit 305"
  }'
```

### Example 5: Check Vehicle Permission
```bash
curl -X GET "http://localhost:8000/api/apartment/<apartment_id>/vehicles/check/<vehicle_id>" \
  -H "Authorization: Bearer <apartment_admin_token>"
```

---

## Error Codes

| Error Code | Description |
|------------|-------------|
| `SHOP_NOT_FOUND` | Shop with given ID not found |
| `APARTMENT_NOT_FOUND` | Apartment with given ID not found |
| `NOT_APARTMENT_ADMIN` | User is not authorized as apartment admin |
| `VEHICLE_ALREADY_PERMITTED` | Vehicle already in permitted list |
| `PERMISSION_NOT_FOUND` | Vehicle permission record not found |
| `VEHICLE_NOT_FOUND` | Vehicle with given ID not found |

---

## Notes

1. **Soft Deletes**: All models use soft delete (records are marked as deleted, not removed from database)
2. **Pagination**: Default limit is 10, max is 100
3. **Time Zones**: All datetime values are in UTC
4. **Anonymous Tracking**: CTA events can be tracked without authentication for analytics
5. **IP Tracking**: CTA events automatically capture IP address and user agent for analytics
