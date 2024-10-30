import os
from datetime import datetime
from authlib.jose import jwt, JWTClaims
from authlib.jose.errors import MissingClaimError, InvalidClaimError, ExpiredTokenError


class FailedTokenAuthentication(Exception):
    pass


def decode_token(token: bytes, debug: bool = False,) -> dict | None:
    """"""
    private_key: str = os.getenv('AUTH_KEY')

    # Decode the token first
    claims_option = {
        'iss': {
            'essential': True,
            'validate': lambda data, iss: iss in ['torched-user-interface', 'torched-backend-veryfication']
        },
        'scope': {
            'essential': True,
            'validate': lambda data, scope: scope in ['read', 'write', 'delete']
        },        
        'exp': {
        # jwt automatically checks this so validate is not required
            'essential': True,
        #     'validate': lambda exp_date: datetime.now().timestamp() >= exp_date
        }
    }
    claims: JWTClaims = jwt.decode(token, private_key, claims_options=claims_option)

    def log(msg: str, debug=False) -> None:
        path = 'token_log.txt' if not debug else 'debug_token_log.txt'
        with open(path, 'a') as file:
            file.write(f'{datetime.now()} - {e}\n') 
        
    try:
        claims.validate() 
        
    except MissingClaimError as e:
        log(e, debug)
        
    except InvalidClaimError as e:
        log(e, debug)
        
    except ExpiredTokenError as e:
        log(e, debug)
    
    except Exception as e:
        log(e, debug)
        raise FailedTokenAuthentication(f"Failed to decode token: {str(e)}")
    
    else:
        # If all validations pass, return claims
        return claims
    return None