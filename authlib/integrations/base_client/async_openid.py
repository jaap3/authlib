from authlib.jose import JsonWebToken, JsonWebKey
from authlib.oidc.core import UserInfo, CodeIDToken, ImplicitIDToken

__all__ = ['AsyncOpenIDMixin']


class AsyncOpenIDMixin(object):
    async def fetch_jwk_set(self, force=False):
        raise NotImplementedError()

    async def userinfo(self, **kwargs):
        """Fetch user info from ``userinfo_endpoint``."""
        metadata = await self.load_server_metadata()
        resp = await self.get(metadata['userinfo_endpoint'], **kwargs)
        data = resp.json()
        return UserInfo(data)

    async def parse_id_token(self, token, nonce, claims_options=None):
        """Return an instance of UserInfo from token's ``id_token``."""
        claims_params = dict(
            nonce=nonce,
            client_id=self.client_id,
        )
        if 'access_token' in token:
            claims_params['access_token'] = token['access_token']
            claims_cls = CodeIDToken
        else:
            claims_cls = ImplicitIDToken

        metadata = await self.load_server_metadata()
        if claims_options is None and 'issuer' in metadata:
            claims_options = {'iss': {'values': [metadata['issuer']]}}

        alg_values = metadata.get('id_token_signing_alg_values_supported')
        if not alg_values:
            alg_values = ['RS256']

        jwt = JsonWebToken(alg_values)

        jwk_set = await self.fetch_jwk_set()
        try:
            claims = jwt.decode(
                token['id_token'],
                key=JsonWebKey.import_key_set(jwk_set),
                claims_cls=claims_cls,
                claims_options=claims_options,
                claims_params=claims_params,
            )
        except ValueError:
            jwk_set = await self.fetch_jwk_set(force=True)
            claims = jwt.decode(
                token['id_token'],
                key=JsonWebKey.import_key_set(jwk_set),
                claims_cls=claims_cls,
                claims_options=claims_options,
                claims_params=claims_params,
            )

        # https://github.com/lepture/authlib/issues/259
        if claims.get('nonce_supported') is False:
            claims.params['nonce'] = None
        claims.validate(leeway=120)
        return UserInfo(claims)
