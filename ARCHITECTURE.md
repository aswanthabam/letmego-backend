# Architecture Overview - New Features

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Application                      │
│                          (app.py)                                │
└─────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────┴──────────────┐
                    │      API Router Layer      │
                    │    (apps/api/router.py)    │
                    └────────────┬───────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
┌───────▼────────┐    ┌─────────▼────────┐    ┌─────────▼────────┐
│  Shop Module   │    │ Analytics Module │    │ Apartment Module │
│  (NEW! 🆕)     │    │  (NEW! 🆕)       │    │   (NEW! 🆕)      │
└────────────────┘    └──────────────────┘    └──────────────────┘
        │                        │                        │
        │                        │                        │
   ┌────▼────┐             ┌────▼────┐             ┌────▼────┐
   │ Router  │             │ Router  │             │ Router  │
   ├─────────┤             ├─────────┤             ├─────────┤
   │ Service │             │ Service │             │ Service │
   ├─────────┤             ├─────────┤             ├─────────┤
   │ Schema  │             │ Schema  │             │ Schema  │
   ├─────────┤             ├─────────┤             ├─────────┤
   │ Models  │             │ Models  │             │ Models  │
   └────┬────┘             └────┬────┘             └────┬────┘
        │                        │                        │
        └────────────────────────┼────────────────────────┘
                                 │
                    ┌────────────▼───────────────┐
                    │    PostgreSQL Database     │
                    │                            │
                    │  Tables:                   │
                    │  • shops                   │
                    │  • cta_events              │
                    │  • apartments              │
                    │  • apartment_permitted_    │
                    │    vehicles                │
                    └────────────────────────────┘
```

---

## Feature Interaction Flow

### 1. Shop Management Flow
```
User (Admin) → Firebase Auth → Shop Router → Shop Service → Database
     ↓                              ↓              ↓
  Returns ←──────────────────── Validation ← shops table
```

### 2. CTA Analytics Flow
```
User (Any) → Optional Auth → Analytics Router → Analytics Service → Database
     │              │               │                  │
     └──IP/Agent────┘               └────────────→ cta_events table
                                                        ↓
Admin → Firebase Auth → Analytics Router ──→ Aggregated Statistics
```

### 3. Apartment Management Flow
```
Super Admin → Create Apartment → apartments table
                    ↓
            Assign apartment_admin role to User
                    ↓
Apartment Admin → Manage Vehicles → apartment_permitted_vehicles table
                                              ↓
                                    Check Permissions
```

---

## Data Relationships

```
┌──────────┐
│  Users   │
└────┬─────┘
     │
     │ admin_id
     ├─────────────────┐
     │                 │
     │ user_id         │
     ▼                 ▼
┌──────────┐    ┌─────────────┐
│cta_events│    │ apartments  │
└──────────┘    └──────┬──────┘
                       │
                       │ apartment_id
                       ▼
            ┌────────────────────────┐
            │apartment_permitted_    │
            │vehicles                │
            └──────┬─────────────────┘
                   │ vehicle_id
                   ▼
            ┌──────────┐
            │ vehicles │
            └──────────┘

┌──────────┐
│  shops   │ (Independent table)
└──────────┘
```

---

## User Role Hierarchy

```
┌─────────────────────────────────────┐
│           Super Admin               │
│         (role: "admin")             │
│                                     │
│  Can:                               │
│  • Manage all shops                 │
│  • View all analytics               │
│  • Create/manage all apartments     │
│  • Access all features              │
└──────────────┬──────────────────────┘
               │
               ├──────────────────────┐
               ▼                      ▼
