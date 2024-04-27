db.getSiblingDB("unifi").createUser({user: "unifi", pwd: "CHANGEME", roles: [{role: "dbOwner", db: "unifi"}, {role: "dbOwner", db: "unifi_stat"}]});
