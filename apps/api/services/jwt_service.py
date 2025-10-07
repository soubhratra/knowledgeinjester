"""
JWT Service for Session Management

This service handles JWT token generation and validation for session-based authentication.
Implements Phase 1 security with origin-bound tokens.
"""

import jwt
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger('apps.api')

# JWT Configuration
JWT_SECRET_KEY = getattr(settings, 'JWT_SECRET_KEY', settings.SECRET_KEY)
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = getattr(settings, 'JWT_EXPIRATION_HOURS', 1)  # 1 hour default


class JWTService:
    """Service for JWT token generation and validation"""
    
    @staticmethod
    def generate_token(
        tenant_id: str,
        site_key: str,
        origin: str,
        env: str = 'prod',
        expires_in_hours: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate a JWT token for a session.
        
        Args:
            tenant_id: Internal tenant identifier
            site_key: Public site key
            origin: Origin header from the request
            env: Environment (prod, stage, dev)
            expires_in_hours: Token expiration time in hours (default: 1 hour)
        
        Returns:
            Dictionary containing token, session_id, and expiration info
        """
        session_id = str(uuid.uuid4())
        issued_at = datetime.utcnow()
        expires_in = expires_in_hours or JWT_EXPIRATION_HOURS
        expires_at = issued_at + timedelta(hours=expires_in)
        
        # JWT payload with claims
        payload = {
            'sid': session_id,           # session ID
            'tid': tenant_id,            # tenant ID (internal)
            'skey': site_key,            # site key (public)
            'org': origin,               # origin (bound to token)
            'env': env,                  # environment
            'iat': int(issued_at.timestamp()),
            'exp': int(expires_at.timestamp()),
        }
        
        # Generate JWT token
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        
        logger.info("JWT token generated", extra={
            'event_type': 'jwt_token_generated',
            'session_id': session_id,
            'site_key': site_key,
            'origin': origin,
            'iat': payload['iat'],
            'exp': payload['exp'],
            'expires_at': expires_at.isoformat(),
            'timestamp': issued_at.isoformat()
        })
        
        return {
            'token': token,
            'session_id': session_id,
            'expires_in': expires_in * 3600,  # Convert to seconds
            'expires_at': expires_at.isoformat(),
            'issued_at': issued_at.isoformat(),
        }
    
    @staticmethod
    def verify_token(token: str, expected_origin: Optional[str] = None) -> Dict[str, Any]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token string
            expected_origin: Expected origin to validate against token's origin claim
        
        Returns:
            Dictionary containing decoded token payload
        
        Raises:
            jwt.ExpiredSignatureError: If token has expired
            jwt.InvalidTokenError: If token is invalid
            ValueError: If origin validation fails
        """
        try:
            # Decode and verify token (skip iat validation, only validate exp)
            payload = jwt.decode(
                token, 
                JWT_SECRET_KEY, 
                algorithms=[JWT_ALGORITHM],
                options={"verify_iat": False},  # Skip iat validation to avoid clock skew issues
                leeway=10  # Allow 10 seconds leeway for exp
            )
            
            # Validate origin if provided
            if expected_origin and payload.get('org') != expected_origin:
                logger.warning("Origin validation failed for JWT token", extra={
                    'event_type': 'jwt_origin_mismatch',
                    'session_id': payload.get('sid'),
                    'token_origin': payload.get('org'),
                    'request_origin': expected_origin,
                    'timestamp': datetime.utcnow().isoformat()
                })
                raise ValueError(f"Origin mismatch: token origin '{payload.get('org')}' does not match request origin '{expected_origin}'")
            
            logger.debug("JWT token verified", extra={
                'event_type': 'jwt_token_verified',
                'session_id': payload.get('sid'),
                'site_key': payload.get('skey'),
                'timestamp': datetime.utcnow().isoformat()
            })
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired", extra={
                'event_type': 'jwt_token_expired',
                'timestamp': datetime.utcnow().isoformat()
            })
            raise
        except jwt.InvalidTokenError as e:
            logger.warning("Invalid JWT token", extra={
                'event_type': 'jwt_token_invalid',
                'error': str(e),
                'error_type': type(e).__name__,
                'timestamp': datetime.utcnow().isoformat()
            })
            raise
    
    @staticmethod
    def extract_bearer_token(authorization_header: Optional[str]) -> Optional[str]:
        """
        Extract JWT token from Authorization header.
        
        Args:
            authorization_header: Authorization header value (e.g., "Bearer <token>")
        
        Returns:
            JWT token string or None if not found
        """
        if not authorization_header:
            return None
        
        parts = authorization_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return None
        
        return parts[1]
    
    @staticmethod
    def get_client_ip(request) -> Optional[str]:
        """
        Extract client IP address from request.
        Handles proxy headers (X-Forwarded-For, X-Real-IP).
        
        Args:
            request: Django request object
        
        Returns:
            IP address string or None
        """
        # Check X-Forwarded-For header (proxy)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Take the first IP in the chain
            ip = x_forwarded_for.split(',')[0].strip()
            return ip
        
        # Check X-Real-IP header (nginx)
        x_real_ip = request.META.get('HTTP_X_REAL_IP')
        if x_real_ip:
            return x_real_ip.strip()
        
        # Fall back to REMOTE_ADDR
        return request.META.get('REMOTE_ADDR')


# Singleton instance
jwt_service = JWTService()

