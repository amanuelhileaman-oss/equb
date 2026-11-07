import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError

logger = logging.getLogger(__name__)

def _extract_error_text(data):
    if not data:
        return ''
    if isinstance(data, str):
        return data
    if isinstance(data, (list, tuple)):
        parts = [_extract_error_text(item) for item in data if item]
        return "; ".join([p for p in parts if p])
    if isinstance(data, dict):
        if 'detail' in data:
            return _extract_error_text(data['detail'])
        if 'message' in data and data['message'] != 'An input or validation error occurred.':
            return _extract_error_text(data['message'])
        errors = []
        for field, errs in data.items():
            err_text = _extract_error_text(errs)
            if err_text:
                if field in ('non_field_errors', '__all__'):
                    errors.append(err_text)
                else:
                    field_label = field.replace('_', ' ').capitalize()
                    errors.append(f"{field_label}: {err_text}")
        return "; ".join(errors) if errors else ''
    return str(data)

def custom_exception_handler(exc, context):
    """
    Standardized, safe error response format for Digital Equb Ethiopia.
    Guarantees no stack traces, raw DB error details, or credentials leak to the client.
    """
    # Call REST framework's default exception handler first to get the standard error response.
    response = exception_handler(exc, context)

    if response is not None:
        from rest_framework.exceptions import NotAuthenticated
        if isinstance(exc, NotAuthenticated):
            response.status_code = status.HTTP_401_UNAUTHORIZED

        custom_data = {
            'success': False,
            'error_type': exc.__class__.__name__,
            'detail': response.data if isinstance(response.data, (dict, list)) else str(response.data),
            'status_code': response.status_code
        }
        # Extract meaningful human-readable error message
        extracted = _extract_error_text(response.data)
        custom_data['message'] = extracted if extracted else 'Validation failed. Please check the provided information.'
        
        response.data = custom_data
        return response

    # Handle standard Django validation or permission errors that DRF might not catch directly
    if isinstance(exc, DjangoValidationError):
        return Response({
            'success': False,
            'error_type': 'ValidationError',
            'message': 'Data validation failed.',
            'detail': exc.message_dict if hasattr(exc, 'message_dict') else exc.messages,
            'status_code': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)

    from django.core.exceptions import RequestDataTooBig
    if isinstance(exc, RequestDataTooBig):
        return Response({
            'success': False,
            'error_type': 'PayloadTooLarge',
            'message': 'The uploaded file or image is too large. Please select an image under 5MB.',
            'status_code': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)

    from django.db import IntegrityError
    if isinstance(exc, IntegrityError):
        err_str = str(exc)
        if 'phone_number' in err_str:
            msg = 'A user with this phone number already exists.'
        elif 'email' in err_str:
            msg = 'A user with this email address already exists.'
        else:
            msg = 'Database constraint error: duplicate or conflicting data.'
        return Response({
            'success': False,
            'error_type': 'IntegrityError',
            'message': msg,
            'detail': err_str,
            'status_code': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)

    if isinstance(exc, PermissionDenied):
        return Response({
            'success': False,
            'error_type': 'PermissionDenied',
            'message': 'You do not have permission to perform this action.',
            'detail': str(exc),
            'status_code': status.HTTP_403_FORBIDDEN
        }, status=status.HTTP_403_FORBIDDEN)

    # Catch-all for unexpected internal exceptions
    logger.exception("Unhandled server exception: %s", exc)
    return Response({
        'success': False,
        'error_type': 'ServerError',
        'message': 'An internal server error occurred. Please contact system support.',
        'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR
    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
