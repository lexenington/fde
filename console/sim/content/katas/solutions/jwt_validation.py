import json

import jwt


class InvalidToken(Exception):
    pass


def validate(token, jwks, *, issuer, audience, now=None, leeway=30):
    try:
        header = jwt.get_unverified_header(token)
        key = next((k for k in jwks.get("keys", []) if k.get("kid") == header.get("kid")), None)
        if key is None:
            raise InvalidToken("unknown key")
        public = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
        options = {"require": ["exp", "iss", "aud"]}
        if now is None:
            return jwt.decode(token, public, algorithms=["RS256"], issuer=issuer, audience=audience, leeway=leeway, options=options)
        # PyJWT reads the real clock; to test at a chosen time, verify the signature and check the times ourselves
        claims = jwt.decode(token, public, algorithms=["RS256"], issuer=issuer, audience=audience,
                            options={**options, "verify_exp": False, "verify_nbf": False, "verify_iat": False})
        if claims["exp"] + leeway < now:
            raise InvalidToken("expired")
        if "nbf" in claims and claims["nbf"] - leeway > now:
            raise InvalidToken("not yet valid")
        return claims
    except InvalidToken:
        raise
    except Exception as e:                     # PyJWTError, KeyError, TypeError on None, ...
        raise InvalidToken(str(e)) from e
