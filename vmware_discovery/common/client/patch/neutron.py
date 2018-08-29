COPYRIGHT = """
*************************************************************
Licensed Materials - Property of Vsettan

OCO Source Materials

(C) Copyright Vsettan Corp. 2016 All Rights Reserved

The source code for this program is not published or other-
wise divested of its trade secrets, irrespective of what has
been deposited with the U.S. Copyright Office.
*************************************************************
"""


def patch_client(service_wrapper, client):
    org_auth_and_fetch = client.httpclient.authenticate_and_fetch_endpoint_url

    """patch the authenticate_and_fetch_endpoint_url method to inject
    our own managed keystone token and endpoint
    """
    def _patched_auth_and_fetch():
        # inject our keystone managed token
        client.httpclient.auth_token = service_wrapper.keystone.auth_token
        client.httpclient.endpoint_url = service_wrapper.management_url
        return org_auth_and_fetch()

    client.httpclient.authenticate_and_fetch_endpoint_url = \
        _patched_auth_and_fetch
