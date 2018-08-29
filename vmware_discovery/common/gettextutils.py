# coding=utf-8

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

import gettext

t = gettext.translation('vmware-driver-common', fallback=True)


def _(msg):
    return t.ugettext(msg)

# vim: tabstop=4 shiftwidth=4 softtabstop=4
