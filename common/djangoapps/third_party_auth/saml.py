"""
Slightly customized python-social-auth backend for SAML 2.0 support
"""
import logging
from django.contrib.sites.models import Site
from django.http import Http404
from django.utils.functional import cached_property
from openedx.core.djangoapps.theming.helpers import get_current_request
import requests
from social.backends.saml import SAMLAuth, OID_EDU_PERSON_ENTITLEMENT
from social.exceptions import AuthForbidden, AuthMissingParameter

log = logging.getLogger(__name__)


class SAMLAuthBackend(SAMLAuth):  # pylint: disable=abstract-method
    """
    Customized version of SAMLAuth that gets the list of IdPs from third_party_auth's list of
    enabled providers.
    """
    name = "tpa-saml"

    def get_idp(self, idp_name):
        """ Given the name of an IdP, get a SAMLIdentityProvider instance """
        from .models import SAMLProviderConfig
        return SAMLProviderConfig.current(idp_name).get_config()

    def setting(self, name, default=None):
        """ Get a setting, from SAMLConfiguration """
        try:
            return self._config.get_setting(name)
        except KeyError:
            return self.strategy.setting(name, default)

    def auth_url(self):
        """
        Check that SAML is enabled and that the request includes an 'idp'
        parameter before getting the URL to which we must redirect in order to
        authenticate the user.

        raise Http404 if SAML authentication is disabled.
        raise AuthMissingParameter if the 'idp' parameter is missing.
        """
        if not self._config.enabled:
            log.error('SAML authentication is not enabled')
            raise Http404

        return super(SAMLAuthBackend, self).auth_url()

    def _check_entitlements(self, idp, attributes):
        """
        Check if we require the presence of any specific eduPersonEntitlement.

        raise AuthForbidden if the user should not be authenticated, or do nothing
        to allow the login pipeline to continue.
        """
        if "requiredEntitlements" in idp.conf:
            entitlements = attributes.get(OID_EDU_PERSON_ENTITLEMENT, [])
            for expected in idp.conf['requiredEntitlements']:
                if expected not in entitlements:
                    log.warning(
                        "SAML user from IdP %s rejected due to missing eduPersonEntitlement %s", idp.name, expected)
                    raise AuthForbidden(self)

    def _create_saml_auth(self, idp):
        """
        Get an instance of OneLogin_Saml2_Auth

        idp: The Identity Provider - a social.backends.saml.SAMLIdentityProvider instance
        """
        # We only override this method so that we can add extra debugging when debug_mode is True
        # Note that auth_inst is instantiated just for the current HTTP request, then is destroyed
        auth_inst = super(SAMLAuthBackend, self)._create_saml_auth(idp)
        from .models import SAMLProviderConfig
        if SAMLProviderConfig.current(idp.name).debug_mode:

            def wrap_with_logging(method_name, action_description, xml_getter):
                """ Wrap the request and response handlers to add debug mode logging """
                method = getattr(auth_inst, method_name)

                def wrapped_method(*args, **kwargs):
                    """ Wrapped login or process_response method """
                    result = method(*args, **kwargs)
                    log.info("SAML login %s for IdP %s. XML is:\n%s", action_description, idp.name, xml_getter())
                    return result
                setattr(auth_inst, method_name, wrapped_method)

            wrap_with_logging("login", "request", auth_inst.get_last_request_xml)
            wrap_with_logging("process_response", "response", auth_inst.get_last_response_xml)

        return auth_inst

    @cached_property
    def _config(self):
        from .models import SAMLConfiguration
        return SAMLConfiguration.current(Site.objects.get_current(get_current_request()))


class SapSuccessFactorsAuthBackend(SAMLAuthBackend):
    """
    Customized version of SAMLAuthBackend that knows how to retrieve user details
    from the SAPSuccessFactors OData API, rather than parse them directly off the
    SAML assertion that we get in response to a login attempt.
    """
    name = "sap-sf-saml"

    required_variables = (
        'sapsf_oauth_root_url',
        'sapsf_private_key',
        'odata_api_root_url',
        'odata_company_id',
        'odata_client_id',
    )

    def missing_variables(self, idp):
        """
        Check that we have all the details we need to properly retrieve rich data from the
        SAP SuccessFactors OData API. If we don't, then we should log a warning indicating
        the specific variables that are missing.
        """
        if not all(var in idp.conf for var in self.required_variables):
            missing = [var for var in self.required_variables if var not in idp.conf]
            log.warning(
                "To retrieve rich user data for an SAP SuccessFactors identity provider, the following keys in "
                "'other_settings' are required, but were missing: %s",
                missing
            )
            return missing

    def get_odata_api_client(self, idp, user_id, timeout):
        """
        Get a Requests session with the headers needed to properly authenticate it with
        the SAP SuccessFactors OData API.
        """
        session = requests.Session()
        assertion = session.post(
            idp.conf['sapsf_oauth_root_url'] + 'idp',
            data={
                'client_id': idp.conf['odata_client_id'],
                'user_id': user_id,
                'token_url': idp.conf['sapsf_oauth_root_url'] + 'token',
                'private_key': idp.conf['sapsf_private_key'],
            },
            timeout=timeout,
        )
        assertion.raise_for_status()
        assertion = assertion.text
        token = session.post(
            idp.conf['sapsf_oauth_root_url'] + 'token',
            data={
                'client_id': idp.conf['odata_client_id'],
                'company_id': idp.conf['odata_company_id'],
                'grant_type': 'urn:ietf:params:oauth:grant-type:saml2-bearer',
                'assertion': assertion,
            },
            timeout=timeout,
        )
        token.raise_for_status()
        token = token.json()['access_token']
        session.headers.update({'Authorization': 'Bearer {}'.format(token), 'Accept': 'application/json'})
        return session

    def get_user_details(self, response):
        """
        Attempt to get rich user details from the SAP SuccessFactors OData API. If we're missing any
        of the details we need to do that, fail nicely by returning the details we're able to extract
        from just the SAML response and log a warning.
        """
        details = super(SapSuccessFactorsAuthBackend, self).get_user_details(response)
        idp = self.get_idp(response['idp_name'])
        if self.missing_variables(idp):
            # If there aren't enough details to make the request, log a warning and return the details
            # from the SAML assertion.
            return details
        username = details['username']
        odata_timeout = int(idp.conf.get('odata_api_timeout_interval', 20))
        try:
            client = self.get_odata_api_client(idp, user_id=username, timeout=odata_timeout)
            response = client.get(
                '{root_url}User(userId=\'{user_id}\')?$select=username,firstName,lastName,defaultFullName,email'.format(
                    root_url=idp.conf['odata_api_root_url'],
                    user_id=username
                ),
                timeout=odata_timeout,
            )
            response.raise_for_status()
            response = response.json()
        except requests.RequestException:
            # If there was an HTTP level error, log the error and return the details from the SAML assertion.
            log.warning(
                'Unable to retrieve user details with username %s from SAPSuccessFactors with company ID %s.',
                username,
                idp.conf['odata_company_id'],
            )
            return details
        return {
            'username': response['d']['username'],
            'first_name': response['d']['firstName'],
            'last_name': response['d']['lastName'],
            'fullname': response['d']['defaultFullName'],
            'email': response['d']['email'],
        }
