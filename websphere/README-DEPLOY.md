# Practice Shop on WebSphere 9.0 with Oracle

This is the Practice Shop rewritten in Java so it can run on traditional IBM WebSphere Application Server 9.0
(Java 8, Servlet 3.1) with an Oracle 12c or newer database. The web pages are the same file the Python version uses.
The chat assistant is not included.

| File | What it is |
|---|---|
| `build/practice-shop.war` | The application to install on WebSphere |
| `db/create_user.sql` | Optional: creates the Oracle user `shop` (run as a DBA) |
| `db/shop_oracle.sql` | Creates the 8 tables and loads the seed data (run as `shop`) |
| `db/shop_oracle_drop.sql` | Removes the tables |
| `was/create_datasource.py` | wsadmin script for step 2 (not tested, see below) |
| `was/install_app.py` | wsadmin script for step 3 (not tested, see below) |
| `src/`, `build.sh`, `pom.xml` | Source code and build files |

## What was tested, and what was not

- Tested: the servlet, with the URL mappings from `web.xml`, on an embedded Jetty 9.4 against an H2 database in
  Oracle compatibility mode. `db/shop_oracle.sql` was run in full on that database. All 110 documented test cases
  (74 API, 36 browser) pass, at context root `/` and the API cases also at `/shop`.
- Not tested: WebSphere itself, a real Oracle database, the Oracle JDBC driver, the two wsadmin scripts, and
  `pom.xml`. None of them were available where this was built. H2's Oracle mode accepts Oracle syntax but is not
  Oracle, so the first run on your server is the real test. Step 4 below is how to check it.

## 1. Oracle

1. If you need a new database user, edit the password in `db/create_user.sql` and run it as a DBA.
   On a multitenant database, connect to the pluggable database first.
2. Connect as that user and run the main script:

   ```
   sqlplus shop/your_password@//dbhost:1521/ORCLPDB1 @shop_oracle.sql
   ```

3. Check it: `SELECT COUNT(*) FROM shop_products;` should return 30.

The product specs contain a bullet character. It displays correctly only if the database character set is
Unicode (AL32UTF8, the default since 12.2). On another character set it shows as `?`; nothing else is affected.

## 2. WebSphere to Oracle connection

The application looks up a data source with the JNDI name `jdbc/ShopDS`. Create it in the admin console
(`https://washost:9043/ibm/console`):

1. **Driver file.** Copy `ojdbc8.jar` (from Oracle, matching Java 8) to a folder on the WebSphere machine,
   for example `/opt/oracle/jdbc`.
2. **Variable.** Environment > WebSphere variables > choose your node > `ORACLE_JDBC_DRIVER_PATH` > set it to that folder.
3. **Login alias.** Security > Global security > Java Authentication and Authorization Service >
   J2C authentication data > New. Alias `shopOracleAlias`, user `shop`, and its password.
4. **JDBC provider.** Resources > JDBC > JDBC providers > choose the server scope > New.
   Database type `Oracle`, provider type `Oracle JDBC Driver`, implementation type `Connection pool data source`.
   Keep the class path `${ORACLE_JDBC_DRIVER_PATH}/ojdbc8.jar`.
5. **Data source.** Resources > JDBC > Data sources > same scope > New.
   - Data source name `ShopDS`, JNDI name `jdbc/ShopDS`
   - Select the provider from step 4
   - URL `jdbc:oracle:thin:@//dbhost:1521/ORCLPDB1` (host, port and service name of your database)
   - Data store helper class: `Oracle11g data store helper`
   - Component-managed authentication alias and container-managed authentication alias: both `shopOracleAlias`
6. Save, then select `ShopDS` and click **Test connection**. Fix this before going further; restart the server
   if the test says the variable or alias is unknown.

`was/create_datasource.py` does steps 2 to 5 from the command line. It has not been run on a real server.

## 3. Install the application

1. Applications > New application > New Enterprise Application > choose `practice-shop.war`.
2. Take the **Fast Path**. On "Map resource references to resources", `jdbc/ShopDS` should already point to
   `jdbc/ShopDS`. On "Map context roots", keep or type `/shop`.
3. Finish, Save, then start the application (Applications > WebSphere enterprise applications > PracticeShop > Start).

`was/install_app.py` does the same from the command line. It has not been run on a real server.

## 4. Check it

Replace `washost:9080` with your server and HTTP port.

| Open | Expect |
|---|---|
| `http://washost:9080/shop/health` | `{"status":"ok"}`: the application is running |
| `http://washost:9080/shop/health/db` | `{"status":"ok","database":"Oracle","products":30}`: WebSphere reaches Oracle and the script was run |
| `http://washost:9080/shop/` | The shop. Log in as `alice@example.com` / `Password123` |

If `/health/db` returns an error, its `detail` shows the database message (for example an `ORA-` code, or that
`jdbc/ShopDS` was not found). The same error is in the server's `SystemOut.log`.

To run the documented test cases against the deployed shop, from the Python project folder:

```
SHOP_BASE_URL=http://washost:9080/shop pytest tests/test_cases_api.py
```

This runs the 74 API cases. They reset the shop's data before each case, so use them only on a test database.
The browser cases assume the shop is at the root address, so they cannot target `/shop`.

## Settings

Set these as JVM custom properties (Servers > server > Java and Process Management > Process definition >
Java Virtual Machine > Custom properties), then restart the server.

| Property | Default | Purpose |
|---|---|---|
| `RESET_KEY` | `practice-reset` | Value the `X-Reset-Key` header must carry for `POST /test/reset` |
| `ALLOW_RESET` | `true` | Set to `false` to switch the reset endpoint off |

Change `RESET_KEY`, or switch reset off, on any server other people can reach: a reset wipes all shop data.

## Differences from the Python version

- No chat assistant, and no `/docs` page.
- Ids come from the table `shop_id_counters`, not identity columns, so that a reset can restart numbering at 1.
- Tables are prefixed `shop_`. The coupon column `value` is named `amount`.
- Validation error messages (HTTP 422) are worded differently. Status codes are the same.
- The application never creates or alters tables. Run `db/shop_oracle.sql` first.

## Rebuilding the WAR

With only a JDK, where `SERVLET_API` is any jar holding the `javax.servlet` 3.1 API:

```
SERVLET_API=/path/to/javax.servlet-api-3.1.0.jar ./build.sh
```

With Maven: `mvn package` (the `pom.xml` is provided but was not run).

`tools/gen_seed.py` regenerates `seed.json` and `db/shop_oracle.sql` from the Python shop's seed data.
`src/dev` holds the test server used during development; it needs Jetty 9.4 and H2 jars, which are not included.
