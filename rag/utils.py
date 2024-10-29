import os
from datetime import datetime
from authlib.jose import jwt, JWTClaims
from authlib.jose.errors import MissingClaimError, InvalidClaimError, ExpiredTokenError


class FailedTokenAuthentication(Exception):
    pass


def decode_token(token: bytes) -> dict:

    private_key: str = os.getenv('AUTH_KEY')

    # Decode the token first
    claims_option = {
        'iss': {
            'essential': True,
            'validate': lambda iss: iss in ['torched-user-interface', 'torched-backend-veryfication']
        },
        'data': {
            'essential': True,
        },
        'scope': {
            'essential': True,
            'validate': lambda scope: scope in ['read', 'write']
        },        
        'exp': {
            'essential': True,
            'validate': lambda exp_date:datetime.now().timestamp() > exp_date
        }
    }
    claims: JWTClaims = jwt.decode(token, private_key)
    claims.claims_option = claims_option

    try:
        claims.validate()
        
        # for some reason it won't validate it with .validate()
        essentials = ['exp', 'data', 'iss', 'scope']
        if not all(essential in claims for essential in essentials):
            raise Exception('Missing claim')
        if not claims_option['scope']['validate'](claims['scope']):
            raise Exception('Invalid scope')
        if not claims_option['iss']['validate'](claims['iss']):
            raise Exception('Invalid iss')
        
    except MissingClaimError as e:
        raise Exception(f"Missing claim: {str(e)}")
    except InvalidClaimError as e:
        raise FailedTokenAuthentication(f"Invalid claim")
    except ExpiredTokenError as e:
        raise FailedTokenAuthentication(f"Token has expired")
    except Exception as e:
        raise FailedTokenAuthentication(f"Failed to decode token: {str(e)}")

    # If all validations pass, return claims
    return claims