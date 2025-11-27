#!/bin/bash

if which mongosh > /dev/null 2>&1; then
  mongo_init_bin='mongosh'
else
  mongo_init_bin='mongo'
fi
"${mongo_init_bin}" <<EOF
use ${MONGO_AUTHSOURCE}
db.auth("${MONGO_INITDB_ROOT_USERNAME}", "${MONGO_INITDB_ROOT_PASSWORD}")
db.getSiblingDB("${MONGO_DBNAME}").createUser({
  user: "${MONGO_USER}", 
  pwd: "${MONGO_PASS}", 
  roles: [
    {role: "dbOwner", db: "${MONGO_DBNAME}"}, 
    {role: "dbOwner", db: "${MONGO_DBNAME}_stat"},
    {role: "dbOwner", db: "${MONGO_DBNAME}_audit"}
  ]
});
db.createUser({
  user: "${MONGO_USER}",
  pwd: "${MONGO_PASS}",
  roles: [
    { db: "${MONGO_DBNAME}", role: "dbOwner" },
    { db: "${MONGO_DBNAME}_stat", role: "dbOwner" },
    { db: "${MONGO_DBNAME}_audit", role: "dbOwner" }
  ]
})
EOF
