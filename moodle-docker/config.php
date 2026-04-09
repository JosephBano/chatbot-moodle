<?php  // Moodle configuration file

unset($CFG);
global $CFG;
$CFG = new stdClass();

$CFG->dbtype = 'mariadb';
$CFG->dblibrary = 'native';
$CFG->dbhost = 'moodle_db';
$CFG->dbname = 'moodle_db';
$CFG->dbuser = 'moodle_user';
$CFG->dbpass = 'moodle_pass';
$CFG->prefix = 'mdl_';
$CFG->dboptions = array(
  'dbpersist' => 0,
  'dbport' => '',
  'dbsocket' => '',
  'dbcollation' => 'utf8mb4_unicode_ci',
);

$CFG->wwwroot = 'http://[IP_ADDRESS]:8080';
$CFG->dataroot = '/var/moodledata';
$CFG->admin = 'admin';

$CFG->directorypermissions = 02777;

// Forzar tema por defecto en caso de que el tema de producción no esté disponible
$CFG->theme = 'boost';

require_once(__DIR__ . '/lib/setup.php');

// There is no php closing tag in this file,
// it is intentional because it prevents trailing whitespace problems!
