# Creates the Oracle JDBC provider, login alias and data source jdbc/ShopDS on traditional WebSphere 9.0.
#
# NOT TESTED: written from the WebSphere 9.0 wsadmin documentation, without a WebSphere server to run it on.
# Read it before running, and prefer the admin console steps in README-DEPLOY.md if anything looks off.
#
# Run from <profile>/bin:
#   wsadmin.sh -lang jython -f create_datasource.py NODE SERVER DRIVER_DIR DB_HOST DB_PORT DB_SERVICE DB_USER DB_PASSWORD
# Example:
#   wsadmin.sh -lang jython -f create_datasource.py myNode01 server1 /opt/oracle/jdbc dbhost 1521 ORCLPDB1 shop secret
#
# DRIVER_DIR is the folder on the WebSphere machine that holds ojdbc8.jar.

import sys

if len(sys.argv) != 8:
    print "Usage: create_datasource.py NODE SERVER DRIVER_DIR DB_HOST DB_PORT DB_SERVICE DB_USER DB_PASSWORD"
    sys.exit(1)

node, server, driverDir, dbHost, dbPort, dbService, dbUser, dbPassword = sys.argv
scope = 'Node=%s,Server=%s' % (node, server)
alias = 'shopOracleAlias'
url = 'jdbc:oracle:thin:@//%s:%s/%s' % (dbHost, dbPort, dbService)

print 'Setting ORACLE_JDBC_DRIVER_PATH = %s on node %s' % (driverDir, node)
AdminTask.setVariable(['-variableName', 'ORACLE_JDBC_DRIVER_PATH', '-variableValue', driverDir, '-scope', 'Node=%s' % node])

print 'Creating login alias %s' % alias
AdminTask.createAuthDataEntry(['-alias', alias, '-user', dbUser, '-password', dbPassword,
                               '-description', 'Practice Shop Oracle login'])

print 'Creating JDBC provider'
provider = AdminTask.createJDBCProvider(['-scope', scope, '-databaseType', 'Oracle', '-providerType', 'Oracle JDBC Driver',
                                         '-implementationType', 'Connection pool data source',
                                         '-name', 'Oracle JDBC Driver (Practice Shop)',
                                         '-description', 'Oracle thin driver for the Practice Shop',
                                         '-classpath', ['${ORACLE_JDBC_DRIVER_PATH}/ojdbc8.jar']])

print 'Creating data source jdbc/ShopDS -> %s' % url
ds = AdminTask.createDatasource(provider, ['-name', 'ShopDS', '-jndiName', 'jdbc/ShopDS',
                                           '-dataStoreHelperClassName', 'com.ibm.websphere.rsadapter.Oracle11gDataStoreHelper',
                                           '-containerManagedPersistence', 'false',
                                           '-componentManagedAuthenticationAlias', alias,
                                           '-configureResourceProperties', [['URL', 'java.lang.String', url]]])
# The application asks the server to log in for it (res-auth = Container), so set the container-managed alias too.
AdminConfig.create('MappingModule', ds, [['authDataAlias', alias], ['mappingConfigAlias', '']])

AdminConfig.save()
print 'Saved. Restart the server, then use "Test connection" on the ShopDS data source in the admin console.'
