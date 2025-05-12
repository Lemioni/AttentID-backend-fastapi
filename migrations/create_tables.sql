DROP TABLE IF EXISTS mqtt_entries, devices, locations, location_type, topics, user_role, roles, users CASCADE;

CREATE TABLE users
(
  id_users BIGINT NOT NULL GENERATED ALWAYS AS IDENTITY,
  email    TEXT,
  created  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  active   TIMESTAMP,
  PRIMARY KEY (id_users)
);

COMMENT ON TABLE users IS 'Uzivatele';

CREATE TABLE roles
(
  id_roles    BIGINT NOT NULL GENERATED ALWAYS AS IDENTITY,
  description TEXT,
  PRIMARY KEY (id_roles)
);

COMMENT ON TABLE roles IS 'Role';

CREATE TABLE user_role
(
  id_user_role         BIGINT NOT NULL GENERATED ALWAYS AS IDENTITY,
  id_users             BIGINT NOT NULL,
  id_roles             BIGINT NOT NULL,
  id_users_created     BIGINT NOT NULL,
  when_created         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  id_users_deactivated BIGINT NOT NULL,
  when_deactivated     TIMESTAMP,
  PRIMARY KEY (id_user_role)
);

CREATE TABLE topics
(
  id_topics        BIGINT NOT NULL GENERATED ALWAYS AS IDENTITY,
  topic            TEXT,
  id_users_created BIGINT NOT NULL,
  when_created     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id_topics)
);

CREATE TABLE location_type
(
  id_location_type BIGINT NOT NULL GENERATED ALWAYS AS IDENTITY,
  description      TEXT,
  topic            TEXT,
  id_topics        BIGINT NOT NULL,
  PRIMARY KEY (id_location_type)
);

COMMENT ON TABLE location_type IS 'Umisteni';

CREATE TABLE device
(
  id_device      BIGINT NOT NULL GENERATED ALWAYS AS IDENTITY,
  description    TEXT,
  identification TEXT,
  mac_address    TEXT,
  id_users       BIGINT NOT NULL,
  PRIMARY KEY (id_device)
);

CREATE TABLE locations
(
  id_locations     BIGINT NOT NULL GENERATED ALWAYS AS IDENTITY,
  description      TEXT,
  id_location_type BIGINT NOT NULL,
  id_device        BIGINT NOT NULL,
  id_users_placed  BIGINT NOT NULL,
  when_created     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id_locations)
);

CREATE TABLE mqttenteries
(
  id_mqttenteries BIGINT NOT NULL GENERATED ALWAYS AS IDENTITY,
  time            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  topic           TEXT,
  payload         TEXT,
  id_topics       BIGINT NOT NULL,
  PRIMARY KEY (id_mqttenteries)
);

-- Add foreign key constraints
ALTER TABLE user_role
  ADD CONSTRAINT FK_users_TO_user_role
    FOREIGN KEY (id_users)
    REFERENCES users (id_users);

ALTER TABLE user_role
  ADD CONSTRAINT FK_roles_TO_user_role
    FOREIGN KEY (id_roles)
    REFERENCES roles (id_roles);

ALTER TABLE user_role
  ADD CONSTRAINT FK_users_TO_user_role1
    FOREIGN KEY (id_users_deactivated)
    REFERENCES users (id_users);

ALTER TABLE user_role
  ADD CONSTRAINT FK_users_TO_user_role2
    FOREIGN KEY (id_users_created)
    REFERENCES users (id_users);

ALTER TABLE locations
  ADD CONSTRAINT FK_location_type_TO_locations
    FOREIGN KEY (id_location_type)
    REFERENCES location_type (id_location_type);

ALTER TABLE locations
  ADD CONSTRAINT FK_device_TO_locations
    FOREIGN KEY (id_device)
    REFERENCES device (id_device);

ALTER TABLE device
  ADD CONSTRAINT FK_users_TO_device
    FOREIGN KEY (id_users)
    REFERENCES users (id_users);

ALTER TABLE locations
  ADD CONSTRAINT FK_users_TO_locations
    FOREIGN KEY (id_users_placed)
    REFERENCES users (id_users);

ALTER TABLE mqttenteries
  ADD CONSTRAINT FK_topics_TO_mqttenteries
    FOREIGN KEY (id_topics)
    REFERENCES topics (id_topics);

ALTER TABLE location_type
  ADD CONSTRAINT FK_topics_TO_location_type
    FOREIGN KEY (id_topics)
    REFERENCES topics (id_topics);

ALTER TABLE topics
  ADD CONSTRAINT FK_users_TO_topics
    FOREIGN KEY (id_users_created)
    REFERENCES users (id_users);

-- Insert some initial roles
INSERT INTO roles (description) VALUES ('Admin'), ('User'), ('Device Manager'), ('Viewer');

-- Add a system user for automated operations
INSERT INTO users (email, created, active) 
VALUES ('system@attentid.com', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);