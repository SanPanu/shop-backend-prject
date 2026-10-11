# Installs practice-shop.war on traditional WebSphere 9.0 with context root /shop.
#
# NOT TESTED: written from the WebSphere 9.0 wsadmin documentation, without a WebSphere server to run it on.
# The admin console steps in README-DEPLOY.md do the same thing.
#
#   wsadmin.sh -lang jython -f install_app.py /path/to/practice-shop.war NODE SERVER

import sys

if len(sys.argv) != 3:
    print "Usage: install_app.py WAR_PATH NODE SERVER"
    sys.exit(1)

war, node, server = sys.argv
cell = AdminControl.getCell()
target = 'WebSphere:cell=%s,node=%s,server=%s' % (cell, node, server)
AdminApp.install(war, ['-appname', 'PracticeShop', '-contextroot', '/shop', '-usedefaultbindings',
                       '-defaultbinding.virtual.host', 'default_host', '-target', target])
AdminConfig.save()
print 'Installed PracticeShop. Start it from the console, or with:'
print "  AdminControl.invoke(AdminControl.queryNames('type=ApplicationManager,process=%s,*'), 'startApplication', 'PracticeShop')" % server
