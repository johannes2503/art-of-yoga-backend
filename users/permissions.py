from rest_framework import permissions

class IsInstructorOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow instructors and admins to access the view.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['instructor', 'admin']

    def has_object_permission(self, request, view, obj):
        # Check if the user is an instructor or admin
        if not request.user.is_authenticated or request.user.role not in ['instructor', 'admin']:
            return False
        
        # If the object has an instructor field, check if the user is the instructor
        if hasattr(obj, 'instructor'):
            return obj.instructor == request.user.userprofile
        
        # If the object has a user field, check if the user owns the object
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # For other objects, allow access to instructors and admins
        return True 