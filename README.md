# Art of Yoga Backend

A Django REST Framework backend for the Art of Yoga application, providing APIs for managing yoga routines, exercises, and user relationships.

## Setup

1. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up environment variables:

```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Run migrations:

```bash
python manage.py migrate
```

5. Create a superuser:

```bash
python manage.py createsuperuser
```

6. Run the development server:

```bash
python manage.py runserver
```

## API Endpoints

### Authentication

- `GET /api/auth-test/` - Test endpoint for authentication

### User Profiles (`/api/users/`)

- `GET /api/users/profiles/` - List user profiles (filtered by role)
- `GET /api/users/profiles/{id}/` - Get specific user profile
- `PUT /api/users/profiles/{id}/` - Update user profile
- `GET /api/users/profiles/me/` - Get current user's profile
- `POST /api/users/profiles/{id}/update_role/` - Update user role (instructor only)

### Routines (`/api/routines/`)

- `GET /api/routines/routines/` - List routines (filtered by role)
- `POST /api/routines/routines/` - Create new routine (instructor only)
- `GET /api/routines/routines/{id}/` - Get specific routine
- `PUT /api/routines/routines/{id}/` - Update routine (instructor only)
- `DELETE /api/routines/routines/{id}/` - Delete routine (instructor only)

### Exercises (`/api/routines/`)

- `GET /api/routines/exercises/` - List exercises (filtered by role)
- `POST /api/routines/exercises/` - Create new exercise
- `GET /api/routines/exercises/{id}/` - Get specific exercise
- `PUT /api/routines/exercises/{id}/` - Update exercise
- `DELETE /api/routines/exercises/{id}/` - Delete exercise

### Client-Instructor Relationships (`/api/routines/`)

- `GET /api/routines/relationships/` - List relationships
- `POST /api/routines/relationships/` - Create new relationship
- `GET /api/routines/relationships/{id}/` - Get specific relationship
- `PUT /api/routines/relationships/{id}/` - Update relationship
- `DELETE /api/routines/relationships/{id}/` - Delete relationship
- `POST /api/routines/relationships/{id}/assign_routine/` - Assign routine to relationship
- `POST /api/routines/relationships/{id}/remove_routine/` - Remove routine from relationship

## Models

### UserProfile

- Represents a user in the system (instructor or client)
- Contains user information and role

### Routine

- Represents a yoga routine created by an instructor
- Contains exercises and can be assigned to clients

### Exercise

- Represents a yoga exercise
- Can be part of multiple routines
- Contains exercise details and instructions

### ClientInstructorRelationship

- Manages the relationship between clients and instructors
- Handles routine assignments

## Authentication

The API uses Supabase JWT authentication. All endpoints (except public ones) require a valid JWT token in the Authorization header.

## Development

### Running Tests

```bash
python manage.py test
```

### Code Style

The project follows PEP 8 guidelines. Use a linter to check your code:

```bash
flake8
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