┌──────────────────────┐   ┌─────────────────────┐
│  Apartment Admin     │   │    Regular User     │
│(role:"apartment_admin)│   │  (role: "user")     │
│                      │   │                     │
│  Can:                │   │  Can:               │
│  • Manage own        │   │  • View shops       │
│    apartments        │   │  • Track CTA        │
│  • Add/remove        │   │  • Use vehicles     │
│    permitted vehicles│   │                     │
│  • Check permissions │   │                     │
└──────────────────────┘   └─────────────────────┘
```

---

## Request/Response Flow

### Example: Adding Permitted Vehicle

```
1. Request
   ┌────────────────────────────────────────────────┐
   │ POST /api/apartment/{id}/vehicles/add          │
   │ Headers:                                       │
   │   Authorization: Bearer <apartment_admin_token>│
   │ Body:                                          │
   │   {                                            │
   │     "vehicle_id": "...",                       │
   │     "parking_spot": "A-15"                     │
   │   }                                            │
   └────────────────────────────────────────────────┘
                       ↓
2. Authentication
   ┌────────────────────────────────────────────────┐
   │ Firebase Auth validates token                  │
   │ → Get user from database                       │
   │ → Check role (apartment_admin or admin)        │
   └────────────────────────────────────────────────┘
                       ↓
3. Authorization
   ┌────────────────────────────────────────────────┐
   │ Verify user is admin of this apartment         │
   │ → Check apartment.admin_id == user.id          │
   └────────────────────────────────────────────────┘
                       ↓
4. Validation
   ┌────────────────────────────────────────────────┐
   │ Pydantic validates request body                │
   │ → Check vehicle exists                         │
   │ → Check not already permitted                  │
   └────────────────────────────────────────────────┘
                       ↓
5. Database Operation
   ┌────────────────────────────────────────────────┐
   │ Insert into apartment_permitted_vehicles       │
   │ → apartment_id, vehicle_id, parking_spot       │
   └────────────────────────────────────────────────┘
                       ↓
6. Response
   ┌────────────────────────────────────────────────┐
   │ {                                              │
   │   "id": "...",                                 │
   │   "apartment_id": "...",                       │
   │   "vehicle_id": "...",                         │
   │   "parking_spot": "A-15",                      │
   │   "created_at": "2024-10-11T..."               │
   │ }                                              │
   └────────────────────────────────────────────────┘
```

---

## Module Dependencies

```
Shop Module
├── Dependencies: User (for admin check)
└── External: None

Analytics Module
├── Dependencies: User (optional, for tracking)
└── External: Request (for IP/user-agent)

Apartment Module
├── Dependencies: 
│   ├── User (for admin check)
│   └── Vehicle (for permission checks)
└── External: None
```

---

## Error Handling Flow

```
Request → Router → Service → Database
   ↓         ↓         ↓         ↓
   └─────────┴─────────┴─────────┘
                  ↓
        Exception Caught?
                  ↓
            ┌─────┴─────┐
            │ YES  │ NO │
            ↓           ↓
    Custom Error    Success
    Response        Response
         ↓               ↓
    {               {
      "message": "...",  "id": "...",
      "error_code": "..."  ...
    }               }
```

---

## Scalability Considerations

### Database Indexes Created
```sql
-- Analytics
CREATE INDEX ix_cta_events_event_type ON cta_events(event_type);
CREATE INDEX ix_cta_events_user_id ON cta_events(user_id);

-- Apartments
CREATE INDEX ix_apartments_admin_id ON apartments(admin_id);
CREATE INDEX ix_apartment_permitted_vehicles_apartment_id 
  ON apartment_permitted_vehicles(apartment_id);
CREATE INDEX ix_apartment_permitted_vehicles_vehicle_id 
  ON apartment_permitted_vehicles(vehicle_id);
```

### Performance Features
- ✅ Pagination on all list endpoints
- ✅ Selective field loading (SQLAlchemy)
- ✅ Indexed foreign keys
- ✅ Optimized queries with joins
- ✅ Connection pooling (built-in)

---

## Security Layers

```
┌──────────────────────────────────────────┐
│         1. Network Layer (HTTPS)         │
└──────────────────┬───────────────────────┘
                   ↓
┌──────────────────────────────────────────┐
│    2. Authentication (Firebase Token)    │
└──────────────────┬───────────────────────┘
                   ↓
┌──────────────────────────────────────────┐
│  3. Authorization (Role-Based Access)    │
└──────────────────┬───────────────────────┘
                   ↓
┌──────────────────────────────────────────┐
│    4. Validation (Pydantic Schemas)      │
└──────────────────┬───────────────────────┘
                   ↓
┌──────────────────────────────────────────┐
│  5. Database (SQL Injection Protection)  │
└──────────────────────────────────────────┘
```

---

## Monitoring & Analytics

### Tracked Metrics (via CTA Events)
- User interactions by type
- Unique users per event type
- Time-based trends
- Anonymous vs authenticated usage
- IP-based geolocation (if added)
- User agent analysis (device types)

### Admin Dashboard Data
```
GET /api/analytics/cta/summary
↓
Returns:
- Total event count
- Breakdown by event type
- Unique user counts
- Date range statistics
```

---

## Development Workflow

```
1. Code Changes
   ├── Modify models.py
   ├── Update schema.py
   ├── Implement service.py
   └── Create router.py

2. Database Migration
   └── alembic upgrade head

3. Testing
   ├── Manual: Swagger UI
   └── Automated: test_new_features.py

4. Deployment
   ├── Push to repository
   ├── CI/CD pipeline
   └── Production deploy
```

---

This architecture ensures:
- 🔒 **Security**: Multiple authentication/authorization layers
- 📈 **Scalability**: Indexed queries, pagination, efficient joins
- 🧩 **Modularity**: Clear separation of concerns
- 🛠️ **Maintainability**: Consistent patterns across all modules
- 🚀 **Performance**: Optimized database operations
- 📊 **Observability**: Built-in analytics and tracking
